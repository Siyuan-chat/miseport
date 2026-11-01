"""D6 natural-discovery study is manually reviewed, never host-simulated."""
import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from miseport.e2_discovery import DiscoveryStudy, E2Trace, score_e2

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "tests/fixtures/e2-shopping-20.synthetic.json"
EMPTY = ROOT / "tests/fixtures/e2-trace-empty.synthetic.json"
HASH = "a" * 64


def study():
    return DiscoveryStudy.model_validate_json(STUDY.read_bytes())


def trial(*, phase="baseline", name="trial-1", reviewed=True, observed=True):
    return {
        "trial_id": name, "phase": phase, "prompt_id": "E2-01",
        "replicate": 1, "host": "host-under-test", "model": "recorded-model",
        "settings_id": "default-with-web-browsing", "captured_at": "2026-11-01T10:00:00+09:00",
        "shop_mcp_connected": False, "shop_named_in_prompt": False,
        "reviewed_by": "manual-reviewer" if reviewed else None,
        "answer_sha256": HASH if reviewed else None,
        "observed_product_urls": ["https://example.org/products/tea-001"]
            if reviewed and observed else [] if reviewed else None,
        "cited_product_urls": ["https://example.org/products/tea-001"]
            if reviewed and observed else [] if reviewed else None,
        "product_facts_correct": True if reviewed and observed else None,
    }


def trace(observations):
    return E2Trace.model_validate({
        "schema_version": "miseport-e2-trace/1.0",
        "study_id": study().study_id, "observations": observations})


def test_frozen_twenty_prompts_do_not_name_shop_and_empty_traces_have_no_scores():
    info = study()
    assert len(info.prompts) == 20
    assert all("example.org" not in x.prompt for x in info.prompts)
    blank = E2Trace.model_validate_json(EMPTY.read_bytes())
    report = score_e2(info, blank)
    assert report["question_count"] == 20
    assert report["phases"]["baseline"]["observed_rate_reviewed"] is None
    assert report["phases"]["followup"]["observed_rate_reviewed"] is None
    assert report["fully_reviewed_paired_trials"] == 0
    assert report["paired_observation_difference"] is None
    assert report["causal_lift_established"] is False
    assert report["no_agent_or_web_requests_performed"] is True


def test_complete_matching_pair_is_counted_as_descriptive_gain_only():
    before = trial(observed=False)
    after = trial(phase="followup", name="trial-2", observed=True)
    result = score_e2(study(), trace([before, after]))
    assert result["phases"]["baseline"]["reviewed"] == 1
    assert result["phases"]["baseline"]["observed_rate_reviewed"] == 0
    assert result["phases"]["followup"]["observed_rate_reviewed"] == 1
    assert result["paired_changes"]["new_observation"] == 1
    assert result["paired_observation_difference"] == 1
    assert result["causal_lift_established"] is False
    assert result["is_demo_study"] is True
    assert "answer" not in result["trials"][0]


def test_unreviewed_row_is_not_a_no_hit_or_a_completed_pair():
    before = trial(reviewed=False)
    after = trial(phase="followup", name="trial-2", observed=True)
    report = score_e2(study(), trace([before, after]))
    assert report["phases"]["baseline"]["reviewed"] == 0
    assert report["phases"]["baseline"]["unreviewed"] == 1
    assert report["phases"]["baseline"]["observed_rate_reviewed"] is None
    assert report["fully_reviewed_paired_trials"] == 0


@pytest.mark.parametrize("field, value", [
    ("shop_mcp_connected", True), ("shop_named_in_prompt", True),
    ("observed_product_urls", ["https://evil.example.org/products/x"]),
    ("cited_product_urls", ["https://example.org/products/tea-002"]),
])
def test_false_e2_conditions_are_rejected(field, value):
    one = trial()
    one[field] = value
    if field == "observed_product_urls":
        one["cited_product_urls"] = []  # Isolate foreign-URL validation from citation-subset validation.
    if field in ("shop_mcp_connected", "shop_named_in_prompt", "cited_product_urls"):
        with pytest.raises(ValidationError):
            trace([one])
    else:
        with pytest.raises(ValueError, match="does not belong"):
            score_e2(study(), trace([one]))


def test_model_settings_must_match_for_pairing_and_no_duplicate_design():
    before = trial()
    after = trial(phase="followup", name="trial-2")
    after["settings_id"] = "different"
    report = score_e2(study(), trace([before, after]))
    assert report["fully_reviewed_paired_trials"] == 0
    duplicate = trial(name="other-id")
    with pytest.raises(ValueError, match="duplicate trial design key"):
        score_e2(study(), trace([before, duplicate]))


def test_study_cannot_embed_merchant_name_domain_or_duplicate_urls():
    raw = json.loads(STUDY.read_text(encoding="utf-8"))
    raw["prompts"][0]["prompt"] = "架空の京都茶店（デモ専用）のお茶をください。"
    with pytest.raises(ValidationError):
        DiscoveryStudy.model_validate(raw)
    raw = json.loads(STUDY.read_text(encoding="utf-8"))
    raw["target_product_urls"].append(raw["target_product_urls"][0])
    with pytest.raises(ValidationError):
        DiscoveryStudy.model_validate(raw)



def test_e2_cli_exports_empty_synthetic_report_without_fake_observations(tmp_path):
    import subprocess
    import sys
    out = tmp_path / "report.json"
    result = subprocess.run(
        [sys.executable, "-m", "miseport.e2_discovery",
         "--study", str(STUDY), "--trace", str(EMPTY), "--output", str(out)],
        capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["question_count"] == 20
    assert report["fully_reviewed_paired_trials"] == 0
    assert report["causal_lift_established"] is False
    assert report["phases"]["baseline"]["observed_rate_reviewed"] is None
    assert report["input_sha256"]["study"] and report["input_sha256"]["trace"]


def test_e2_rejects_stored_answer_body_and_unreviewed_incomplete_records():
    one = trial()
    one["answer"] = "Private shop conversation should not be recorded here."
    with pytest.raises(ValidationError):
        trace([one])
    invalid = trial()
    invalid["reviewed_by"] = None
    with pytest.raises(ValidationError, match="review"):
        trace([invalid])
