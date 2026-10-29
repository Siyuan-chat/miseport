"""BASE public storefront URL suggestions, derived only from its documented route.

These are *candidate* URLs. The user must confirm an actual public example
for the same store, then review the catalog before any publication.
No HTTP requests, login credentials, crawler or background traffic.
Official BASE page structure: https://docs.thebase.in/template/directory/page/
"""
from dataclasses import dataclass
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


class BaseURLValidationError(ValueError):
    """Safe error messages for merchant-facing display."""


_ITEM_PATH = re.compile(r"/items/([1-9][0-9]*)(?:/)?\Z", flags=re.ASCII)
_MAX_ITEMS = 10000


def _store_origin(url: str) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or len(url) > 2048:
        raise BaseURLValidationError("店舗URLを確認してください。")
    try:
        parts = urlsplit(url)
        host = parts.hostname
        port = parts.port
    except ValueError:
        raise BaseURLValidationError("店舗URLが正しくありません。") from None
    if (parts.scheme != "https" or not host or parts.username or parts.password
            or port not in (None, 443) or parts.query or parts.fragment
            or any(c.isspace() or ord(c) < 32 for c in url)
            or "\\" in url or host.endswith(".") or "%" in host):
        raise BaseURLValidationError("HTTPSの店舗URLを指定してください。")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise BaseURLValidationError("IPアドレスを店舗URLに使用できません。")
    if (host == "localhost" or host.endswith((".local", ".internal", ".localhost", ".test"))
            or "." not in host or host.startswith("-")):
        raise BaseURLValidationError("公開されている店舗ドメインを指定してください。")
    # Keep the user's known merchant hostname, not userinfo or a guessed one.
    return "https://" + parts.netloc.lower().removesuffix(":443")


def candidate_product_urls(
    items: list[dict], homepage: str, confirmed_example_url: str,
    *, merchant_confirmed: bool = False
) -> dict[int, str]:
    """Produce public URL candidates after a merchant confirms one real page.

    The confirmed example must correspond to one of the retrieved BASE item IDs.
    Only published/in-sale normal products are proposed. The remaining candidates
    are inferred by BASE's documented route, not network-verified or guaranteed.
    """
    if merchant_confirmed is not True:
        raise BaseURLValidationError("店主が公開商品ページの例を確認してください。")
    origin = _store_origin(homepage)
    hp = urlsplit(homepage)
    if hp.path not in ("", "/"):
        raise BaseURLValidationError("店舗のトップページURLを入力してください。")
    if not isinstance(confirmed_example_url, str):
        raise BaseURLValidationError("公開商品のURL例を入力してください。")
    try:
        sample = urlsplit(confirmed_example_url)
        sample_origin = _store_origin(confirmed_example_url)
    except BaseURLValidationError:
        raise BaseURLValidationError("公開商品URLを確認してください。") from None
    if sample_origin != origin or sample.query or sample.fragment:
        raise BaseURLValidationError("商品URLと店舗ドメインが一致しません。")
    match = _ITEM_PATH.fullmatch(sample.path)
    if not match:
        raise BaseURLValidationError("商品URLは「/items/商品ID」の形式にしてください。")
    sample_id = int(match.group(1))
    if not isinstance(items, list) or len(items) > _MAX_ITEMS:
        raise BaseURLValidationError("商品件数が上限を超えました。")
    candidates = {}
    for item in items:
        if not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] < 1:
            raise BaseURLValidationError("商品IDの形式を確認してください。")
        key = item["id"]
        if key in candidates:
            raise BaseURLValidationError("商品IDの重複があります。")
        if (item.get("visible") is True and item.get("sales_status") == "item_now_on_sale"
                and item.get("type") == "normal"):
            candidates[key] = origin + "/items/" + str(key)
    if sample_id not in candidates:
        raise BaseURLValidationError("URL例の商品IDが読み込んだ公開商品にありません。")
    return candidates


def validate_manual_product_urls(urls: dict[int, str], homepage: str) -> None:
    """Keep manually entered URLs on the merchant's exact shop origin."""
    origin = _store_origin(homepage)
    for item_id, url in urls.items():
        if type(item_id) is not int or item_id < 1 or not isinstance(url, str):
            raise BaseURLValidationError("商品URLの形式を確認してください。")
        if _store_origin(url) != origin:
            raise BaseURLValidationError("他の店舗のURLを登録できません。")
        parsed = urlsplit(url)
        match = _ITEM_PATH.fullmatch(parsed.path)
        if not match or int(match.group(1)) != item_id or parsed.query or parsed.fragment:
            raise BaseURLValidationError("商品IDと公開URLの対応を確認してください。")
