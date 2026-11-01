"""Google Merchant JP CSV conversion is offline and fails closed."""
from dataclasses import replace
import csv
import io

import pytest

from miseport.core import Catalog, Product
from miseport.discovery import DiscoveryProfile
from miseport.google_feed import inspect_google, google_csv, atomic_bytes, FeedExportError


def sample(*, stock="in_stock", demo=False, price=1850, tax=True):
    # Fictional product created in memory only. Never published as a real shop.
    return Catalog([Product(sku="00012", name='京都お茶 "ギフト", 80g',
        description="お茶\n香ばしい茶葉", category="食品", price_jpy=price,
        stock=stock, source_url="https://shop.example.org/items/12",
        image_url="https://shop.example.org/images/item12.png",
        updated_at="2026-10-29T10:00:00+09:00", is_demo=demo,
        merchant_id="tea", merchant_name="架空のお茶屋",
        merchant_homepage="https://shop.example.org",
        tax_included=tax)])


def profile(*, brand="架空お茶ブランド", verified=True):
    return DiscoveryProfile.model_validate({
        "schema_version": "miseport-discovery/1.0", "merchant_id": "tea",
        "products": [{"sku": "00012", "brand": brand, "brand_verified": verified}]})


def test_valid_japan_full_snapshot_uses_exact_csv_fields_quoted_unicode_and_jpy():
    report = inspect_google(sample(), profile())
    assert report["catalog_count"] == 1
    assert report["blocked_rows"] == 0 and report["submitted"] is False
    assert report["platform_policy_verified"] is False
    data = google_csv(report)
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
    assert len(rows) == 1 and rows[0]["id"] == "00012"
    assert rows[0]["price"] == "1850 JPY" and rows[0]["availability"] == "in_stock"
    assert rows[0]["title"] == '京都お茶 "ギフト", 80g'
    assert rows[0]["description"] == "お茶\n香ばしい茶葉"
    assert rows[0]["brand"] == "架空お茶ブランド"
    assert "image_link" in rows[0] and "item_id" not in rows[0]


@pytest.mark.parametrize("catalog, prof, expected", [
    (sample(stock="unknown"), profile(), "google_requires_known_availability"),
    (sample(price=0), profile(), "positive_price_required"),
    (sample(tax=False), profile(), "japan_tax_included_price_unconfirmed"),
    (sample(), profile(verified=False), "verified_brand_missing_or_over_70"),
    (sample(demo=True), profile(), "demo_product_not_for_submission"),
])
def test_required_fields_reject_incomplete_or_synthetic_items(catalog, prof, expected):
    report = inspect_google(catalog, prof)
    assert expected in report["issues"][0]["codes"]
    with pytest.raises(FeedExportError):
        google_csv(report)


def test_atomic_export_does_not_replace_good_file_after_validation_failure(tmp_path):
    target = tmp_path / "feed.csv"
    target.write_bytes(b"prior complete feed")
    assert inspect_google(sample(stock="unknown"), profile())["blocked_rows"] == 1
    with pytest.raises(FeedExportError):
        google_csv(inspect_google(sample(stock="unknown"), profile()))
    assert target.read_bytes() == b"prior complete feed"
    atomic_bytes(target, google_csv(inspect_google(sample(), profile())))
    assert target.read_bytes().startswith(b"id,title,description")


def test_profile_identity_is_not_derived_from_merchant_name():
    with pytest.raises(FeedExportError, match="merchant identity"):
        inspect_google(sample(), DiscoveryProfile.model_validate({
            "schema_version": "miseport-discovery/1.0", "merchant_id": "wrong"}))
