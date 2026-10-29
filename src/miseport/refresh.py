"""Safe preview / apply of read-only BASE product-catalog refreshes.

A complete successful API fetch is a prerequisite. Product delistings are
visible before replacement; a partial or invalid fetch cannot replace the
last known-good local catalog. No automatic cloud publishing.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .core import Catalog
from .importers import load_catalog, save_catalog

if TYPE_CHECKING:
    from .base_v2 import BaseMappingResult


class RefreshError(ValueError):
    pass


@dataclass(frozen=True)
class CatalogDiff:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[str, ...]
    unchanged: tuple[str, ...]

    @property
    def requires_removal_confirmation(self) -> bool:
        return bool(self.removed)

    def as_dict(self) -> dict:
        return {
            "added": list(self.added),
            "removed": list(self.removed),
            "changed": list(self.changed),
            "unchanged": list(self.unchanged),
            "requires_removal_confirmation": self.requires_removal_confirmation,
        }


def _identity(catalog: Catalog) -> tuple[str, str, str] | None:
    values = {(p.merchant_id, p.merchant_name, p.merchant_homepage)
              for p in catalog.products}
    if len(values) != 1:
        return None
    identity = values.pop()
    if not all(identity):
        return None
    return identity


def _fields(product):
    record = product.model_dump(mode="json")
    # Snapshot fetch timestamp changes every import, but not the product's facts.
    record.pop("snapshot_at", None)
    return record


def plan_refresh(previous: Catalog | None, incoming: "BaseMappingResult") -> CatalogDiff:
    """Validate the complete incoming snapshot and calculate stable SKU diffs."""
    if not incoming.publishable:
        raise RefreshError("未確認の商品があるため、この更新内容を確定できません。")
    latest = incoming.catalog
    latest_id = _identity(latest)
    if latest_id is None:
        raise RefreshError("店舗情報を確認してください。")
    if previous is None:
        return CatalogDiff(tuple(sorted(latest.by_sku)), (), (), ())
    previous_id = _identity(previous)
    if previous.products and previous_id != latest_id:
        raise RefreshError("前回とは異なる店舗の商品を上書きできません。")
    old, new = set(previous.by_sku), set(latest.by_sku)
    shared = old & new
    changed = sorted(sku for sku in shared
                     if _fields(previous.by_sku[sku]) != _fields(latest.by_sku[sku]))
    unchanged = sorted(shared - set(changed))
    return CatalogDiff(
        added=tuple(sorted(new - old)),
        removed=tuple(sorted(old - new)),
        changed=tuple(changed),
        unchanged=tuple(unchanged),
    )


def commit_refresh(destination: str | Path, incoming: "BaseMappingResult", *,
                   approve_removed: bool = False) -> CatalogDiff:
    """Atomic local replacement only after complete fetch and merchant review."""
    destination = Path(destination)
    if destination.exists() and not destination.is_file():
        raise RefreshError("既存のカタログ保存先は通常のファイルである必要があります。")
    try:
        previous = load_catalog(destination) if destination.exists() else None
    except ValueError:
        raise RefreshError("前回のカタログが破損しています。上書きを中断します。") from None
    diff = plan_refresh(previous, incoming)
    if diff.requires_removal_confirmation and approve_removed is not True:
        raise RefreshError("公開商品が削除されています。店主が削除を確認してください。")
    try:
        save_catalog(incoming.catalog, destination)
    except (OSError, ValueError):
        raise RefreshError("カタログ保存に失敗しました。保存先を確認してください。") from None
    return diff
