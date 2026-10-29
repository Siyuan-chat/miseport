"""Regression: shop/profile switching must never reuse old imported products."""
import pytest

from miseport.source_context import (
    SourceContextError, capture_source_context, context_is_current
)


def capture(mode="api", platform="base", example_url="", **kwargs):
    fields=dict(merchant_id="shop-a", merchant_name="京都お茶店",
                merchant_homepage="https://tea.example.org/")
    fields.update(kwargs)
    return capture_source_context(mode,platform,**fields,example_url=example_url)


def is_current(snapshot, mode="api", platform="base", example_url="", **kwargs):
    fields=dict(merchant_id="shop-a", merchant_name="京都お茶店",
                merchant_homepage="https://tea.example.org/")
    fields.update(kwargs)
    return context_is_current(snapshot,mode=mode,platform=platform,
                              **fields,example_url=example_url)


def test_api_source_identity_pinned_without_token_or_example_url():
    old=capture()
    assert old.merchant_id=="shop-a" and old.platform=="base"
    assert old.example_url is None
    assert is_current(old,example_url="https://tea.example.org/items/1")
    for changes in [
        dict(merchant_id="shop-b"),dict(merchant_name="別のお店"),
        dict(merchant_homepage="https://evil.example.org/"),
        dict(mode="csv",platform="BASEの商品CSV",
             example_url="https://tea.example.org/items/1"),
    ]:
        assert not is_current(old,**changes)


def test_csv_source_binds_shop_profile_and_confirmed_item_example():
    old=capture(mode="csv",platform="BASEの商品CSV",
                example_url="https://tea.example.org/items/21")
    assert is_current(old,mode="csv",platform="BASEの商品CSV",
                      example_url="https://tea.example.org/items/21")
    assert not is_current(old,mode="csv",platform="Shopifyの商品CSV",
                          example_url="https://tea.example.org/items/21")
    assert not is_current(old,mode="csv",platform="BASEの商品CSV",
                          example_url="https://tea.example.org/items/22")
    assert not is_current(old,mode="csv",platform="BASEの商品CSV",
                          example_url="https://tea.example.org/items/21",
                          merchant_name="新しい店舗名")
    assert not is_current(old,mode="csv",platform="BASEの商品CSV",
                          example_url="https://tea.example.org/items/21",
                          merchant_homepage="https://another.example.org/")


@pytest.mark.parametrize("changed",[
    dict(merchant_id=""),dict(merchant_name=" "),
    dict(merchant_homepage="http://tea.example.org"),
    dict(merchant_homepage="https://127.0.0.1/"),
    dict(merchant_homepage="https://tea.example.org/admin"),
    dict(merchant_homepage="https://tea.example.org/?secret=1"),
])
def test_invalid_merchant_identity_rejected_before_import(changed):
    with pytest.raises(SourceContextError):
        capture(**changed)


def test_unknown_platform_or_missing_csv_example_cannot_pass():
    with pytest.raises(SourceContextError):
        capture(mode="api",platform="shopify")
    with pytest.raises(SourceContextError):
        capture(mode="csv",platform="Shopifyの商品CSV")
    with pytest.raises(SourceContextError):
        capture(mode="csv",platform="Shopifyの商品CSV",example_url=" ")
    assert not is_current(None)


def test_normalized_whitespace_is_not_a_cross_shop_identity():
    old=capture(merchant_id="shop-a",merchant_name="京都お茶店")
    assert is_current(old,merchant_id="  shop-a  ",merchant_name=" 京都お茶店 ")
