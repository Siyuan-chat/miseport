"""Source-independent, offline safety tests for merchant-owned snapshots."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from miseport.base_v2 import BaseMappingResult, MappingIssue
from miseport.core import Catalog, Product
from miseport.importers import load_catalog
from miseport.refresh import RefreshError, commit_refresh, plan_refresh


def product(sku="base-1", **overrides):
    data = dict(
        sku=sku, name="京都茶葉", price_jpy=1850, stock="in_stock",
        stock_quantity=4, source_url="https://shop.example.org/items/1",
        updated_at="2026-10-29T00:00:00Z",
        snapshot_at="2026-10-29T01:00:00Z", is_demo=True,
        merchant_id="shop", merchant_name="茶店",
        merchant_homepage="https://shop.example.org/",
    )
    data.update(overrides)
    return Product(**data)


def result(*products, issue=None):
    return BaseMappingResult(Catalog(list(products)), [issue] if issue else [],
                             fetched_count=len(products))


def test_first_import_is_added_and_writes_local_catalog(tmp_path):
    dest = tmp_path / "catalog.json"
    candidate = result(product())
    diff = plan_refresh(None, candidate)
    assert diff.added == ("base-1",)
    assert diff.removed == ()
    applied = commit_refresh(dest, candidate)
    assert applied == diff
    assert load_catalog(dest).products[0].name == "京都茶葉"


def test_snapshot_time_alone_is_not_a_product_change():
    old = Catalog([product(snapshot_at="2026-10-29T01:00:00Z")])
    new = result(product(snapshot_at="2026-10-29T02:00:00Z"))
    diff = plan_refresh(old, new)
    assert diff.unchanged == ("base-1",)
    assert diff.changed == ()


def test_price_change_is_detected_and_applied_without_deletion_approval(tmp_path):
    dest = tmp_path / "current.json"
    commit_refresh(dest, result(product()))
    updated = result(product(price_jpy=2000))
    assert plan_refresh(load_catalog(dest), updated).changed == ("base-1",)
    changes = commit_refresh(dest, updated)
    assert changes.changed == ("base-1",)
    assert load_catalog(dest).products[0].price_jpy == 2000


def test_merchant_identity_change_cannot_replace_existing_catalog(tmp_path):
    dest = tmp_path / "current.json"
    commit_refresh(dest, result(product()))
    before = dest.read_bytes()
    with pytest.raises(RefreshError, match="異なる店舗"):
        commit_refresh(dest, result(product(merchant_id="another")))
    assert dest.read_bytes() == before


def test_removals_require_explicit_merchant_approval(tmp_path):
    dest = tmp_path / "current.json"
    a = product()
    b = product("base-2", source_url="https://shop.example.org/items/2")
    commit_refresh(dest, result(a, b))
    old = dest.read_bytes()
    incoming = result(a)
    plan = plan_refresh(load_catalog(dest), incoming)
    assert plan.removed == ("base-2",)
    assert plan.requires_removal_confirmation
    with pytest.raises(RefreshError, match="削除"):
        commit_refresh(dest, incoming)
    assert dest.read_bytes() == old
    commit_refresh(dest, incoming, approve_removed=True)
    assert list(load_catalog(dest).by_sku) == ["base-1"]


def test_partial_mapping_failure_does_not_overwrite_old_data(tmp_path):
    dest = tmp_path / "current.json"
    commit_refresh(dest, result(product()))
    before = dest.read_bytes()
    invalid = result(product(price_jpy=500),
                     issue=MappingIssue(1, "PRICE_UNKNOWN", "価格不明"))
    with pytest.raises(RefreshError, match="未確認"):
        commit_refresh(dest, invalid)
    assert dest.read_bytes() == before


def test_empty_snapshot_does_not_delete_all_products(tmp_path):
    dest = tmp_path / "current.json"
    commit_refresh(dest, result(product()))
    before = dest.read_bytes()
    with pytest.raises(RefreshError, match="未確認"):
        commit_refresh(dest, result(), approve_removed=True)
    assert dest.read_bytes() == before


def test_corrupt_existing_catalog_is_never_overwritten(tmp_path):
    dest = tmp_path / "current.json"
    dest.write_text("bad json", encoding="utf-8")
    with pytest.raises(RefreshError, match="破損"):
        commit_refresh(dest, result(product()))
    assert dest.read_text(encoding="utf-8") == "bad json"


def test_diff_is_sorted_and_serializable():
    old = Catalog([product("base-4"), product("base-2")])
    new = result(product("base-3"), product("base-2", price_jpy=1000))
    diff = plan_refresh(old, new)
    assert diff.as_dict() == {
        "added": ["base-3"], "removed": ["base-4"],
        "changed": ["base-2"], "unchanged": [],
        "requires_removal_confirmation": True,
    }
