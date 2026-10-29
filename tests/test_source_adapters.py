"""Read-only connector protocol contract stays portable across EC platforms."""
from datetime import datetime, timezone
import json

import pytest

from miseport.base_v2 import BaseV2Client
from miseport.source_adapters import (
    BaseSourceAdapter, MerchantProfile, ReadOnlySourceAdapter,
    get_source_adapter,
)


def sample_item():
    return {
        "id": 17, "name": "ほうじ茶", "detail": "", "type": "normal",
        "visible": True, "sales_status": "item_now_on_sale",
        "stock": 2, "price": 1800, "modified_at": "2026-10-29T00:00:00Z",
        "categories": [], "images": [], "options": [], "variations": [],
    }


def test_base_adapter_matches_protocol_and_has_only_read_access():
    calls=[]
    def fake(url,headers,timeout):
        calls.append({"url":url,"method":"GET", "has_pat":headers.get("Authorization")=="Bearer secret"})
        return 200,json.dumps([sample_item()]).encode()
    adapter=get_source_adapter("base",base_client=BaseV2Client(transport=fake))
    assert isinstance(adapter,ReadOnlySourceAdapter)
    caps=adapter.capabilities
    assert caps.platform_id=="base" and caps.access_level=="read_only"
    assert caps.authorization_type=="owner_pat_items.read"
    assert not caps.supports_automatic_background_sync
    rows=adapter.fetch_public("secret")
    assert [x["id"] for x in rows]==[17]
    assert calls[0]["has_pat"] and "secret" not in calls[0]["url"]
    merchant=MerchantProfile(
        merchant_id="shop",merchant_name="京都茶店",
        merchant_homepage="https://shop.example.org/",
        verified_product_urls={17:"https://shop.example.org/items/17"},
        is_demo=True,
    )
    mapped=adapter.normalize(rows,merchant,snapshot_at=datetime(2026,10,29,tzinfo=timezone.utc))
    assert mapped.publishable
    assert mapped.catalog.products[0].sku=="base-17"
    assert not hasattr(adapter,"write_product")
    assert not hasattr(adapter,"delete_product")


@pytest.mark.parametrize("platform",["shopify","makeshop","eccube","stores","","BASE"])
def test_unsupported_native_integrations_not_falsely_advertised(platform):
    with pytest.raises(ValueError,match="未対応"):
        get_source_adapter(platform)


def test_profile_requires_identity_without_secrets():
    with pytest.raises(ValueError):
        MerchantProfile("","bad","https://shop.example.org/",{})
    with pytest.raises(ValueError):
        MerchantProfile("id","name","https://shop.example.org/",{},is_demo="false")
