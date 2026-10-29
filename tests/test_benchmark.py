"""Data-boundary checks from archived prompts; no semantic or host evaluation."""
import json
from pathlib import Path

from miseport.importers import load_catalog

REFERENCE = Path(__file__).resolve().parents[1] / "tests/fixtures"


def test_archived_reference_keeps_host_evaluation_explicitly_unrun():
    benchmark = json.loads((REFERENCE / "muse-benchmark-20.reference.json").read_text(encoding="utf-8"))
    assert benchmark["host_status"] == "not_run_on_muse"
    assert benchmark["data_status"] == "synthetic_demo_only"
    assert len(benchmark["queries"]) == 20


def test_j05_j09_j14_snapshot_price_boundaries():
    catalog = load_catalog(REFERENCE / "demo-store.reference.json")
    cases = {case["id"]: case for case in json.loads(
        (REFERENCE / "muse-benchmark-20.reference.json").read_text(encoding="utf-8"))["queries"]}
    assert catalog.quote("tea-001", 2)["total_jpy"] == cases["J05"]["expected_snapshot_total_jpy"]
    assert catalog.quote("tea-001")["total_jpy"] == cases["J14"]["expected_snapshot_total_jpy"]
    quote = catalog.quote("tea-002")
    assert quote["shipping_jpy"] is None and quote["total_jpy"] is None
    assert quote["is_binding"] is False


def test_j04_j07_j10_j13_j18_j19_evidence_and_unknown_boundaries():
    catalog = load_catalog(REFERENCE / "demo-store.reference.json")
    assert [p["sku"] for p in catalog.search(origin_prefecture="京都府")["products"]] == ["tea-001"]
    assert catalog.detail("tea-001")["product"]["caffeine_level"] is None
    assert catalog.inventory("tea-002")["stock"] == "unknown"
    assert catalog.inventory("tea-002")["stock_is_live"] is False
    assert catalog.audit()["missing_fields"]["shipping_jpy"] == ["tea-002"]
    assert catalog.audit()["missing_fields"]["stock"] == ["tea-002"]
    wrapped = catalog.search(gift_wrapping=True)["products"]
    assert len(wrapped) == 1 and wrapped[0]["is_demo"] is True
    assert wrapped[0]["evidence_url"] == "https://example.org/products/tea-001"
    jsonld = catalog.jsonld("tea-001")["jsonld"]
    assert "aggregateRating" not in jsonld and "review" not in jsonld
