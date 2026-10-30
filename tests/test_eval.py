"""Agent eval does not mistake fixture assertions for an LLM evaluation."""
import asyncio
import json
from pathlib import Path

import pytest

from miseport.eval import at, evaluate, host_review, protocol, suite, write_report

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "tests/fixtures/muse-benchmark-20.reference.json"
PROBES = ROOT / "tests/fixtures/muse-eval-probes-v1.json"
CAT = ROOT / "tests/fixtures/demo-store.reference.json"


def test_suite_is_complete_and_frozen():
    cases, steps, hashes = suite(BENCH, PROBES)
    assert [c["id"] for c in cases] == [s["id"] for s in steps]
    assert cases[0]["id"] == "J01" and cases[-1]["id"] == "J20"
    assert len(cases) == 20 and len(hashes["benchmark_sha256"]) == 64


def test_expected_fields_and_missing_vs_null():
    payload = {"products": [{"sku": "a"}, {"sku": "b"}],
               "available": True, "offer": {"shipping": None}}
    checks = [{"path": "products[*].sku", "equals": ["a", "b"]},
              {"path": "offer.review", "absent": True},
              {"path": "offer.shipping", "equals": None},
              {"path": "available", "equals": 1},
              {"path": "offer.review", "equals": None}]
    assert [x["passed"] for x in evaluate(payload, checks)] == [
        True, True, True, False, False]
    assert at(payload, "products[*].sku") == ["a", "b"]


def test_real_mcp_stdio_run_all_twenty_without_llm(tmp_path):
    result = asyncio.run(asyncio.wait_for(protocol(BENCH, PROBES, CAT), timeout=90))
    assert result["tool_metadata_safe"] is True
    assert result["case_count"] == result["passed"] == 20
    assert result["failed"] == 0
    assert result["agent_answer_evaluated"] is False
    assert result["natural_discovery_evaluated"] is False
    assert result["merchant_data_used"] is False
    path = tmp_path / "protocol.json"
    write_report(path, result)
    assert json.loads(path.read_text(encoding="utf-8"))["passed"] == 20


def test_non_demo_catalog_refused_before_running_protocol(tmp_path):
    fake = json.loads(CAT.read_text(encoding="utf-8"))
    fake["demo_only"] = False
    p = tmp_path / "not-demo.json"
    p.write_text(json.dumps(fake), encoding="utf-8")
    with pytest.raises(ValueError):
        asyncio.run(protocol(BENCH, PROBES, p))


def test_unreviewed_host_questions_are_not_success(tmp_path):
    trace = {
        "host": "test-host", "model": "test-model", "captured_at": "2026-10-30",
        "cases": [
            {"id": "J01", "answer": "A possible match", "reviewed_by": "human",
             "tool_calls": [{"name": "search_products", "is_error": False}],
             "review": {"observed_product_ids": ["tea-001"],
                        "facts_grounded": True, "unknown_handled": True,
                        "source_cited": True, "safe_behavior": True}},
            {"id": "J02", "answer": "Not yet reviewed", "tool_calls": [], "review": {}}
        ]
    }
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(trace), encoding="utf-8")
    result = host_review(BENCH, PROBES, path)
    assert result["case_count"] == 20
    assert result["reviewed"] == 1
    assert result["passed"] == 1
    assert result["failed"] == 0
    assert result["unreviewed"] == 19
    assert result["host_status"] == "user_supplied_not_independently_verified"
    assert "A possible match" not in json.dumps(result)


def test_host_review_flags_fail_and_prohibited_tools_rejected(tmp_path):
    trace = {
        "host": "test", "model": "test", "captured_at": "2026-10-30",
        "cases": [{"id": "J01", "answer": "demo", "reviewed_by": "human",
                   "tool_calls": [{"name": "get_product", "is_error": True}],
                   "review": {"observed_product_ids": ["tea-001"],
                              "facts_grounded": False, "unknown_handled": True,
                              "source_cited": True, "safe_behavior": True}}]}
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(trace), encoding="utf-8")
    result = host_review(BENCH, PROBES, path)
    assert result["failed"] == result["tool_errors"] == 1
    trace["cases"][0]["tool_calls"] = [{"name": "checkout", "is_error": False}]
    path.write_text(json.dumps(trace), encoding="utf-8")
    with pytest.raises(ValueError, match="tool_calls"):
        host_review(BENCH, PROBES, path)


def test_host_tool_error_never_counts_as_pass_even_when_review_flags_are_true(tmp_path):
    trace = {"host": "sample", "model": "sample", "captured_at": "2026-10-30",
        "cases": [{"id": "J01", "answer": "a result", "reviewed_by": "human",
            "tool_calls": [{"name": "search_products", "is_error": True}],
            "review": {"observed_product_ids": ["tea-001"],
                "facts_grounded": True, "unknown_handled": True,
                "source_cited": True, "safe_behavior": True}}]}
    path = tmp_path / "host-tool-failure.json"
    path.write_text(json.dumps(trace), encoding="utf-8")
    result = host_review(BENCH, PROBES, path)
    assert result["tool_errors"] == 1 and result["failed"] == 1
    assert result["passed"] == 0 and result["reviewed"] == 1
