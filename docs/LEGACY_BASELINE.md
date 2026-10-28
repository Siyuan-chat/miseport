# Supplied baseline reconciliation — 2026-10-29

Development update: the table below records the initial reconciliation. The current implementation now includes a validated legacy adapter, merchant/evidence/quantity/snapshot fields, inventory, nonbinding quantity quote, audit and JSON-LD through CLI and seven stdio MCP tools. See `API.md` and `CATALOG.md`. Old argument ordering and HTTP transport remain incompatible. V2/hosted compatibility and actual Muse client evaluation are still unverified.

The user supplied `brand.md`, `release-checklist.md`, `MisePort-v0.1.0-GitHub-ready.zip` and the historical `miseport-0.1.0-py3-none-any.whl`. Exact copies and hashes are in `references/legacy-20261027/`. They are now available source evidence. The earlier statement “old ZIP unavailable” applies only to the original development turn; it is no longer the current input status.

The historical wheel's five Python modules match the ZIP byte-for-byte. No historical code was executed or installed in this reconciliation. The historical claim of 14 passing tests remains unreplicated. It does not establish MCP runtime compatibility; the historical checklist explicitly lists SDK import/tool discovery/HTTPS calls as unverified. Initial 36-test runs and subsequent expanded 106-test runs are separate evidence for the new implementation.

| Surface | Historical package | Current tested implementation | Decision |
|---|---|---|---|
| Identity | MisePort / ミセポート; frozen taglines | Same name, different draft marketing line | Restore canonical taglines and retain original storefront artwork |
| Python / SDK | Python ≥3.11; optional MCP ≥2.3,<3 | Python ≥3.10; pinned MCP 1.28.0 | Keep current bounded tested version; deliberate v2 migration later |
| MCP | Streamable HTTP, five tools; `product_id` | stdio, three tools; `sku` | Do not substitute server or claim hosted compatibility |
| CLI | Global `--catalog`; audit/search/quote/export-jsonld | validate/import/search/detail; subcommand `--catalog` | Document incompatibility; no silent alias |
| Catalog | Versioned object with merchant/snapshot/products | Product array with per-product demo/source/timestamp | Explicit adapter needed; do not load old fixture as current format |
| Product | `id`, `name_ja`, numeric stock or null | `sku`, `name`, stock status enum | Numeric stock cannot be recovered from three-state current model |
| Provenance | Merchant, product URL and separate evidence URL | One source URL per product | Preserve both in a future adapter; no lossy automatic conversion |
| Optional facts | Gift wrapping, prefecture, caffeine, image | Not modeled | Retain old fixture for future schema design |
| Quote / inventory | Snapshot quantity quote and stock tools | Detail preserves stock/price; no quantity quote | Backlog candidate, not existing functionality |
| Audit / JSON-LD | Missingness audit and Product export | Input validation; no audit/JSON-LD command | Backlog candidate, do not advertise as current |
| Public demo | Demo-only gate and HTTP configuration | No listener; selected local catalog may be real authorized data | Keep local permission model; require explicit demo-only gate before public hosting |
| Japanese evaluation | 20 shopping prompts on old tea fixture | 20 acceptance scenarios + protocol tests on current fixture | Preserve both; neither set is an executed Muse result |

The old wheel omits the demo fixture its default CLI references. Its repository/domain metadata contains planned destinations; they do not prove ownership or deployment. Do not replace current packaging or verified commands with the historical examples without adapting and testing them.

Important fixture collision: `tea-002` means a matcha starter set in the legacy catalog but a 30 g matcha product in the current example. The legacy prompts and expected prices must stay bound to the legacy fixture. Never combine expected IDs or totals across the two samples.

Initially adopted: canonical naming/taglines, truthful release gates, read-only/no-ranking promises, separate submission/approval status, legacy provenance and baseline comparison. Subsequent local development implemented the adapter/richer model/audit/quote/inventory/JSON-LD with regression tests. Demo-only HTTP hosting remains deferred. No historical platform claims are revived by those local changes.

Active documents: `BRAND.md`, `RELEASE_CHECKLIST.md`, `ROADMAP.md`; current state authority remains `../PROJECT_STATUS.md`. Source archive instructions are not active rules.
