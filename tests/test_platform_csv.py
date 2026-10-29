"""Offline official CSV sample tests: never read customer data or write shops."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from miseport.platform_csv import (
    PlatformCSVError, import_base_product_csv, import_shopify_product_csv
)
from miseport.source_adapters import MerchantProfile


def profile():
    return MerchantProfile(
        merchant_id="shop", merchant_name="京都茶屋",
        merchant_homepage="https://shop.example.org/",
        verified_product_urls={}, is_demo=True,
    )


def sample(tmp_path, content, encoding="utf-8", name="merchant.csv"):
    f=tmp_path / name
    f.write_bytes(content.encode(encoding))
    return f


def base(tmp_path, content, **kwargs):
    return import_base_product_csv(
        sample(tmp_path,content,kwargs.pop("encoding","utf-8")),
        profile(), confirmed_example_url="https://shop.example.org/items/1",
        merchant_confirmed=True,
        verified_at=datetime(2026,10,29,tzinfo=timezone.utc),**kwargs,
    )


def shopify(tmp_path, content, **kwargs):
    return import_shopify_product_csv(
        sample(tmp_path,content),profile(),
        confirmed_example_url="https://shop.example.org/products/tea",
        merchant_confirmed=True,currency_jpy=True,
        verified_at=datetime(2026,10,29,tzinfo=timezone.utc),**kwargs,
    )


def test_base_official_csv_normal_item_utf8_and_cp932(tmp_path):
    text=("商品ID,商品名,価格,公開状態,在庫数,説明\n"
          "1,京都ほうじ茶,1850,1,12,産地:京都府\n"
          "2,非公開のお茶,5000,0,2,非公開\n")
    for encoding in ("utf-8-sig","cp932"):
        r=base(tmp_path,text,encoding=encoding)
        assert r.publishable and r.source_rows==2
        assert [p.sku for p in r.catalog.products] == ["base-1"]
        item=r.catalog.products[0]
        assert item.stock_quantity==12 and item.tax_included is True
        assert item.shipping_jpy is None
        assert item.source_url=="https://shop.example.org/items/1"
        assert any(i.code=="CSV_VERIFIED_AT" for i in r.issues)


def test_base_csv_variants_keep_ids_and_individual_stock(tmp_path):
    text=("商品ID,商品名,価格,公開状態,種類ID,種類名,種類在庫数\n"
          "1,お茶,1500,1,44,缶,2\n"
          "1,お茶,1500,1,45,袋,0\n")
    r=base(tmp_path,text)
    assert r.publishable
    assert [p.sku for p in r.catalog.products]==["base-1-44","base-1-45"]
    assert [p.stock_quantity for p in r.catalog.products]==[2,0]
    assert r.catalog.products[0].name.endswith("缶")


@pytest.mark.parametrize("bad_text,expected", [
    ("商品ID,商品名,価格,公開状態\n1,茶,,1\n","PRICE_UNKNOWN"),
    ("商品ID,商品名,価格,公開状態\n1,茶,8.50,1\n","PRICE_UNKNOWN"),
    ("商品ID,商品名,価格,公開状態\n1,茶,1500,\n","UNKNOWN_PUBLICATION"),
    ("商品ID,商品名,価格,公開状態\n,茶,1500,1\n","ITEM_ID_REQUIRED"),
    ("商品ID,商品名,価格,公開状態,種類名\n1,茶,1000,1,缶\n","VARIATION_ID_REQUIRED"),
])
def test_base_blocks_unverified_or_ambiguous_csv_fields(tmp_path,bad_text,expected):
    r=base(tmp_path,bad_text)
    assert not r.publishable
    assert expected in {i.code for i in r.issues}


def test_base_requires_confirmed_real_example(tmp_path):
    f=sample(tmp_path,"商品ID,商品名,価格,公開状態\n1,茶,1500,1\n")
    r=import_base_product_csv(f,profile(),confirmed_example_url="https://evil.example.org/items/1",
         merchant_confirmed=True)
    assert not r.publishable
    assert "URL_CONFIRMATION_REQUIRED" in {i.code for i in r.issues}


def test_rejects_customer_order_csv_before_import(tmp_path):
    text="商品ID,商品名,価格,公開状態,メールアドレス\n1,茶,1000,1,secret@example.org\n"
    with pytest.raises(PlatformCSVError,match="顧客"):
        base(tmp_path,text)


def test_base_requires_official_headers(tmp_path):
    with pytest.raises(PlatformCSVError,match="BASE"):
        base(tmp_path,"Name,Price\nTea,1000\n")


def test_shopify_current_csv_imports_published_variant_and_unknown_location_stock(tmp_path):
    text=("URL handle,Title,Status,Published on online store,Price,SKU,"
          "Option1 name,Option1 value,Inventory quantity,Type\n"
          "tea,ほうじ茶,active,true,2000,TEA-01,Size,Small,25,茶\n")
    r=shopify(tmp_path,text)
    assert r.publishable
    p=r.catalog.products[0]
    assert p.name=="ほうじ茶" and p.price_jpy==2000
    assert p.stock.value=="unknown" and p.stock_quantity is None
    assert p.tax_included is None and p.shipping_jpy is None
    assert p.source_url=="https://shop.example.org/products/tea"
    assert any(i.code=="MULTI_LOCATION_STOCK_UNKNOWN" for i in r.issues)
    one=shopify(tmp_path,text,single_location=True)
    assert one.catalog.products[0].stock_quantity==25


def test_shopify_legacy_csv_and_image_only_continuation(tmp_path):
    text=("Handle,Title,Published,Variant Price,Variant SKU,Variant Inventory Qty,Image Src\n"
          "tea,お茶,TRUE,1200,T-A,2,https://cdn.example.org/1.png\n"
          "tea,,,,,,https://cdn.example.org/2.png\n")
    r=shopify(tmp_path,text,single_location=True)
    assert r.publishable and len(r.catalog.products)==1
    assert r.catalog.products[0].price_jpy==1200


def test_shopify_draft_and_hidden_not_published(tmp_path):
    text=("URL handle,Title,Status,Published on online store,Price,SKU\n"
          "tea,非公開,draft,false,1500,D-01\n")
    r=shopify(tmp_path,text)
    assert not r.publishable and len(r.catalog.products)==0


@pytest.mark.parametrize("price",["","abc","10.50","-5","Infinity"])
def test_shopify_rejects_unverified_jpy_prices(tmp_path,price):
    text=("URL handle,Title,Status,Published on online store,Price,SKU\n"
          "tea,茶,active,true,"+price+",TEA\n")
    r=shopify(tmp_path,text)
    assert not r.publishable
    assert "PRICE_UNKNOWN" in {i.code for i in r.issues}


def test_shopify_needs_confirmed_store_currency(tmp_path):
    f=sample(tmp_path,"URL handle,Title,Published on online store,Price\ntea,茶,true,1200\n")
    with pytest.raises(PlatformCSVError,match="JPY"):
        import_shopify_product_csv(f,profile(),confirmed_example_url="https://shop.example.org/products/tea",
                                   merchant_confirmed=True,currency_jpy=False)


def test_shopify_duplicate_skus_block_publication(tmp_path):
    text=("URL handle,Title,Status,Published on online store,Price,SKU\n"
          "tea,茶,active,true,1200,TEA\n"
          "tea,,active,true,1800,TEA\n")
    r=shopify(tmp_path,text)
    assert not r.publishable
    assert any(i.code=="DUPLICATE_SKU" for i in r.issues)


def test_shopify_bad_url_example_fails(tmp_path):
    text=("URL handle,Title,Published on online store,Price\ntea,茶,true,1200\n")
    f=sample(tmp_path,text)
    with pytest.raises(PlatformCSVError):
        import_shopify_product_csv(f,profile(),confirmed_example_url="https://evil.example.org/products/tea",
                    merchant_confirmed=True,currency_jpy=True)
