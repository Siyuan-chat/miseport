"""Tests for BASE's official /items/{id} storefront URL candidate path."""
import pytest

from miseport.base_urls import (
    BaseURLValidationError, candidate_product_urls, validate_manual_product_urls
)


def item(id, visible=True, sales_status="item_now_on_sale", type="normal"):
    return {"id": id, "visible": visible, "sales_status": sales_status, "type": type}


SHOP = "https://shop.example.org/"


def test_batch_url_candidates_require_one_real_confirmed_example():
    rows = [item(33), item(34), item(35, visible=False), item(36, type="digital")]
    with pytest.raises(BaseURLValidationError, match="店主"):
        candidate_product_urls(rows, SHOP, "https://shop.example.org/items/33")
    result = candidate_product_urls(rows, SHOP, "https://shop.example.org/items/33",
                                    merchant_confirmed=True)
    assert result == {
        33: "https://shop.example.org/items/33",
        34: "https://shop.example.org/items/34",
    }


@pytest.mark.parametrize("bad", [
    "https://othershop.example.org/items/33",
    "http://shop.example.org/items/33",
    "https://shop.example.org/items/999",
    "https://shop.example.org/items/34#secret",
    "https://shop.example.org/items/33?next=1",
    "https://shop.example.org/items/0",
    "https://shop.example.org/admin/items/33",
    "https://shop.example.org/items/33?redirect=https://attacker.example",
    "https://shop.example.org/items/33/widget/small",
])
def test_sample_is_exact_confirmed_item_and_store(bad):
    with pytest.raises(BaseURLValidationError):
        candidate_product_urls([item(33), item(34)], SHOP, bad, merchant_confirmed=True)


@pytest.mark.parametrize("bad_home", [
    "http://shop.example.org/", "https://shop.example.org/shop",
    "https://user:pass@shop.example.org/", "https://127.0.0.1/",
    "https://localhost/", "https://internal.local/",
    "https://shop.example.org:8080/", "https://shop.example.org/?shop=1",
    "https://shop.example.org#foo",
    "https://shop.example.org.evil.com/",
])
def test_bad_homepages_or_sample_host_not_accepted(bad_home):
    with pytest.raises(BaseURLValidationError):
        candidate_product_urls([item(33)], bad_home, "https://shop.example.org/items/33",
                               merchant_confirmed=True)


def test_original_item_ids_retain_same_page_for_variations():
    result = candidate_product_urls([item(33), item(34)], SHOP, "https://shop.example.org/items/34",
                                    merchant_confirmed=True)
    assert result[33].endswith("/items/33")


def test_duplicate_ids_and_bad_item_shape_rejected():
    for rows in ([item(33), item(33)], [item("33")], [None]):
        with pytest.raises(BaseURLValidationError):
            candidate_product_urls(rows, SHOP, "https://shop.example.org/items/33",
                                   merchant_confirmed=True)


def test_manual_product_urls_must_match_shop_and_item_id():
    validate_manual_product_urls({33: "https://shop.example.org/items/33"}, SHOP)
    for wrong in (
        {33: "https://othershop.example.org/items/33"},
        {33: "https://shop.example.org/items/34"},
        {33: "https://shop.example.org/items/33?tracked=1"},
        {33: "http://shop.example.org/items/33"},
    ):
        with pytest.raises(BaseURLValidationError):
            validate_manual_product_urls(wrong, SHOP)
