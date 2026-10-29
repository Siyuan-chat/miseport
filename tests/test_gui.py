"""GUI-related logic can be tested headlessly; no Tk or credentials required."""
import pytest

from miseport.gui import parse_product_urls, preview_mapping


@pytest.mark.parametrize("raw", [
    "abc=https://shop.example.org/1", "0=https://shop.example.org/0",
    "1=http://shop.example.org/1", "1=javascript:alert(1)",
    "1=https://user:password@shop.example.org/1",
    "1=https://shop.example.org/1\n1=https://shop.example.org/2",
    "https://shop.example.org/1",
])
def test_unverified_or_unsafe_merchant_public_urls_are_rejected(raw):
    with pytest.raises(ValueError):
        parse_product_urls(raw)


def test_merchant_url_parser_is_explicit_and_id_based():
    data = parse_product_urls("1=https://shop.example.org/items/1\n\n 2 = https://shop.example.org/items/2 ")
    assert data == {1: "https://shop.example.org/items/1", 2: "https://shop.example.org/items/2"}


def test_gui_review_logic_is_local_and_publish_gate_is_closed_for_incomplete_rows():
    items = [{
        "id": 1, "type": "normal", "name": "お茶", "detail": "", "visible": True,
        "sales_status": "item_now_on_sale", "price": 1000, "stock": 1,
        "modified_at": "2026-10-29T00:00:00Z", "variations": [], "options": [],
        "categories": [], "images": [],
    }]
    result = preview_mapping(items, "shop", "商店", "https://shop.example.org/", "")
    assert not result.publishable
    assert result.issues[0].code == "PUBLIC_URL_REQUIRED"
    result = preview_mapping(items, "shop", "商店", "https://shop.example.org/",
                             "1=https://shop.example.org/items/1")
    assert result.publishable
    assert result.catalog.products[0].is_demo is False
