"""Bounded local JSON/CSV adapters; validation is atomic."""
import csv
import io
import json
import os
from pathlib import Path
import tempfile

from pydantic import ValidationError
from .core import Catalog, Product

MAX_BYTES = 10 * 1024 * 1024
MAX_PRODUCTS = 10000


class CatalogError(ValueError):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _csv_value(key: str, value: str | None):
    if value is None:
        raise ValueError("missing CSV cell")
    value = value.strip()
    if key in {"price_jpy", "shipping_jpy", "stock_quantity"}:
        if key != "price_jpy" and value == "":
            return None
        if not value.isascii() or not value.isdigit():
            raise ValueError(f"{key} must be integer JPY")
        return int(value)
    if key in {"is_demo", "tax_included", "gift_wrapping"}:
        if key != "is_demo" and value == "":
            return None
        if value.lower() not in {"true", "false"}:
            raise ValueError(f"{key} must be true or false")
        return value.lower() == "true"
    if key == "stock" and not value:
        return "unknown"
    if key in {"merchant_id", "merchant_name", "merchant_homepage", "evidence_url", "image_url",
               "origin_prefecture", "caffeine_level", "snapshot_at"} and not value:
        return None
    return value


def load_catalog(path: str | Path) -> Catalog:
    path = Path(path)
    try:
        if not path.is_file():
            raise CatalogError("catalog must be a regular local file")
        with path.open("rb") as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise CatalogError("catalog exceeds 10 MiB")
        text = raw.decode("utf-8-sig")
        if path.suffix.lower() == ".json":
            rows = json.loads(text, object_pairs_hook=_unique_object)
            if isinstance(rows, dict):
                from .legacy import LegacyAdapter, canonical_catalog
                if rows.get("schema_version") == "1.0":
                    return LegacyAdapter.convert(rows)
                if rows.get("schema_version") == "miseport/1.1":
                    return canonical_catalog(rows)
                raise CatalogError("unsupported catalog object schema_version")
        elif path.suffix.lower() == ".csv":
            reader = csv.DictReader(io.StringIO(text), strict=True)
            if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise CatalogError("CSV headers must be present and unique")
            rows = []
            for row in reader:
                if None in row:
                    raise CatalogError("CSV has extra cells")
                rows.append({key: _csv_value(key, value) for key, value in row.items()})
                if len(rows) > MAX_PRODUCTS:
                    raise CatalogError("catalog exceeds 10000 products")
        else:
            raise CatalogError("supported formats: .json and .csv")
        if not isinstance(rows, list) or len(rows) > MAX_PRODUCTS:
            raise CatalogError("catalog must be an array of at most 10000 products")
        products = []
        for index, row in enumerate(rows, 1):
            try:
                products.append(Product.model_validate(row))
            except ValidationError as exc:
                details = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
                raise CatalogError(f"row {index}: {details}") from exc
        return Catalog(products)
    except CatalogError:
        raise
    except RecursionError as exc:
        raise CatalogError("catalog JSON nesting is too deep") from exc
    except ValidationError as exc:
        details = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        raise CatalogError(f"invalid catalog: {details}") from exc
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        raise CatalogError(f"cannot load catalog: {exc}") from exc


def save_catalog(catalog: Catalog, output: str | Path) -> None:
    output = Path(output)
    temporary = None
    data = [p.model_dump(mode="json") for p in catalog.products]
    if catalog.metadata:
        from .legacy import canonical_catalog
        data = {"schema_version": "miseport/1.1", "metadata": catalog.metadata, "products": data}
        canonical_catalog(data)  # Refuse inconsistent envelope before writing.
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         delete=False, suffix=".tmp") as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
