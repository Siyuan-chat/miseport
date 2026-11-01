"""E2: human-verified observations of *unconnected* Agent product discovery.

This module performs NO model calls, browser searches, URL fetching or platform
submissions. It scores externally recorded observations and never treats
user-supplied labels as independently verified exposure or causal lift.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from .eval import write_report

MAX_BYTES = 1024 * 1024


def _https(url: str) -> bool:
    try:
        p = urlsplit(url)
        return (p.scheme == "https" and bool(p.hostname) and not p.username
                and not p.password and p.fragment == ""
                and p.port in (None, 443)
                and len(url) <= 2048 and not any(c.isspace() for c in url))
    except (ValueError, TypeError):
        return False


class ShoppingPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^E2-[0-9]{2}$")
    prompt: str = Field(min_length=12, max_length=500)


class DiscoveryStudy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["miseport-e2-study/1.0"]
    study_id: str = Field(min_length=3, max_length=100)
    merchant_id: str = Field(min_length=1, max_length=128)
    merchant_name: str = Field(min_length=1, max_length=300)
    merchant_website: str
    target_product_urls: list[str] = Field(min_length=1, max_length=100)
    fixture_kind: Literal["synthetic", "merchant_authorized"]
    prompts: list[ShoppingPrompt] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def study_contract(self):
        if not _https(self.merchant_website):
            raise ValueError("merchant_website must be an HTTPS domain")
        host = urlsplit(self.merchant_website).hostname
        if (len(set(self.target_product_urls)) != len(self.target_product_urls)
                or any(not _https(url) or urlsplit(url).hostname != host
                       for url in self.target_product_urls)):
            raise ValueError("target URLs must be unique merchant-owned HTTPS links")
        ids = [p.id for p in self.prompts]
        if set(ids) != {f"E2-{n:02}" for n in range(1, 21)}:
            raise ValueError("expected E2-01 through E2-20 exactly once")
        for prompt in self.prompts:
            lower = prompt.prompt.lower()
            if host.lower() in lower or (len(self.merchant_name) >= 3
                                          and self.merchant_name.lower() in lower):
                raise ValueError("natural discovery prompts must not name the shop/domain")
        return self


class E2Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trial_id: str = Field(min_length=1, max_length=100)
    phase: Literal["baseline", "followup"]
    prompt_id: str = Field(pattern=r"^E2-[0-9]{2}$")
    replicate: int = Field(ge=1, le=20)
    host: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    settings_id: str = Field(min_length=1, max_length=100)
    captured_at: datetime
    shop_mcp_connected: StrictBool
    shop_named_in_prompt: StrictBool
    reviewed_by: str | None = Field(default=None, max_length=100)
    answer_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    observed_product_urls: list[str] | None = None
    cited_product_urls: list[str] | None = None
    product_facts_correct: StrictBool | None = None

    @model_validator(mode="after")
    def record_boundaries(self):
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at requires timezone")
        if self.shop_mcp_connected or self.shop_named_in_prompt:
            raise ValueError("E2 must not use shop MCP or a prompt naming the shop")
        supplied = (self.observed_product_urls is not None
                    or self.cited_product_urls is not None
                    or self.product_facts_correct is not None)
        if supplied and (not self.reviewed_by or not self.answer_sha256
                         or self.observed_product_urls is None
                         or self.cited_product_urls is None):
            raise ValueError("review requires reviewer, answer hash and explicit URL lists")
        if self.reviewed_by and not supplied:
            raise ValueError("reviewer without reviewed observations")
        if self.observed_product_urls is not None:
            if len(set(self.observed_product_urls)) != len(self.observed_product_urls):
                raise ValueError("duplicate observed product URLs")
            if not set(self.cited_product_urls or []).issubset(self.observed_product_urls):
                raise ValueError("citation URLs must be among observed target URLs")
            if self.observed_product_urls and self.product_facts_correct is None:
                raise ValueError("observed product requires explicit factual review")
        return self


class E2Trace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["miseport-e2-trace/1.0"]
    study_id: str
    observations: list[E2Observation] = Field(default_factory=list, max_length=5000)


def _read(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError("E2 fixture/trace exceeds 1 MiB")
    return raw, sha256(raw).hexdigest()


def score_e2(study: DiscoveryStudy, trace: E2Trace) -> dict:
    """Only score explicitly reviewed runs; no missing record becomes a no-hit."""
    if trace.study_id != study.study_id:
        raise ValueError("E2 trace/study mismatch")
    prompts = {p.id for p in study.prompts}
    allowed = set(study.target_product_urls)
    seen_ids, matched = set(), set()
    rows = []
    for row in trace.observations:
        if row.trial_id in seen_ids:
            raise ValueError("duplicate trial_id")
        seen_ids.add(row.trial_id)
        if row.prompt_id not in prompts:
            raise ValueError("unknown study prompt")
        if (row.observed_product_urls is not None and
                not set(row.observed_product_urls).issubset(allowed)):
            raise ValueError("observed URL does not belong to this study target set")
        key = (row.phase, row.prompt_id, row.replicate, row.host, row.model, row.settings_id)
        if key in matched:
            raise ValueError("duplicate trial design key")
        matched.add(key)
        reviewed = row.observed_product_urls is not None
        hit = bool(reviewed and row.observed_product_urls)
        valid_hit = bool(hit and row.product_facts_correct is True)
        rows.append({
            "trial_id": row.trial_id, "phase": row.phase,
            "prompt_id": row.prompt_id, "replicate": row.replicate,
            "host": row.host, "model": row.model, "settings_id": row.settings_id,
            "captured_at": row.captured_at.isoformat(),
            "reviewed": reviewed,
            "target_observed": hit if reviewed else None,
            "target_cited": bool(row.cited_product_urls) if reviewed else None,
            "factually_correct_target_observed": valid_hit if reviewed else None,
            "answer_sha256": row.answer_sha256,
        })
    phases = {}
    for phase in ("baseline", "followup"):
        subset = [r for r in rows if r["phase"] == phase]
        valid = [r for r in subset if r["reviewed"]]
        hits = sum(r["target_observed"] for r in valid)
        accurate = sum(r["factually_correct_target_observed"] for r in valid)
        phases[phase] = {
            "records": len(subset), "reviewed": len(valid),
            "unreviewed": len(subset) - len(valid),
            "target_observed": hits, "target_cited": sum(r["target_cited"] for r in valid),
            "factually_correct_target_observed": accurate,
            "observed_rate_reviewed": round(hits / len(valid), 4) if valid else None,
            "accurate_observed_rate_reviewed": round(accurate / len(valid), 4) if valid else None,
        }
    paired = defaultdict(dict)
    for r in rows:
        key = (r["prompt_id"], r["replicate"], r["host"], r["model"], r["settings_id"])
        paired[key][r["phase"]] = r
    valid_pairs = [v for v in paired.values()
                   if all(v.get(phase, {}).get("reviewed") for phase in ("baseline", "followup"))]
    changes = {"new_observation": 0, "lost_observation": 0,
               "observed_both": 0, "observed_neither": 0}
    for records in valid_pairs:
        before, after = (records["baseline"]["target_observed"],
                         records["followup"]["target_observed"])
        label = ("new_observation" if not before and after else
                 "lost_observation" if before and not after else
                 "observed_both" if before else "observed_neither")
        changes[label] += 1
    return {
        "schema_version": "miseport-e2-report/1.0",
        "evaluation_type": "unconnected_agent_manual_observation",
        "source_evidence": "self_reported_human_review_not_independently_verified",
        "is_demo_study": study.fixture_kind == "synthetic",
        "shop_connector_excluded_by_record": True,
        "platform_indexing_verified": False, "causal_lift_established": False,
        "no_agent_or_web_requests_performed": True,
        "study_id": study.study_id,
        "question_count": len(study.prompts),
        "target_url_count": len(study.target_product_urls),
        "phases": phases,
        "fully_reviewed_paired_trials": len(valid_pairs),
        "paired_changes": changes,
        "paired_observation_difference": (
            round((changes["new_observation"] - changes["lost_observation"]) /
                  len(valid_pairs), 4) if valid_pairs else None),
        "trials": rows,
        "cautions": [
            "No missing or unreviewed trial is treated as a negative result.",
            "Same host/model/settings and prompt/replicate required for a pair.",
            "Before/after differences cannot establish causal ranking uplift.",
            "Host, MCP-disconnected state and reviewer labels are user-reported.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        prog="miseport-e2-eval",
        description="Human-annotated unconnected Agent discovery study; no model calls")
    parser.add_argument("--study", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        study_data, study_hash = _read(args.study)
        trace_data, trace_hash = _read(args.trace)
        study = DiscoveryStudy.model_validate_json(study_data)
        trace = E2Trace.model_validate_json(trace_data)
        report = score_e2(study, trace)
        report["input_sha256"] = {"study": study_hash, "trace": trace_hash}
        write_report(args.output, report)
    except (ValueError, OSError) as exc:
        parser.error("invalid E2 input or report destination: " + type(exc).__name__)
    print(json.dumps({"study_id": report["study_id"],
                      "reviewed_baseline": report["phases"]["baseline"]["reviewed"],
                      "reviewed_followup": report["phases"]["followup"]["reviewed"],
                      "paired": report["fully_reviewed_paired_trials"]}))


if __name__ == "__main__":
    main()
