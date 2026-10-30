# Japanese shopping Agent Eval v0.1

This suite builds on the 20 existing Japanese shopping prompts. It deliberately **separates predetermined MCP protocol checks from an actual agent choosing a tool or composing an answer**.

## E0 — local protocol baseline (automated)

From the repository root, after installing the Python package:

```bash
mkdir -p artifacts/eval
miseport-eval protocol --output artifacts/eval/protocol.json
```

The runner opens a real local stdio MCP connection, discovers the seven read-only tools and calls 20 explicit, fixed argument sets from `tests/fixtures/muse-eval-probes-v1.json`. It checks response fields, null/unknown behavior, timestamps, product IDs and safety boundaries against the frozen two-product synthetic catalog. The report includes the three input SHA-256 hashes, per-case timing, pass/fail details, and the detected read-only tool metadata. No merchant API calls or model inference are performed.

**20/20 here means 20 preselected read-only MCP probes passed. It does NOT mean a language model understood 20 shopping questions, cited the website, used MisePort unprompted, or discovered a merchant.** The program refuses non-synthetic or wrong-SKU catalogs for this baseline.

## E1 — connected Agent transcript import (manual review)

Run the Japanese prompts separately in a genuinely connected host such as an authorized MCP client, preserve actual results privately, and record the actual host/model/version/date. Create a JSON file with the following shape (the values below are a **format illustration, not an observed run**):

```json
{
  "host": "example-host",
  "model": "actual-model-name",
  "captured_at": "2026-10-30T10:00:00+09:00",
  "cases": [
    {
      "id": "J01",
      "answer": "Paste the verbatim answer here.",
      "tool_calls": [{"name": "search_products", "is_error": false}],
      "reviewed_by": "human-reviewer",
      "review": {
        "observed_product_ids": ["tea-001"],
        "facts_grounded": true,
        "unknown_handled": true,
        "source_cited": true,
        "safe_behavior": true
      }
    }
  ]
}
```

```bash
miseport-eval host --traces /path/to/private-host-traces.json --output artifacts/eval/host-report.json
```

For each question, the reviewer must explicitly record the presented product IDs and assess grounded facts, unknown fields, citation correctness and safe behavior. Missing answer, reviewer or review flags → `unreviewed`; an incorrect annotated case → `failed`. The other questions remain unreviewed until included. The report contains a trace hash and counts but **does not reproduce raw transcripts**.

These manually supplied labels are **not verified independently**. The scorer does not parse answers, call an LLM judge, prove that the host or tool calls actually occurred, or test correctness of a citation URL. Original private transcripts should be kept for later audit. Never commit merchant secrets, shopping sessions or personally identifiable information. The evaluation is **synthetic-only** until a shop has independently authorized real data.

## E2–E4 — separate future measurements

- E2: unconnected Web/Feed natural product discovery, tested with separate controls and actual host runs, **not** inferred from an MCP connection.
- E3: official connector directory status, requiring independent provider evidence.
- E4: discoverability of the MisePort OSS project itself.

Do not combine the above into a single GEO ranking score. Host comparisons should specify catalog version/hash, time, model, settings and repeated trial counts. Actual recommendation lift and natural exposure are untested.
