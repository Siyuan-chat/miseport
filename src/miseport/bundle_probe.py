"""Offline verification of a generated merchant-owned Cloudflare Pages ZIP.

This verifies the exact catalog, manifest, approved file set and executable
Worker template. It never deploys, fetches shop pages or contacts a cloud API.
"""
from hashlib import sha256
from html import escape
from importlib.resources import files
import json
from pathlib import Path
from urllib.parse import urlsplit
import zipfile

from .core import Catalog, Product
from .publisher import SENSITIVE_TEXT

PUBLIC_FILES = frozenset({
    "_worker.js", "index.html", "catalog.json", "manifest.json",
    "robots.txt", "sitemap.xml", "README.txt",
})
MAX_ZIP_BYTES = 24 * 1024 * 1024
MAX_FILE_BYTES = 15 * 1024 * 1024
MAX_UNCOMPRESSED = 25 * 1024 * 1024


class BundleVerificationError(ValueError):
    """Merchant-readable failure message without echoing secret content."""


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _json(data: bytes):
    if len(data) > MAX_FILE_BYTES:
        raise BundleVerificationError("ZIP内のファイルが大きすぎます。")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise BundleVerificationError("商品データのJSON形式が正しくありません。") from None


def inspect_merchant_zip(path: str | Path, *, expected_origin: str | None = None) -> dict:
    """Verify a bundle's integrity and read-only assumptions before upload."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ZIP_BYTES:
        raise BundleVerificationError("ZIPファイルを確認してください。")
    try:
        with zipfile.ZipFile(path, "r") as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
            if (len(names) != len(PUBLIC_FILES) or set(names) != PUBLIC_FILES
                    or len(set(names)) != len(names)
                    or any(i.is_dir() or i.file_size > MAX_FILE_BYTES
                           or i.filename.startswith(("/", "."))
                           or "/" in i.filename or "\\" in i.filename
                           for i in infos)
                    or sum(i.file_size for i in infos) > MAX_UNCOMPRESSED):
                raise BundleVerificationError("ZIPの公開ファイル構成を確認してください。")
            data = {name: z.read(name) for name in names}
    except BundleVerificationError:
        raise
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError):
        raise BundleVerificationError("ZIPファイルを安全に読み取れません。") from None

    for name, content in data.items():
        if SENSITIVE_TEXT.search(content.decode("utf-8", errors="replace")):
            raise BundleVerificationError("ZIP内の機密情報を確認してください。")

    manifest = _json(data["manifest.json"])
    catalog_data = _json(data["catalog.json"])
    if (not isinstance(manifest, dict) or not isinstance(catalog_data, dict)
            or manifest.get("version") != "merchant-bundle-0.1"
            or not isinstance(catalog_data.get("metadata"), dict)
            or not isinstance(catalog_data.get("products"), list)):
        raise BundleVerificationError("商品公開マニフェストが不正です。")
    meta = catalog_data["metadata"]
    origin = meta.get("origin")
    try:
        url = urlsplit(origin)
    except (TypeError, ValueError):
        raise BundleVerificationError("公開HTTPSアドレスが不正です。") from None
    if (url.scheme != "https" or not url.hostname
            or origin != "https://" + url.hostname
            or (expected_origin is not None and origin != expected_origin)):
        raise BundleVerificationError("ZIPの公開ドメインが想定と異なります。")
    if (manifest.get("origin") != origin or manifest.get("merchant") != meta.get("merchant")
            or manifest.get("snapshot_generated_at") != meta.get("snapshot_generated_at")
            or manifest.get("demo_only") != meta.get("demo_only")
            or type(meta.get("demo_only")) is not bool or meta.get("checkout") is not False
            or meta.get("stock_is_live") is not False):
        raise BundleVerificationError("公開商品情報とマニフェストが一致しません。")
    raw_products = catalog_data["products"]
    if not raw_products or len(raw_products) > 10000:
        raise BundleVerificationError("公開商品件数が不正です。")
    try:
        products = [Product.model_validate(p) for p in raw_products]
        catalog = Catalog(products)
    except ValueError:
        raise BundleVerificationError("商品データを検証できません。") from None
    merchant = meta["merchant"]
    if (not isinstance(merchant, dict) or
            any(p.is_demo != meta["demo_only"] or
                p.merchant_id != merchant.get("id") or
                p.merchant_name != merchant.get("name") or
                p.merchant_homepage != merchant.get("homepage") or
                not p.source_url.startswith("https://")
                for p in products)):
        raise BundleVerificationError("異なる商店または非公開商品が混入しています。")
    listed = manifest.get("files")
    if (type(manifest.get("product_count")) is not int
            or manifest["product_count"] != len(raw_products)
            or not isinstance(listed, list) or len(listed) != len(PUBLIC_FILES)-1):
        raise BundleVerificationError("商品件数やファイル一覧が一致しません。")
    if {f for f in data if f != "manifest.json"} != {x.get("path") for x in listed
        if isinstance(x, dict)}:
        raise BundleVerificationError("ZIPのファイル一覧が一致しません。")
    for entry in listed:
        if (not isinstance(entry, dict) or
                type(entry.get("size")) is not int or
                entry["size"] != len(data[entry["path"]]) or
                entry.get("sha256") != sha256(data[entry["path"]]).hexdigest()):
            raise BundleVerificationError("ZIPファイルのハッシュが一致しません。")
    # Check that the executable Worker is compiled from the reviewed template and
    # from exactly the same catalog being published. Hashes alone are forgeable.
    product_payload = [p.model_dump(mode="json") for p in products]
    if raw_products != product_payload:
        raise BundleVerificationError("商品データが正規の形式と一致しません。")
    records = {"products": product_payload,
               "jsonld": {p.sku: catalog.jsonld(p.sku)["jsonld"] for p in products},
               "snapshot_at": meta["snapshot_generated_at"],
               "demo_only": meta["demo_only"]}
    template = files("miseport").joinpath("merchant_worker.js").read_text(encoding="utf-8")
    expected_worker = template.replace("__MISEPORT_DATA__", json.dumps(records, ensure_ascii=True))
    expected_worker = expected_worker.replace("__MISEPORT_HOST__", json.dumps(url.hostname))
    if expected_worker.encode("utf-8") != data["_worker.js"]:
        raise BundleVerificationError("MCP Workerと商品カタログが一致しません。")
    if (origin not in data["robots.txt"].decode("utf-8")
            or escape(origin) not in data["sitemap.xml"].decode("utf-8")):
        raise BundleVerificationError("検索エンジン向けURLが公開先と異なります。")
    return {
        "valid": True, "merchant_id": merchant["id"],
        "origin": origin, "product_count": len(products),
        "demo_only": meta["demo_only"], "read_only": True,
        "snapshot_generated_at": meta["snapshot_generated_at"],
        "files_verified": len(PUBLIC_FILES),
        "note": "Offline package verification only; actual HTTP/MCP hosting and merchant consent require separate checks.",
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verify a merchant MCP/REST ZIP before Cloudflare upload.")
    parser.add_argument("zip_file")
    parser.add_argument("--origin", default=None)
    args = parser.parse_args()
    try:
        report = inspect_merchant_zip(args.zip_file, expected_origin=args.origin)
    except (BundleVerificationError, OSError):
        parser.error("ZIPの整合性を確認できません。再生成してからお試しください。")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
