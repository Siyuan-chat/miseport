"""BASE API v2 beta read-only product ingestion.

Source: https://apiv2.thebase.com/docs/endpoints/get-api-items/
This module never writes to a shop, stores PATs, or guesses public item URLs.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .core import Catalog, Product

BASE_API_ORIGIN = "https://apiv2.thebase.com"
PAGE_LIMIT = 100
MAX_ITEMS = 10000
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class BaseAPIError(ValueError):
    """Safe-to-display error; does not contain credentials or raw API bodies."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _network_get(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    """Production transport: fixed HTTPS origin and no credential-bearing redirects."""
    if not url.startswith(BASE_API_ORIGIN + "/api/"):
        raise BaseAPIError("APIの接続先が正しくありません。")
    opener = build_opener(_NoRedirect())
    request = Request(url, headers=headers, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
            return response.status, data
    except HTTPError as exc:
        # Do not echo exception, response URL, headers, or body (credentials may occur).
        return exc.code, b""
    except (URLError, TimeoutError, OSError) as exc:
        raise BaseAPIError("BASEへの接続に失敗しました。通信環境を確認してください。") from None


def _distinct_fields(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


class BaseV2Client:
    """Read-only BASE item API. PAT is supplied per request and never retained."""

    def __init__(self, transport: Callable | None = None, timeout: float = 15.0):
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 1 <= timeout <= 60:
            raise ValueError("timeout must be 1..60 seconds")
        self._transport = transport or _network_get
        self.timeout = float(timeout)

    def _get_json(self, path: str, token: str, params: dict | None = None):
        if not isinstance(token, str) or not token or token != token.strip() or any(
                ord(char) < 33 or ord(char) == 127 for char in token):
            raise BaseAPIError("BASEの認証情報を確認してください。")
        if not path.startswith("/api/items") or any(symbol in path for symbol in ("?", "#", "\\")):
            raise ValueError("invalid BASE read path")
        url = BASE_API_ORIGIN + path
        if params:
            url += "?" + urlencode(params)
        headers = {
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "User-Agent": "MisePort/0.1 (read-only catalog importer)",
        }
        try:
            status, data = self._transport(url, headers, self.timeout)
        except BaseAPIError:
            raise
        except Exception:
            # Injected transport exceptions must never leak request headers or token.
            raise BaseAPIError("BASEへの接続に失敗しました。") from None
        if status in (401, 403):
            raise BaseAPIError("BASEの認証・読み取り権限を確認してください（401/403）。")
        if status == 429:
            raise BaseAPIError("BASEのAPI利用上限に達しました。時間を置いて再試行してください（429）。")
        if status in (301, 302, 303, 307, 308):
            raise BaseAPIError("BASE APIからリダイレクトされました。安全のため処理を停止します。")
        if status != 200:
            raise BaseAPIError("BASE APIがエラーを返しました（HTTP " + str(status) + "）。")
        if not isinstance(data, bytes) or len(data) > MAX_RESPONSE_BYTES:
            raise BaseAPIError("BASE APIの応答サイズが大きすぎます。")
        try:
            return json.loads(data.decode("utf-8"), object_pairs_hook=_distinct_fields)
        except (UnicodeError, ValueError, RecursionError):
            raise BaseAPIError("BASE APIの応答を読み取れません。") from None

    def fetch_items(self, token: str, limit: int = PAGE_LIMIT) -> list[dict]:
        """Fetch *complete* visible list or raise; never return a partial snapshot."""
        if type(limit) is not int or not 1 <= limit <= PAGE_LIMIT:
            raise ValueError("limit must be 1..100")
        items = []
        seen = set()
        offset = 0
        while True:
            page = self._get_json(
                "/api/items", token, {"visible": "true", "limit": limit, "offset": offset}
            )
            if not isinstance(page, list) or len(page) > limit:
                raise BaseAPIError("BASEの商品一覧形式が想定と異なります。")
            for item in page:
                if not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] < 1:
                    raise BaseAPIError("BASEの商品IDが不正です。")
                if item["id"] in seen:
                    raise BaseAPIError("BASEのページ間に重複商品があります。再取得してください。")
                seen.add(item["id"])
                items.append(item)
                if len(items) > MAX_ITEMS:
                    raise BaseAPIError("商品件数が上限を超えました。")
            if len(page) < limit:
                break
            offset += len(page)
            if offset > 1_000_000:
                raise BaseAPIError("BASE APIのページ番号が上限を超えました。")
        return items

    def fetch_variations(self, token: str, item_id: int) -> list[dict]:
        """Optional explicit refresh; list responses already embed variations."""
        if type(item_id) is not int or item_id < 1:
            raise ValueError("item_id must be a positive integer")
        data = self._get_json("/api/items/" + str(item_id) + "/variations", token)
        if not isinstance(data, dict) or not isinstance(data.get("variations"), list):
            raise BaseAPIError("BASEの種類一覧形式が想定と異なります。")
        return data["variations"]


@dataclass(frozen=True)
class MappingIssue:
    item_id: int | None
    code: str
    message: str
    blocking: bool = True


@dataclass
class BaseMappingResult:
    """The Catalog may be previewed, but must not publish with blocking issues."""
    catalog: Catalog
    issues: list[MappingIssue] = field(default_factory=list)
    fetched_count: int = 0

    @property
    def publishable(self) -> bool:
        return bool(self.catalog.products) and not any(issue.blocking for issue in self.issues)

    def summary(self) -> dict:
        return {
            "fetched_items": self.fetched_count,
            "mapped_products": len(self.catalog.products),
            "publishable": self.publishable,
            "issues": [
                {"item_id": i.item_id, "code": i.code, "message": i.message,
                 "blocking": i.blocking} for i in self.issues
            ],
        }


def map_base_items(
    items: list[dict], *,
    merchant_id: str, merchant_name: str, merchant_homepage: str,
    source_urls: Mapping[int, str],
    is_demo: bool, snapshot_at: datetime | None = None
) -> BaseMappingResult:
    """Map only verified, currently-for-sale BASE normal products.

    The BASE API exposes admin _links, not an authoritative public product URL
    in its documented item schema. Source URLs must be confirmed by the merchant.
    Nullable price and options with additional charges cannot be silently mapped.
    """
    if type(is_demo) is not bool:
        raise ValueError("is_demo must be a boolean")
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ValueError("too many items")
    timestamp = snapshot_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("snapshot must have timezone")
    products = []
    issues = []
    seen = set()
    for item in items:
        item_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(item, dict) or type(item_id) is not int or item_id < 1 or item_id in seen:
            issues.append(MappingIssue(None, "INVALID_OR_DUPLICATE_ID", "商品IDを確認してください。"))
            continue
        seen.add(item_id)
        if item.get("visible") is not True or item.get("sales_status") != "item_now_on_sale":
            issues.append(MappingIssue(item_id, "NOT_ON_SALE", "非公開または販売対象外のため除外しました。", False))
            continue
        if item.get("type") != "normal":
            issues.append(MappingIssue(item_id, "UNSUPPORTED_TYPE", "この販売方式は未対応のため除外しました。", False))
            continue
        price = item.get("price")
        if type(price) is not int or price < 0:
            issues.append(MappingIssue(item_id, "PRICE_UNKNOWN", "税込価格が未確定のため公開できません。"))
            continue
        if item.get("options"):
            issues.append(MappingIssue(item_id, "COMPLEX_OPTIONS", "追加料金を含む商品オプションは未対応です。"))
            continue
        url = source_urls.get(item_id)
        if not url:
            issues.append(MappingIssue(item_id, "PUBLIC_URL_REQUIRED", "店舗が確認した公開商品URLが必要です。"))
            continue
        variations = item.get("variations", [])
        if not isinstance(variations, list):
            issues.append(MappingIssue(item_id, "INVALID_VARIATIONS", "種類データを確認してください。"))
            continue
        choices = variations or [None]
        categories = item.get("categories", [])
        category = (categories[0].get("name", "") if isinstance(categories, list)
                    and categories and isinstance(categories[0], dict) else "")
        images = item.get("images", [])
        image = (images[0].get("url") if isinstance(images, list) and images
                 and isinstance(images[0], dict) else None)
        for variation in choices:
            if variation is not None and (not isinstance(variation, dict)
                    or type(variation.get("id")) is not int or variation["id"] < 1):
                issues.append(MappingIssue(item_id, "INVALID_VARIATION_ID", "種類IDが不正です。"))
                continue
            stock = item.get("stock") if variation is None else variation.get("stock")
            if type(stock) is not int or stock < 0:
                issues.append(MappingIssue(item_id, "INVALID_STOCK", "在庫情報が不正です。"))
                continue
            vid = None if variation is None else variation["id"]
            sku = "base-" + str(item_id) + (("-" + str(vid)) if vid is not None else "")
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                issues.append(MappingIssue(item_id, "INVALID_NAME", "商品名が未設定です。"))
                continue
            if variation is not None and variation.get("name"):
                name = name + " / " + str(variation["name"])
            try:
                products.append(Product(
                    sku=sku, name=name, description=item.get("detail") or "",
                    category=category, price_jpy=price,
                    stock="in_stock" if stock > 0 else "out_of_stock",
                    stock_quantity=stock, tax_included=True, shipping_jpy=None,
                    source_url=url, evidence_url=None, image_url=image,
                    updated_at=item.get("modified_at"), snapshot_at=timestamp,
                    merchant_id=merchant_id, merchant_name=merchant_name,
                    merchant_homepage=merchant_homepage, is_demo=is_demo,
                ))
            except (ValueError, TypeError):
                issues.append(MappingIssue(item_id, "INVALID_PRODUCT", "必須項目や公開URLを確認してください。"))
    try:
        catalog = Catalog(products)
    except ValueError as exc:
        issues.append(MappingIssue(None, "DUPLICATE_SKU", "同じ種類IDが重複しています。"))
        catalog = Catalog([])
    return BaseMappingResult(catalog=catalog, issues=issues, fetched_count=len(items))
