"""Archived v1 input must survive conversion without losing uncertainty."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from miseport.importers import CatalogError, load_catalog, save_catalog
from miseport.legacy import LegacyAdapter

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "tests/fixtures/demo-store.reference.json"


@pytest.fixture
def legacy():
    return json.loads(LEGACY.read_text(encoding="utf-8"))


def write_catalog(tmp_path, data):
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_legacy_auto_detection_and_explicit_adapter_preserve_product_metadata(legacy, tmp_path):
    catalog = load_catalog(LEGACY)
    assert LegacyAdapter.convert(legacy).search() == catalog.search()
    assert len(catalog.products) == 2
    for source in legacy["products"]:
        row = catalog.detail(source["id"])["product"]
        assert row["sku"] == source["id"] and row["name"] == source["name_ja"]
        assert row["description"] == source["description_ja"]
        assert row["source_url"] == source["product_url"] and row["is_demo"] is True
        assert row["stock_quantity"] == source["stock"]
        for field in ("merchant_id", "price_jpy", "tax_included", "shipping_jpy", "gift_wrapping",
                      "origin_prefecture", "caffeine_level", "image_url", "evidence_url", "updated_at"):
            assert row[field] == source[field]
        assert row["merchant_name"] == legacy["merchant"]["name"]
        assert row["merchant_homepage"] == legacy["merchant"]["homepage"]
    assert catalog.inventory("tea-001")["stock"] == "in_stock"
    assert catalog.inventory("tea-002")["stock"] == "unknown"
    converted = tmp_path / "converted.json"
    save_catalog(catalog, converted)
    restored = load_catalog(converted)
    assert restored.search() == catalog.search()
    assert restored.metadata == catalog.metadata
    assert restored.metadata["merchant"] == legacy["merchant"]
    assert restored.metadata["snapshot_at"] == legacy["snapshot_at"]
    assert restored.metadata["demo_only"] is True


def test_legacy_empty_catalog_keeps_provenance_through_roundtrip(tmp_path, legacy):
    legacy["products"] = []
    catalog = load_catalog(write_catalog(tmp_path, legacy))
    output = tmp_path / "empty.json"
    save_catalog(catalog, output)
    restored = load_catalog(output)
    assert restored.products == []
    assert restored.metadata == catalog.metadata
    assert restored.metadata["merchant"] == legacy["merchant"]


@pytest.mark.parametrize("field,value", [
    ("merchant_id", "other"), ("merchant_name", "other"),
    ("merchant_homepage", "https://other.example/"), ("is_demo", False),
    ("snapshot_at", "2026-10-28T00:00:00+09:00"),
])
def test_canonical_envelope_rejects_product_provenance_tampering(tmp_path, legacy, field, value):
    output = tmp_path / "canonical.json"
    save_catalog(LegacyAdapter.convert(legacy), output)
    canonical = json.loads(output.read_text(encoding="utf-8"))
    canonical["products"][0][field] = value
    with pytest.raises(CatalogError):
        load_catalog(write_catalog(tmp_path, canonical))


def test_inconsistent_metadata_save_keeps_existing_output(tmp_path, legacy):
    catalog = LegacyAdapter.convert(legacy)
    output = tmp_path / "canonical.json"
    save_catalog(catalog, output)
    before = output.read_bytes()
    catalog.metadata["demo_only"] = False
    with pytest.raises(ValueError):
        save_catalog(catalog, output)
    assert output.read_bytes() == before


@pytest.mark.parametrize("change", [
    {"schema_version": "2.0"}, {"schema_version": 1.0}, {"demo_only": "true"},
    {"demo_only": 1}, {"snapshot_at": "2026-10-27T00:00:00"}, {"extra": "silently lost"},
])
def test_legacy_invalid_envelope_is_rejected(tmp_path, legacy, change):
    legacy.update(change)
    with pytest.raises(CatalogError):
        load_catalog(write_catalog(tmp_path, legacy))


@pytest.mark.parametrize("field,value", [
    ("merchant_id", "another-shop"), ("stock", True), ("stock", -1), ("stock", 1.5),
    ("stock", "12"), ("evidence_url", "javascript:alert(1)"),
    ("image_url", "https://u:p@example.org/image"), ("product_url", "relative/path"),
    ("invented", "silently lost"),
])
def test_legacy_invalid_product_is_rejected(tmp_path, legacy, field, value):
    legacy["products"][0][field] = value
    with pytest.raises(CatalogError):
        load_catalog(write_catalog(tmp_path, legacy))


@pytest.mark.parametrize("field,value", [("homepage", "file:///tmp/shop"), ("extra", 1)])
def test_legacy_invalid_merchant_is_rejected(tmp_path, legacy, field, value):
    legacy["merchant"][field] = value
    with pytest.raises(CatalogError):
        load_catalog(write_catalog(tmp_path, legacy))


def test_legacy_duplicate_sku_rejected(tmp_path, legacy):
    legacy["products"].append(deepcopy(legacy["products"][0]))
    with pytest.raises(CatalogError, match="duplicate SKU"):
        load_catalog(write_catalog(tmp_path, legacy))


def test_legacy_false_demo_and_zero_stock_remain_facts(tmp_path, legacy):
    legacy["demo_only"] = False
    legacy["products"][0]["stock"] = 0
    catalog = load_catalog(write_catalog(tmp_path, legacy))
    assert all(p.is_demo is False for p in catalog.products)
    assert catalog.audit()["demo_product_count"] == 0
    inventory = catalog.inventory("tea-001")
    assert inventory["stock"] == "out_of_stock" and inventory["stock_quantity"] == 0
    assert catalog.quote("tea-001")["can_fulfill_snapshot"] is False
