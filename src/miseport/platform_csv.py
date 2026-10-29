"""Read-only official merchant product CSV adapters (BASE / Shopify snapshots).

This module never uploads files back to a shop, reads orders/customers, or
infers current inventory when it is not included in the provided export.
CSV rows are snapshots confirmed by the merchant, not live API results.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import csv
from hashlib import sha256
import io
from pathlib import Path
import re
from typing import Mapping
from urllib.parse import urlsplit

from .base_urls import BaseURLValidationError, candidate_product_urls, _store_origin
from .core import Catalog, Product
from .source_adapters import MerchantProfile

MAX_CSV_BYTES = 10 * 1024 * 1024
MAX_CSV_ROWS = 10000
HANDLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$", re.ASCII)
FORBIDDEN_COLUMNS = frozenset({
    "注文ID", "注文番号", "顧客ID", "顧客名", "メールアドレス",
    "氏名", "電話番号", "住所", "Customer Email",
})


class PlatformCSVError(ValueError):
    """No credentials or arbitrary CSV cell contents are echoed."""


@dataclass(frozen=True)
class CSVIssue:
    row: int
    code: str
    message: str
    blocking: bool = True


@dataclass
class CSVImportResult:
    catalog: Catalog
    platform: str
    source_rows: int
    issues: list[CSVIssue] = field(default_factory=list)

    @property
    def publishable(self) -> bool:
        return bool(self.catalog.products) and not any(x.blocking for x in self.issues)

    def summary(self) -> dict:
        return {"platform": self.platform, "source_rows": self.source_rows,
                "mapped_products": len(self.catalog.products), "publishable": self.publishable,
                "issues": [vars(x) for x in self.issues]}


def _load_rows(path: str | Path, *, platform: str):
    path = Path(path)
    try:
        with path.open("rb") as f:
            raw = f.read(MAX_CSV_BYTES + 1)
    except OSError:
        raise PlatformCSVError("商品CSVファイルを読み込めません。") from None
    if len(raw) > MAX_CSV_BYTES:
        raise PlatformCSVError("商品CSVは10 MiB以下にしてください。")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        if platform != "base":
            raise PlatformCSVError("Shopifyの商品CSVはUTF-8で保存してください。") from None
        try:
            text = raw.decode("cp932")
        except UnicodeError:
            raise PlatformCSVError("商品CSVの文字コードを確認してください。") from None
    reader = csv.DictReader(io.StringIO(text), strict=True)
    fields = reader.fieldnames
    if (not fields or len(fields) != len(set(fields))
            or any(not name for name in fields)):
        raise PlatformCSVError("商品CSVの列名を確認してください。")
    if set(fields) & FORBIDDEN_COLUMNS:
        raise PlatformCSVError("注文・顧客情報を含むCSVは取り込めません。商品CSVを選んでください。")
    rows = []
    try:
        for row in reader:
            if None in row:
                raise PlatformCSVError("商品CSVの列数が一致しません。")
            rows.append(row)
            if len(rows) > MAX_CSV_ROWS:
                raise PlatformCSVError("商品CSVは10000行以下にしてください。")
    except csv.Error:
        raise PlatformCSVError("商品CSVを読み取れません。") from None
    return set(fields), rows


def _price(value) -> int:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("empty price")
    v = value.strip()
    if len(v) > 18:
        raise ValueError("price too large")
    try:
        dec = Decimal(v)
    except InvalidOperation:
        raise ValueError("invalid JPY price") from None
    if not dec.is_finite() or dec < 0 or dec != dec.to_integral_value():
        raise ValueError("non-integer JPY price")
    return int(dec)


def _stock(value, *, trusted: bool) -> tuple[str, int | None]:
    if not trusted or not isinstance(value, str) or not value.strip():
        return "unknown", None
    if not value.isascii() or not value.isdigit():
        return "unknown", None
    quantity = int(value)
    return ("in_stock" if quantity > 0 else "out_of_stock"), quantity


def _timestamp(value: datetime | None):
    stamp = value or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise PlatformCSVError("商品確認日時にはタイムゾーンが必要です。")
    return stamp


def _merchant_profile(profile: MerchantProfile):
    if not isinstance(profile, MerchantProfile):
        raise PlatformCSVError("店舗情報の形式を確認してください。")
    try:
        origin = _store_origin(profile.merchant_homepage)
    except BaseURLValidationError:
        raise PlatformCSVError("店舗の公開URLを確認してください。") from None
    if urlsplit(profile.merchant_homepage).path not in ("", "/"):
        raise PlatformCSVError("店舗トップのURLを指定してください。")
    return origin


def _catalog_result(products, issues, platform, count):
    try:
        result = Catalog(products)
    except ValueError:
        issues.append(CSVIssue(0, "DUPLICATE_SKU", "商品や種類の識別子が重複しています。"))
        result = Catalog([])
    return CSVImportResult(result, platform, count, issues)


def import_base_product_csv(
    path: str | Path, merchant: MerchantProfile, *,
    confirmed_example_url: str, merchant_confirmed: bool,
    verified_at: datetime | None = None
) -> CSVImportResult:
    """Import BASE's official product export columns, no backend writes.

    A CSV has no trustworthy source modified_at: store the merchant's explicit
    verification time and disclose this as a dated CSV snapshot.
    """
    _merchant_profile(merchant)
    headers, rows = _load_rows(path, platform="base")
    if not {"商品ID", "商品名", "価格", "公開状態"} <= headers:
        raise PlatformCSVError("BASEの商品管理CSVではありません。必要な列を確認してください。")
    stamp = _timestamp(verified_at)
    raw_items = {}
    issues = []
    for n, row in enumerate(rows, 2):
        rid = (row.get("商品ID") or "").strip()
        if not rid.isascii() or not rid.isdigit() or int(rid) < 1:
            issues.append(CSVIssue(n, "ITEM_ID_REQUIRED", "既存商品の商品IDが必要です。"))
            continue
        item_id = int(rid)
        visible = (row.get("公開状態") or "").strip()
        if visible == "0":
            continue
        if visible != "1":
            issues.append(CSVIssue(n, "UNKNOWN_PUBLICATION", "公開状態を確認してください。"))
            continue
        if item_id in raw_items and not (row.get("種類ID") or "").strip():
            issues.append(CSVIssue(n, "DUPLICATE_ITEM", "商品IDが重複しています。"))
            continue
        raw_items[item_id] = True
    eligible = [{"id": i, "visible": True, "sales_status": "item_now_on_sale", "type": "normal"}
                for i in sorted(raw_items)]
    try:
        source_urls = candidate_product_urls(eligible, merchant.merchant_homepage,
                 confirmed_example_url, merchant_confirmed=merchant_confirmed)
    except BaseURLValidationError as exc:
        issues.append(CSVIssue(0, "URL_CONFIRMATION_REQUIRED", str(exc)))
        source_urls = {}
    products=[]
    for n,row in enumerate(rows,2):
        rid=(row.get("商品ID") or "").strip()
        if not rid.isdigit() or int(rid) not in raw_items:
            continue
        item_id=int(rid)
        if (row.get("公開状態") or "").strip()!="1":
            continue
        raw_url=source_urls.get(item_id)
        if not raw_url:
            issues.append(CSVIssue(n, "SOURCE_URL_REQUIRED", "公開商品のURLが未確認です。"))
            continue
        name=(row.get("商品名") or "").strip()
        if not name:
            issues.append(CSVIssue(n, "NAME_REQUIRED", "商品名が未設定です。"))
            continue
        try:
            price=_price(row.get("価格"))
        except ValueError:
            issues.append(CSVIssue(n, "PRICE_UNKNOWN", "正しい税込JPY価格が必要です。"))
            continue
        variation_id=(row.get("種類ID") or "").strip()
        variation_name=(row.get("種類名") or "").strip()
        if variation_id and (not variation_id.isascii() or not variation_id.isdigit()
                             or int(variation_id)<1):
            issues.append(CSVIssue(n, "INVALID_VARIATION_ID", "種類IDを確認してください。"))
            continue
        if variation_name and not variation_id:
            issues.append(CSVIssue(n, "VARIATION_ID_REQUIRED", "種類IDが必要です。"))
            continue
        stock, quantity=_stock(row.get("種類在庫数") if variation_id else row.get("在庫数"),
                              trusted=True)
        try:
            products.append(Product(
                sku="base-"+str(item_id)+(("-"+variation_id) if variation_id else ""),
                name=name+(" / "+variation_name if variation_name else ""),
                description=(row.get("説明") or ""), category="",
                price_jpy=price, tax_included=True, shipping_jpy=None,
                stock=stock, stock_quantity=quantity, source_url=raw_url,
                updated_at=stamp, snapshot_at=stamp, is_demo=merchant.is_demo,
                merchant_id=merchant.merchant_id, merchant_name=merchant.merchant_name,
                merchant_homepage=merchant.merchant_homepage))
        except ValueError:
            issues.append(CSVIssue(n,"INVALID_PRODUCT","必須項目を確認してください。"))
    if products:
        issues.append(CSVIssue(0, "CSV_VERIFIED_AT",
            "商品更新日時ではなく、店主がCSVを確認した日時を記録しています。", False))
    return _catalog_result(products,issues,"base-csv",len(rows))


def import_shopify_product_csv(
    path: str | Path, merchant: MerchantProfile, *,
    confirmed_example_url: str, merchant_confirmed: bool, currency_jpy: bool,
    single_location: bool = False, verified_at: datetime | None = None
) -> CSVImportResult:
    """Import Shopify's official current/legacy product CSV read-only.

    Requires explicit online-store publication and merchant JPY confirmation.
    Multilocation inventory remains unknown; no assumptions about tax/shipping.
    """
    origin=_merchant_profile(merchant)
    fields, rows=_load_rows(path,platform="shopify")
    handle_field="URL handle" if "URL handle" in fields else "Handle"
    price_field="Price" if "Price" in fields else "Variant Price"
    sku_field="SKU" if "SKU" in fields else "Variant SKU"
    stock_field="Inventory quantity" if "Inventory quantity" in fields else "Variant Inventory Qty"
    pub_field=("Published on online store" if "Published on online store" in fields
               else "Published")
    if not {handle_field,"Title",price_field,pub_field} <= fields:
        raise PlatformCSVError("Shopifyの商品CSVの必須列を確認してください。")
    if currency_jpy is not True:
        raise PlatformCSVError("このショップの販売通貨がJPYであることを確認してください。")
    if merchant_confirmed is not True:
        raise PlatformCSVError("店舗の公開商品URLを確認してください。")
    try:
        sample=urlsplit(confirmed_example_url)
        if _store_origin(confirmed_example_url)!=origin or sample.query or sample.fragment:
            raise ValueError()
        if not re.fullmatch(r"/products/[A-Za-z0-9][A-Za-z0-9-]*",sample.path):
            raise ValueError()
    except (BaseURLValidationError,ValueError):
        raise PlatformCSVError("Shopifyの公開商品URL例を確認してください。") from None
    sample_handle=sample.path.split("/")[-1]
    handles={(row.get(handle_field) or "").strip() for row in rows}
    if sample_handle not in handles:
        raise PlatformCSVError("URL例の商品ハンドルがCSVに含まれていません。")
    stamp=_timestamp(verified_at)
    issues=[]
    products=[]
    metadata={}
    for n,row in enumerate(rows,2):
        handle=(row.get(handle_field) or "").strip()
        if not HANDLE.fullmatch(handle):
            issues.append(CSVIssue(n,"INVALID_HANDLE","商品ハンドルを確認してください。"))
            continue
        title=(row.get("Title") or "").strip()
        state=(row.get("Status") or "").strip().lower()
        visible=(row.get(pub_field) or "").strip().lower()
        if title or state or visible:
            meta=metadata.setdefault(handle,{"title":"","status":"","published":""})
            if title: meta["title"]=title
            if state: meta["status"]=state
            if visible: meta["published"]=visible
        meta=metadata.setdefault(handle,{"title":"","status":"","published":""})
        if meta["published"] in ("false","0"):
            continue
        if meta["published"] not in ("true","1"):
            issues.append(CSVIssue(n,"PUBLICATION_UNKNOWN","オンラインストアの公開状態を確認してください。"))
            continue
        if "Status" in fields and meta["status"] != "active":
            if meta["status"] in ("draft","archived"):
                continue
            issues.append(CSVIssue(n,"STATUS_UNKNOWN","商品ステータスを確認してください。"))
            continue
        price_string=(row.get(price_field) or "").strip()
        sku_raw=(row.get(sku_field) or "").strip()
        options=[(row.get(k) or "").strip() for k in
                 ("Option1 value","Option2 value","Option3 value",
                  "Option1 Value","Option2 Value","Option3 Value")]
        if not price_string and not sku_raw and not any(options):
            continue  # Shopify image-only continuation row, not a product variant.
        if not meta["title"]:
            issues.append(CSVIssue(n,"NAME_REQUIRED","商品名が必要です。"))
            continue
        try:
            price=_price(price_string)
        except ValueError:
            issues.append(CSVIssue(n,"PRICE_UNKNOWN","整数JPY価格が必要です。"))
            continue
        # Stable identity for missing SKU; do not pretend this is Shopify's
        # internal variant ID (not provided by the CSV).
        stable_key=sku_raw or "|".join([handle]+options)
        if not stable_key or not stable_key.strip("|"):
            issues.append(CSVIssue(n,"SKU_UNKNOWN","SKU/種類を確認してください。"))
            continue
        digest=sha256((handle+"\\x00"+stable_key).encode()).hexdigest()[:20]
        slug="shopify-"+digest
        qty,stock_quantity=_stock(row.get(stock_field),trusted=single_location)
        try:
            products.append(Product(
                sku=slug, name=meta["title"], description=(row.get("Description") or
                    row.get("Body (HTML)") or ""), category=(row.get("Type") or ""),
                price_jpy=price, stock=qty, stock_quantity=stock_quantity,
                tax_included=None, shipping_jpy=None,
                source_url=origin+"/products/"+handle,
                updated_at=stamp,snapshot_at=stamp,is_demo=merchant.is_demo,
                merchant_id=merchant.merchant_id,merchant_name=merchant.merchant_name,
                merchant_homepage=merchant.merchant_homepage))
        except ValueError:
            issues.append(CSVIssue(n,"INVALID_PRODUCT","商品情報を確認してください。"))
    if products:
        issues.append(CSVIssue(0,"CSV_SOURCE_TIME_UNKNOWN",
            "元の最終更新時刻はCSVから取得できません。店主の確認日時を記録しています。",False))
        if not single_location:
            issues.append(CSVIssue(0,"MULTI_LOCATION_STOCK_UNKNOWN",
                "複数倉庫の在庫は不明として扱います。",False))
    return _catalog_result(products,issues,"shopify-csv",len(rows))
