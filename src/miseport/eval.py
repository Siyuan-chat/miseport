"""20-case Japanese shopping evaluation without invented Agent results.

protocol: call the real local read-only MCP stdio server with fixed probes.
host: score user-supplied, human-annotated transcripts, never auto-judge prose.
"""
import argparse
import asyncio
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter

TOOLS = frozenset(("about_miseport", "search_products", "get_product",
    "check_inventory", "get_quote", "audit_catalog", "export_product_jsonld"))
REVIEW = ("facts_grounded", "unknown_handled", "source_cited", "safe_behavior")
MISSING = object()


def load_json(path):
    raw = Path(path).read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError("evaluation input exceeds 1 MiB")
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("evaluation input is not a JSON object")
    return data, hashlib.sha256(raw).hexdigest()


def suite(benchmark, probes):
    b, bh = load_json(benchmark)
    p, ph = load_json(probes)
    cases, steps = b.get("queries"), p.get("probes")
    if (b.get("data_status") != "synthetic_demo_only"
            or not isinstance(cases, list) or not isinstance(steps, list)
            or len(cases) != 20 or len(steps) != 20):
        raise ValueError("expected the frozen 20-question synthetic benchmark")
    ids = [c.get("id") for c in cases]
    if (len(set(ids)) != 20 or ids != [x.get("id") for x in steps]
            or any(not isinstance(c.get("prompt"), str) for c in cases)):
        raise ValueError("benchmark/probe ids do not match")
    for probe in steps:
        if (probe.get("tool") not in TOOLS or
                not isinstance(probe.get("arguments"), dict) or
                not isinstance(probe.get("checks"), list) or not probe["checks"]):
            raise ValueError("invalid probe")
        for check in probe["checks"]:
            if (not isinstance(check, dict) or
                    not isinstance(check.get("path"), str) or
                    (("equals" in check) == ("absent" in check)) or
                    ("absent" in check and check["absent"] is not True)):
                raise ValueError("invalid probe assertion")
    return cases, steps, {"benchmark_id": b["benchmark_id"],
                          "benchmark_sha256": bh, "probes_sha256": ph}


def at(payload, path):
    for segment in path.split("."):
        multiple = segment.endswith("[*]")
        key = segment[:-3] if multiple else segment
        if not key or not key.replace("_", "").isalnum():
            raise ValueError("invalid check path")
        if isinstance(payload, list):
            payload = [item.get(key, MISSING) if isinstance(item, dict)
                       else MISSING for item in payload]
        elif isinstance(payload, dict):
            payload = payload.get(key, MISSING)
        else:
            return MISSING
        if multiple and not isinstance(payload, list):
            return MISSING
    return payload


def equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    return a == b


def evaluate(payload, checks):
    out = []
    for check in checks:
        value = at(payload, check["path"])
        passed = (value is MISSING if "absent" in check else
                  value is not MISSING and equal(value, check["equals"]))
        out.append({"path": check["path"], "passed": passed})
    return out


async def protocol(benchmark, probes, catalog_file):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from .importers import load_catalog
    cases, steps, hashes = suite(benchmark, probes)
    catalog = load_catalog(catalog_file)
    if ([p.sku for p in catalog.products] != ["tea-001", "tea-002"]
            or any(not p.is_demo for p in catalog.products)):
        raise ValueError("only the frozen synthetic two-product fixture is permitted")
    catalog_hash = hashlib.sha256(Path(catalog_file).read_bytes()).hexdigest()
    params = StdioServerParameters(command=sys.executable,
        args=["-m", "miseport.server", "--catalog", str(Path(catalog_file).resolve())],
        env={**os.environ, "PYTHONUTF8": "1"})
    outcomes = []
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer,
                                 read_timeout_seconds=timedelta(seconds=10)) as session:
            await session.initialize()
            listing = await session.list_tools()
            available = {t.name: t for t in listing.tools}
            safe_tools = (set(available) == TOOLS and all(
                t.annotations is not None and t.annotations.readOnlyHint is True
                for t in available.values()))
            for case, probe in zip(cases, steps):
                start = perf_counter()
                findings, error = [], None
                try:
                    reply = await session.call_tool(probe["tool"], probe["arguments"])
                    if reply.isError:
                        error = "MCP isError"
                    elif not reply.content or not hasattr(reply.content[0], "text"):
                        error = "MCP response has no text"
                    else:
                        response = json.loads(reply.content[0].text)
                        if not isinstance(response, dict):
                            raise ValueError("invalid MCP JSON object")
                        findings = evaluate(response, probe["checks"])
                except (ValueError, TypeError, KeyError):
                    error = "invalid MCP payload"
                outcomes.append({"id": case["id"], "tool": probe["tool"],
                    "passed": error is None and len(findings) == len(probe["checks"])
                              and all(x["passed"] for x in findings),
                    "checks": findings, "error": error,
                    "elapsed_ms": round((perf_counter() - start) * 1000, 2)})
    passed = sum(x["passed"] for x in outcomes)
    return {"schema_version": "miseport-eval/1.0",
            "evaluation_type": "local_mcp_protocol_probes",
            "agent_answer_evaluated": False, "natural_discovery_evaluated": False,
            "merchant_data_used": False, "host_status": "not_run", **hashes,
            "catalog_sha256": catalog_hash, "tool_metadata_safe": safe_tools,
            "case_count": 20, "passed": passed, "failed": 20 - passed,
            "cases": outcomes}


def host_review(benchmark, probes, traces):
    cases, _, hashes = suite(benchmark, probes)
    trace, trace_hash = load_json(traces)
    if (not all(isinstance(trace.get(k), str) and trace[k].strip()
                for k in ("host", "model", "captured_at")) or
                not isinstance(trace.get("cases"), list)):
        raise ValueError("host/model/captured_at/cases are required")
    records = {}
    for item in trace["cases"]:
        if not isinstance(item, dict) or item.get("id") in records:
            raise ValueError("invalid or duplicate host case")
        records[item["id"]] = item
    if set(records) - {c["id"] for c in cases}:
        raise ValueError("unknown host case id")
    out = []
    for case in cases:
        entry = records.get(case["id"])
        reviewed, passed, calls, errors = False, False, 0, 0
        if entry is not None:
            tool_calls = entry.get("tool_calls")
            if (not isinstance(tool_calls, list) or any(
                    not isinstance(x, dict) or x.get("name") not in TOOLS
                    or type(x.get("is_error")) is not bool for x in tool_calls)):
                raise ValueError("invalid read-only tool_calls")
            calls = len(tool_calls)
            errors = sum(x["is_error"] for x in tool_calls)
            rev = entry.get("review")
            reviewed = (isinstance(entry.get("answer"), str)
                and bool(entry["answer"].strip())
                and isinstance(entry.get("reviewed_by"), str)
                and bool(entry["reviewed_by"].strip())
                and isinstance(rev, dict)
                and isinstance(rev.get("observed_product_ids"), list)
                and all(isinstance(x, str) for x in rev["observed_product_ids"])
                and all(type(rev.get(k)) is bool for k in REVIEW))
            if reviewed:
                passed = (sorted(rev["observed_product_ids"]) ==
                    sorted(case["expected_product_ids"]) and all(rev[k] for k in REVIEW))
        out.append({"id": case["id"],
            "status": "unreviewed" if not reviewed else "passed" if passed else "failed",
            "tool_call_count": calls, "tool_error_count": errors})
    return {"schema_version": "miseport-eval/1.0",
            "evaluation_type": "human_annotated_host_trace",
            "host_status": "user_supplied_not_independently_verified",
            "review_method": "human_labels_not_model_judge",
            "agent_answer_evaluated": any(x["status"] != "unreviewed" for x in out),
            "natural_discovery_evaluated": False, "merchant_data_used": False,
            "host": trace["host"], "model": trace["model"],
            "captured_at": trace["captured_at"], **hashes,
            "trace_sha256": trace_hash, "case_count": 20,
            "reviewed": sum(x["status"] != "unreviewed" for x in out),
            "passed": sum(x["status"] == "passed" for x in out),
            "failed": sum(x["status"] == "failed" for x in out),
            "unreviewed": sum(x["status"] == "unreviewed" for x in out),
            "tool_calls": sum(x["tool_call_count"] for x in out),
            "tool_errors": sum(x["tool_error_count"] for x in out), "cases": out}


def write_report(path, data):
    target = Path(path)
    if not target.parent.is_dir():
        raise ValueError("create the report parent directory first")
    pending = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                dir=target.parent, prefix=".eval-", suffix=".tmp", delete=False) as f:
            pending = Path(f.name)
            json.dump(data, f, ensure_ascii=False, allow_nan=False, indent=2)
            f.write("\n")
        os.replace(pending, target)
    finally:
        if pending is not None and pending.exists():
            pending.unlink()


def main():
    parser = argparse.ArgumentParser(prog="miseport-eval")
    parser.add_argument("mode", choices=("protocol", "host"))
    parser.add_argument("--benchmark", default="tests/fixtures/muse-benchmark-20.reference.json")
    parser.add_argument("--probes", default="tests/fixtures/muse-eval-probes-v1.json")
    parser.add_argument("--catalog", default="tests/fixtures/demo-store.reference.json")
    parser.add_argument("--traces")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.mode == "protocol":
            report = asyncio.run(asyncio.wait_for(
                protocol(args.benchmark, args.probes, args.catalog), timeout=90))
        else:
            if not args.traces:
                parser.error("host mode requires --traces")
            report = host_review(args.benchmark, args.probes, args.traces)
        write_report(args.output, report)
    except (OSError, ValueError, TimeoutError) as exc:
        parser.error(str(exc))
    print(json.dumps({k: report[k] for k in ("evaluation_type", "case_count", "passed", "failed")}))
    if report["failed"] or (args.mode == "protocol" and not report["tool_metadata_safe"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
