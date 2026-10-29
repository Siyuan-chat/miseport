"""Bind imported merchant product data to the exact UI source configuration.

A user changing merchant name/domain, source kind, CSV profile or example URL
must re-import rather than publishing cached product data under another store.
This module holds no BASE PAT, CSV contents or customer information.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit

from .base_urls import BaseURLValidationError, _store_origin


class SourceContextError(ValueError):
    """Safe-to-display merchant GUI configuration error."""


@dataclass(frozen=True)
class SourceContext:
    mode: str
    platform: str
    merchant_id: str
    merchant_name: str
    merchant_homepage: str
    example_url: str | None


def capture_source_context(
    mode: str, platform: str, merchant_id: str, merchant_name: str,
    merchant_homepage: str, *, example_url: str = ""
) -> SourceContext:
    """Capture the context *before* fetching or opening a merchant CSV.

    API URL examples can be supplied after import. CSV example URLs must be
    frozen because they determine inferred product links in the parsed data.
    """
    if mode == "api":
        if platform != "base":
            raise SourceContextError("BASE API以外の自動接続には対応していません。")
        example = None
    elif mode == "csv":
        if platform not in ("BASEの商品CSV", "Shopifyの商品CSV"):
            raise SourceContextError("CSVの種類を選択してください。")
        if not isinstance(example_url, str) or not example_url.strip():
            raise SourceContextError("実際に確認した1商品の公開URLを入力してください。")
        example = example_url.strip()
    else:
        raise SourceContextError("データ取得方式を選択してください。")

    if any(not isinstance(s, str) or not s.strip() or len(s.strip()) > 512
           for s in (merchant_id, merchant_name, merchant_homepage)):
        raise SourceContextError("店舗ID・店舗名・トップURLを確認してください。")
    shop_id, name, home = (
        merchant_id.strip(), merchant_name.strip(), merchant_homepage.strip()
    )
    try:
        host = _store_origin(home)
        if urlsplit(home).path not in ("", "/") or home.rstrip("/") != host:
            raise SourceContextError("店舗トップのHTTPS URLを確認してください。")
    except BaseURLValidationError:
        raise SourceContextError("店舗トップのHTTPS URLを確認してください。") from None
    return SourceContext(mode, platform, shop_id, name, home, example)


def context_is_current(
    stored: SourceContext | None, *,
    mode: str, platform: str, merchant_id: str, merchant_name: str,
    merchant_homepage: str, example_url: str = ""
) -> bool:
    if stored is None:
        return False
    try:
        now = capture_source_context(
            mode, platform, merchant_id, merchant_name, merchant_homepage,
            example_url=example_url,
        )
        return now == stored
    except SourceContextError:
        return False
