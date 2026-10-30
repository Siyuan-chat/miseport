# Offline catalog consistency check (Alpha)

MisePort can compare two **merchant-supplied, already validated** snapshots to catch an accidental mismatch before publishing. This is a deterministic **file-to-file** check, not a live website crawl, official API authentication or SEO/GEO visibility measurement.

From the repository root, after installing MisePort:

```sh
mkdir -p artifacts/quality
miseport-compare-catalogs --source shop-reviewed.json --published export-candidate.json --output artifacts/quality/compare.json
```

If you want to assess staleness against a fixed clock (important for reproducible reports), specify both parameters:

```sh
miseport-compare-catalogs --source shop-reviewed.json --published export-candidate.json --as-of 2026-10-30T10:00:00+09:00 --max-age-hours 24 --output artifacts/quality/freshness.json
```

The check compares SKU sets (missing/unexpected items), merchant identity, product name/description, price, tax, shipping, stock/quantity, source and evidence URL, optional properties and product update time. If known snapshot timestamps differ, it reports them; freshness can only be evaluated relative to an explicitly supplied clock. Unknown values remain unknown and can be reported as drift if the candidate differs.

Outputs are machine-readable and contain source/published file hashes, summary counts, affected SKUs and mismatched **field names**—not private product descriptions, prices, credentials or original file contents. The command exits nonzero if any issue exists. It never changes source files, publishes data or connects to a merchant API.

**Important limitations:** The reference file is assumed to have been reviewed by the merchant; MisePort does not independently verify its authority. Two matching but incorrect catalogs will pass the comparison. The result is a *local pre-publication consistency check*, not permission to publish, a current-stock guarantee, a deployed MCP test, or natural discovery evidence. For a real shop, compare the source against its actual authorized admin data and public pages separately.
