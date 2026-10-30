"""Offline catalog comparison never substitutes for checking a real shop."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from miseport.catalog_compare import compare_catalogs
from miseport.core import Catalog
from miseport.importers import load_catalog

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/demo-store.reference.json"


def sample():
    return load_catalog(FIXTURE)


def test_identical_merchant_snapshots_pass_locally():
    report = compare_catalogs(sample(), sample())
    assert report["ready_for_review"] and report["issue_count"] == 0
    assert report["web_pages_verified"] is False
    assert report["source_authenticity_verified"] is False


def test_price_and_stock_drift_fails_with_field_names_not_sensitive_values():
    actual = sample()
    changed = sample()
    changed.products[0] = changed.products[0].model_copy(
        update={"price_jpy": 999, "stock_quantity": 0, "stock": "out_of_stock"})
    changed.by_sku = {p.sku: p for p in changed.products}
    result = compare_catalogs(actual, changed)
    assert not result["ready_for_review"]
    errors = [x for x in result["issues"] if x["code"] == "PRODUCT_FACT_MISMATCH"]
    assert len(errors) == 1 and errors[0]["sku"] == "tea-001"
    assert {"price_jpy", "stock", "stock_quantity"} <= set(errors[0]["fields"])


def test_missing_and_unexpected_products_do_not_silently_pass():
    source = sample()
    published = Catalog([source.products[1]])
    result = compare_catalogs(source, published)
    assert any(x["code"] == "MISSING_PUBLISHED_SKU" for x in result["issues"])


def test_wrong_merchant_identity_blocks():
    source, target = sample(), sample()
    target.products[0] = target.products[0].model_copy(update={"merchant_id": "wrong"})
    target.by_sku = {p.sku: p for p in target.products}
    result = compare_catalogs(source, target)
    assert any(x["code"] == "MERCHANT_IDENTITY_UNVERIFIED" for x in result["issues"])


def test_age_requires_explicit_reference_time_and_records_stale():
    with pytest.raises(ValueError):
        compare_catalogs(sample(), sample(), max_age_hours=1)
    stamp = datetime(2026, 10, 30, tzinfo=timezone.utc)
    result = compare_catalogs(sample(), sample(), as_of=stamp, max_age_hours=24)
    assert any(x["code"] == "PUBLISHED_SNAPSHOT_STALE" for x in result["issues"])
    assert result["as_of"] == stamp.isoformat()
