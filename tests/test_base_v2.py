"""Offline tests for BASE v2 read-only product ingestion."""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from miseport.base_v2 import BaseAPIError, BaseV2Client, map_base_items


def item(number=1, **updates):
    data = {
        "id": number,
        "type": "normal",
        "name": "京都ほうじ茶",
        "detail": "茶葉100g",
        "visible": True,
        "sales_status": "item_now_on_sale",
        "price": 1850,
        "stock": 12,
        "identifier": None,
        "modified_at": "2026-10-29T00:00:00Z",
        "categories": [{"id": 1, "name": "日本茶", "parent": None}],
        "images": [],
        "variations": [],
        "options": [],
        "item_tax_type": "reduced",
    }
    data.update(updates)
    return data


def encode(data):
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def test_client_reads_all_pages_with_fixed_public_filter_and_no_token_in_url():
    records = []
    def fake(url, headers, timeout):
        records.append((url, headers, timeout))
        return 200, encode([item(1), item(2)] if len(records) == 1 else [item(3)])
    rows = BaseV2Client(transport=fake).fetch_items("example-secret", limit=2)
    assert [r["id"] for r in rows] == [1, 2, 3]
    assert len(records) == 2
    assert all(x[0].startswith("https://apiv2.thebase.com/api/items?") for x in records)
    assert all("visible=true" in x[0] and "example-secret" not in x[0] for x in records)
    assert "offset=0" in records[0][0] and "offset=2" in records[1][0]
    assert all(x[1]["Authorization"] == "Bearer example-secret" for x in records)


def test_exact_page_limit_fetches_empty_final_page():
    pages = [[item(1)], []]
    reads = []
    def fake(url, headers, timeout):
        reads.append(url)
        return 200, encode(pages.pop(0))
    assert len(BaseV2Client(transport=fake).fetch_items("pat", limit=1)) == 1
    assert len(reads) == 2


@pytest.mark.parametrize("status,phrase", [(401, "401/403"), (403, "401/403"), (429, "429"), (500, "500"), (302, "リダイレクト")])
def test_client_errors_are_safe_and_never_echo_secrets(status, phrase):
    client = BaseV2Client(transport=lambda *_: (status, b"secret PAT: my-hidden-pat"))
    with pytest.raises(BaseAPIError, match=phrase) as err:
        client.fetch_items("my-hidden-pat")
    assert "my-hidden-pat" not in str(err.value)


def test_untrusted_transport_exception_is_redacted():
    def fake(*args):
        raise RuntimeError("Bearer my-hidden-pat")
    with pytest.raises(BaseAPIError) as err:
        BaseV2Client(transport=fake).fetch_items("my-hidden-pat")
    assert "my-hidden-pat" not in str(err.value)


@pytest.mark.parametrize("payload", [b"{", b'{"id":1,"id":2}', encode({"items": []}), encode([{"id": "3"}])])
def test_client_rejects_invalid_or_unexpected_response(payload):
    with pytest.raises(BaseAPIError):
        BaseV2Client(transport=lambda *_: (200, payload)).fetch_items("pat")


def test_client_rejects_duplicate_ids_across_pages():
    pages = [[item(1)], [item(1)]]
    def fake(*args):
        return 200, encode(pages.pop(0))
    with pytest.raises(BaseAPIError, match="重複"):
        BaseV2Client(transport=fake).fetch_items("pat", limit=1)


def test_client_rejects_response_with_more_than_requested_limit():
    with pytest.raises(BaseAPIError, match="形式"):
        BaseV2Client(transport=lambda *_: (200, encode([item(1), item(2)]))).fetch_items("pat", limit=1)


def test_client_rejects_bad_pat_and_limit_before_network():
    def no_network(*_):
        raise AssertionError("should not reach network")
    client = BaseV2Client(transport=no_network)
    for pat in ("", " abc", "secret\nBearer fake", "with space"):
        with pytest.raises(BaseAPIError):
            client.fetch_items(pat)
    for limit in (0, 101, True, "10"):
        with pytest.raises(ValueError):
            client.fetch_items("pat", limit=limit)


def test_client_explicit_variations_path_and_shape():
    urls = []
    def fake(url, headers, timeout):
        urls.append(url)
        return 200, encode({"variations": [{"id": 2, "name": "M", "stock": 3, "identifier": None}]})
    out = BaseV2Client(transport=fake).fetch_variations("pat", 3)
    assert out[0]["id"] == 2
    assert urls == ["https://apiv2.thebase.com/api/items/3/variations"]
    with pytest.raises(ValueError):
        BaseV2Client(transport=fake).fetch_variations("pat", 0)


def kwargs(**updates):
    opts = dict(
        merchant_id="tea-shop", merchant_name="茶の店",
        merchant_homepage="https://shop.example.org/",
        source_urls={1: "https://shop.example.org/items/1"},
        snapshot_at=datetime(2026, 10, 29, tzinfo=timezone.utc),
        is_demo=True,
    )
    opts.update(updates)
    return opts


def test_mapping_normal_product_preserves_source_price_stock_tax_and_unknown_shipping():
    result = map_base_items([item()], **kwargs())
    assert result.publishable and result.summary()["fetched_items"] == 1
    product = result.catalog.products[0]
    assert product.sku == "base-1" and product.price_jpy == 1850
    assert product.stock_quantity == 12 and product.stock.value == "in_stock"
    assert product.tax_included is True and product.shipping_jpy is None
    assert product.source_url == "https://shop.example.org/items/1"
    assert product.updated_at.isoformat() == "2026-10-29T00:00:00+00:00"
    assert product.is_demo is True
    assert result.catalog.quote("base-1")["complete_total"] is False


def test_mapping_variation_uses_ids_and_individual_stock():
    one = item(1, variations=[
        {"id": 21, "name": "茶袋", "stock": 5, "identifier": "BAG"},
        {"id": 22, "name": "缶", "stock": 0, "identifier": "TIN"},
    ], stock=5)
    result = map_base_items([one], **kwargs())
    assert result.publishable
    assert [p.sku for p in result.catalog.products] == ["base-1-21", "base-1-22"]
    assert [p.stock.value for p in result.catalog.products] == ["in_stock", "out_of_stock"]
    assert result.catalog.products[1].name.endswith("缶")
    assert all(p.source_url == "https://shop.example.org/items/1" for p in result.catalog.products)


def test_mapping_nonpublic_and_not_on_sale_not_exported():
    result = map_base_items([
        item(1, visible=False), item(2, sales_status="item_waiting_for_sale"),
        item(3, type="digital"),
    ], **kwargs(source_urls={1: "https://shop.example.org/1",
                             2: "https://shop.example.org/2",
                             3: "https://shop.example.org/3"}))
    assert len(result.catalog.products) == 0
    assert not result.publishable
    assert {i.code for i in result.issues} == {"NOT_ON_SALE", "UNSUPPORTED_TYPE"}
    assert all(not i.blocking for i in result.issues)


def test_missing_price_public_url_or_complex_options_blocks_publication():
    catalog = [
        item(1, price=None),
        item(2, price=2000),
        item(3, options=[{"option_type": "form", "extra_price": 500}]),
        item(4, stock=10),
    ]
    result = map_base_items(catalog, **kwargs(
        source_urls={2: "", 3: "https://shop.example.org/3", 4: "https://shop.example.org/4"}))
    assert len(result.catalog.products) == 1
    assert not result.publishable
    assert {x.code for x in result.issues} == {
        "PRICE_UNKNOWN", "PUBLIC_URL_REQUIRED", "COMPLEX_OPTIONS"
    }


def test_invalid_or_duplicate_variation_and_bad_url_do_not_silently_publish():
    one = item(1, variations=[
        {"id": 2, "stock": 5},
        {"id": 2, "stock": 3},
    ])
    result = map_base_items([one], **kwargs())
    assert not result.publishable
    assert any(x.code == "DUPLICATE_SKU" for x in result.issues)
    other = map_base_items([item()], **kwargs(source_urls={1: "javascript:alert(1)"}))
    assert not other.publishable
    assert other.summary()["issues"][0]["code"] == "INVALID_PRODUCT"


def test_mapping_refuses_unverified_homepage_and_timestamp():
    result = map_base_items([item(modified_at="not-a-time")], **kwargs())
    assert not result.publishable
    assert result.issues[0].code == "INVALID_PRODUCT"
    with pytest.raises(ValueError):
        map_base_items([item()], **kwargs(snapshot_at=datetime(2026, 10, 29)))


def test_mapping_uses_only_explicit_urls_not_admin_links():
    row = item(_links={"update_item": {"href": "https://apiv2.thebase.com/api/items/1"}},
               public_url="https://shop.example.org/items/guess")
    result = map_base_items([row], **kwargs(source_urls={}))
    assert not result.publishable
    assert result.issues[0].code == "PUBLIC_URL_REQUIRED"


def test_mapper_is_not_a_write_operation(tmp_path):
    dest = tmp_path / "existing.json"
    dest.write_text('{"untouched":true}', encoding="utf-8")
    result = map_base_items([item(price=None)], **kwargs())
    assert not result.publishable
    assert dest.read_text(encoding="utf-8") == '{"untouched":true}'
