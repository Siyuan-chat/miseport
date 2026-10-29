"""Small platform-source contract for merchant-owned, read-only catalog ingestion.

All platform integrations provide a separate adapter. No global merchant index,
token store, write API, or mandatory model provider is introduced here.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol, runtime_checkable

from .base_v2 import BaseMappingResult, BaseV2Client, map_base_items


@dataclass(frozen=True)
class MerchantProfile:
    merchant_id: str
    merchant_name: str
    merchant_homepage: str
    verified_product_urls: Mapping[int, str]
    is_demo: bool = False

    def __post_init__(self):
        if not all(isinstance(x, str) and x.strip() for x in (
                self.merchant_id, self.merchant_name, self.merchant_homepage)):
            raise ValueError("店舗ID・店舗名・URLを入力してください。")
        if type(self.is_demo) is not bool:
            raise ValueError("is_demo must be boolean")


@dataclass(frozen=True)
class SourceCapabilities:
    platform_id: str
    api_version: str
    authorization_type: str
    access_level: str = "read_only"
    supports_manual_refresh: bool = True
    supports_automatic_background_sync: bool = False


@runtime_checkable
class ReadOnlySourceAdapter(Protocol):
    """No add/update/delete methods; authentication stays owner controlled."""

    @property
    def capabilities(self) -> SourceCapabilities: ...

    def fetch_public(self, authorization: str) -> list[dict]: ...

    def normalize(self, items: list[dict], merchant: MerchantProfile,
                  *, snapshot_at: datetime | None = None) -> BaseMappingResult: ...


class BaseSourceAdapter:
    """BASE beta adapter. Credentials are passed per fetch, not stored."""

    capabilities = SourceCapabilities(
        platform_id="base",
        api_version="v2-beta",
        authorization_type="owner_pat_items.read",
    )

    def __init__(self, client: BaseV2Client | None = None):
        self._client = client if client is not None else BaseV2Client()

    def fetch_public(self, authorization: str) -> list[dict]:
        return self._client.fetch_items(authorization)

    def normalize(self, items: list[dict], merchant: MerchantProfile,
                  *, snapshot_at: datetime | None = None) -> BaseMappingResult:
        return map_base_items(
            items, merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            merchant_homepage=merchant.merchant_homepage,
            source_urls=merchant.verified_product_urls,
            is_demo=merchant.is_demo, snapshot_at=snapshot_at,
        )


def get_source_adapter(platform_id: str, *, base_client: BaseV2Client | None = None
                       ) -> ReadOnlySourceAdapter:
    """Reject unknown/unverified integrations rather than guessing an API."""
    if platform_id == "base":
        return BaseSourceAdapter(base_client)
    raise ValueError("このECプラットフォームの自動API連携は未対応です。")
