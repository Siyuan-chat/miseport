"""OpenAI Stable JSONL.gz local preview: never claims JP partner approval."""
import gzip
import json

import pytest

from miseport.core import Catalog, Product
from miseport.discovery import DiscoveryProfile
from miseport.google_feed import FeedExportError, atomic_bytes
from miseport.openai_feed import inspect_openai, openai_preview_gzip, REQUIRED_FIELDS


def catalog(*, demo=True, stock="unknown", price=1850):
    product = Product(
        sku="0012", name="宇治抹茶 30g", description="香り高い抹茶",
        price_jpy=price, stock=stock, tax_included=None,
        image_url="https://shop.example.org/pic/tea.png",
        source_url="https://shop.example.org/items/12",
        updated_at="2026-10-28T10:00:00+09:00",
        merchant_id="tea-shop", merchant_name="架空の茶店",
        merchant_homepage="https://shop.example.org",
        is_demo=demo,
    )
    return Catalog([product])


def profile(*, verified=True):
    return DiscoveryProfile.model_validate({
        "schema_version": "miseport-discovery/1.0", "merchant_id": "tea-shop",
        "products": [{"sku": "0012", "brand": "架空ブランド",
                      "brand_verified": verified}],
    })


def test_openai_preview_has_nine_stable_fields_jpy_and_explicit_unknown():
    report = inspect_openai(catalog(), profile())
    assert report["blocked_rows"] == 0
    assert report["market"] == "JP" and not report["market_approved"]
    assert report["default_upload_market"] == "US"
    assert report["contains_synthetic"] is True
    data = openai_preview_gzip(report)
    assert data == openai_preview_gzip(report)
    payload = gzip.decompress(data).decode("utf-8")
    assert payload.endswith("\n") and payload.count("\n") == 1
    row = json.loads(payload.strip())
    assert set(row) == set(REQUIRED_FIELDS)
    assert row["item_id"] == "0012"
    assert row["availability"] == "unknown"
    assert row["price"] == "1850 JPY"
    assert row["seller_name"] == "架空の茶店"
    assert "target_countries" not in row
    assert "marketplace_seller" not in row
    assert report["submitted"] is False and report["agent_discovery_verified"] is False


def test_full_snapshot_failure_cannot_replace_previous_export(tmp_path):
    target = tmp_path / "feed.preview.jsonl.gz"
    target.write_bytes(b"good old export")
    incomplete = inspect_openai(catalog(), profile(verified=False))
    assert "merchant_verified_brand_missing" in incomplete["issues"][0]["codes"]
    with pytest.raises(FeedExportError):
        openai_preview_gzip(incomplete)
    assert target.read_bytes() == b"good old export"
    good = openai_preview_gzip(inspect_openai(catalog(), profile()))
    atomic_bytes(target, good)
    assert gzip.decompress(target.read_bytes())


def test_zero_price_and_wrong_merchant_are_refused():
    x = inspect_openai(catalog(price=0), profile())
    assert "positive_price_required" in x["issues"][0]["codes"]
    with pytest.raises(FeedExportError):
        openai_preview_gzip(x)
    wrong = DiscoveryProfile.model_validate({
        "schema_version": "miseport-discovery/1.0", "merchant_id": "other"})
    with pytest.raises(FeedExportError, match="merchant identity"):
        inspect_openai(catalog(), wrong)


def test_real_shop_state_does_not_imply_market_approval():
    report = inspect_openai(catalog(demo=False, stock="in_stock"), profile())
    assert report["blocked_rows"] == 0 and report["market_approved"] is False
    assert report["partner_approved"] is False
