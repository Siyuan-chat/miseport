"""Feed adapters must share safety behavior without cross-importing vendors."""
import pytest

from miseport.core import Catalog, Product
from miseport.discovery import DiscoveryProfile
from miseport.feed_common import FeedExportError, verified_enrichments, atomic_bytes
from miseport.google_feed import inspect_google, google_csv
from miseport.openai_feed import inspect_openai, openai_preview_gzip


def _shop():
    return Catalog([Product(
        sku="001", name="架空の茶葉", description="説明あり",
        price_jpy=1800, tax_included=True, stock="in_stock",
        source_url="https://shop.example.org/items/1",
        image_url="https://shop.example.org/image/1.png",
        merchant_id="shop", merchant_name="架空店",
        merchant_homepage="https://shop.example.org",
        updated_at="2026-11-01T12:00:00+09:00",
        is_demo=False,
    )])


def _profile(merchant="shop", sku="001"):
    return DiscoveryProfile.model_validate({
        "schema_version": "miseport-discovery/1.0",
        "merchant_id": merchant,
        "products": [{"sku": sku, "brand": "架空ブランド",
                      "brand_verified": True}],
    })


def test_both_exporters_share_identity_and_unknown_sku_rejection():
    shop = _shop()
    for invalid in (_profile(merchant="other"), _profile(sku="not-in-shop")):
        with pytest.raises(FeedExportError):
            verified_enrichments(shop, invalid)
        with pytest.raises(FeedExportError):
            inspect_google(shop, invalid)
        with pytest.raises(FeedExportError):
            inspect_openai(shop, invalid)


def test_no_synthetic_bypass_and_complete_cross_channel_snapshot():
    shop, profile = _shop(), _profile()
    assert set(verified_enrichments(shop, profile)) == {"001"}
    assert google_csv(inspect_google(shop, profile)).startswith(b"id,title,description")
    assert openai_preview_gzip(inspect_openai(shop, profile))
    # No legacy allow_synthetic_preview argument remains.
    with pytest.raises(TypeError):
        google_csv(inspect_google(shop, profile), allow_synthetic_preview=True)


def test_atomic_output_preserves_existing_target_when_symlinked(tmp_path):
    original = tmp_path / "original.csv"
    original.write_bytes(b"previous good data")
    link = tmp_path / "linked.csv"
    try:
        link.symlink_to(original)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this runner")
    with pytest.raises(FeedExportError):
        atomic_bytes(link, b"new data")
    assert original.read_bytes() == b"previous good data"
