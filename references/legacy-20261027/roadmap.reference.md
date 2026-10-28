# MisePort — frozen 14-day launch charter

**Freeze date / final naming approval:** Tuesday 2026-10-27 (JST)  
**Target launch completion:** Tuesday 2026-11-10 (JST)  
**Canonical brand:** MisePort  
**GitHub repository target:** `Siyuan-chat/miseport`  
**Primary hostname target:** `miseport.dev` (not purchased; registrar/RDAP and trademark screening still required)  
**Documentation:** `https://miseport.dev/` after DNS deployment; `https://docs.miseport.dev/` is an optional redirect to the canonical site, not a duplicate indexable website  
**Remote MCP:** `https://api.miseport.dev/mcp` after HTTPS deployment  
**License:** Apache-2.0

## Brand cutover / Day 0 acceptance

The local migration/test evidence and GitHub handoff procedure are in [`release-checklist.md`](release-checklist.md).

- The **MisePort** brand is frozen prior to any GitHub push, domain registration, package release or Muse application. See [`brand.md`](brand.md).
- Source package, CLI, MCP identity and about tool, `MISEPORT_*` environment variables, schema identifier, demo benchmark ID, GitHub target, site and community-directory path are renamed together.
- **No automatic redirects / renaming of public assets are required yet:** the earlier project was local-only, and GitHub targets are uncreated.
- Name search is preliminary, not trademark clearance; independently check the chosen domain with a registrar before purchase. Keep all planned URLs labeled unregistered until verified.
- Final D0 gate: local test suite, wheel, JSON + HTML metadata sanity, old-name scan, fresh archive; store command output with launch checklist.

## Scope freeze

The MVP is an open-source **Japanese merchant catalog normalization, evidence audit, JSON-LD export, and read-only MCP demo**. It is not a payments or ranking product. It supports synthetic product fixtures first and does not access production credentials. Merchant-authorized adapters and transaction workflows are later releases and need separate security reviews.

### Proposed development stack

Python >=3.11, standard-library deterministic core, MCP Python SDK 2.x, Docker for the HTTP demo, GitHub Actions CI, static bilingual GitHub Pages or Cloudflare Pages. One canonical product schema, not separate per-platform formulas. Independent merchant data ingestion stays behind future adapters. The standalone core can be imported by any Agent platform, not just Muse.

### Acceptance criteria (controlled by maintainer)

1. Public, independent repository with tagged `v0.1.0` and Apache-2.0, passing CI on Python 3.11/3.12/3.13.
2. Demo catalog and all five read-only MCP tools respond; MCP Inspector and a second host verified against public HTTPS endpoint.
3. No private merchant data, write, checkout or payment function enabled; synthetic data conspicuously marked.
4. Japanese and English SEO pages reachable with correct 200 HTTP status, canonical/hreflang, sitemap, Search Console submissions, no blocked robots.
5. `SKILL.md` / `llms.txt` / README and real integration examples published for discoverability (not as a guarantee of model indexing).
6. Public launch note, repo topics, community directory submission where its contribution rules permit, and Muse Connector Platform intake submitted **only if** real service, business verification, auth, privacy and end-to-end review requirements are satisfied.
7. Baseline eval log of at least 20 Japanese shopping queries, with date, input, host, catalog version, correct/incorrect fields and access status. If no public MCP, log blocked/unfinished, not a success.

## Detailed schedule (JST)

| Date | Work | Exit condition |
| --- | --- | --- |
| Oct 27 (D0) | Approve MisePort name and cut over package, MCP metadata, demo, docs, site, brand policy, license and domain target; run local regression suite. | Canonical MisePort names across artifacts; local tests and package build pass; no stale working-brand strings. |
| Oct 28 (D1) | Create dedicated public `Siyuan-chat/miseport` repo, apply topics, first push and CI. Check `miseport.dev` registrar availability and Japan trademark classes before considering registration. | Public MisePort repo / commit URL and CI evidence; registrar or DNS ownership recorded only after confirmation. |
| Oct 29 (D2) | Harden parser, evidence rules, pricing/inventory unknowns; smoke MCP SDK v2. | CI + verified MCP Inspector calls. |
| Oct 30 (D3) | Deploy synthetic HTTPS MCP server with allowed host/origin, rate limiting/abuse policy; check logs. | Server endpoint accessible without publishing secrets. |
| Oct 31–Nov 1 (D4–5) | Publish Japanese & English landing pages, FAQ, JSON-LD, robots, sitemap, and only then submit Search Console property for the verified hostname. | Public URLs and crawlability checks. |
| Nov 2 (D6) | Audit public ecosystem / merchants; finalize BASE OAuth adapter requirements; check makeshop GraphQL (old REST retirement). | Platform compatibility matrix with verified sources. |
| Nov 3–4 (D7–8) | Run 20-query Muse/GEO benchmark on synthetic catalog, include negative tests and source snapshots. | Reproducible eval fixtures + report, no invented ranking score. |
| Nov 5 (D9) | Record 90-second demo and integration guide; prepare third-party listing metadata. | Working demo + reproducible setup guide. |
| Nov 6 (D10) | Submit documentation/community PR to independent Awesome Muse Connectors if contribution criteria met. | Public PR/issue URL or documented inability. |
| Nov 7–8 (D11–12) | Try first authorized Japan merchant pilot; invite ~20 relevant small shops; implement only approved public-data import. | At least an outreach and consent log, not guaranteed merchant participation. |
| Nov 9 (D13) | Security review, license attribution, changelog, CI, SEO site audit and release candidate. | No critical issues; publishable repo and demo. |
| Nov 10 (D14) | Tag v0.1.0, publish launch note and links; submit official Muse connector **if eligibility verified**; otherwise publish outstanding review checklist. | Live maintainer-controlled assets, evidence of submissions and honest status. |

## Critical external dependencies

- **Domain registration:** this plan chooses `miseport.dev` as target but does not reserve/buy it. If it is unavailable, select a new canonical domain before DNS and indexing. Until then, use the actual GitHub Pages/Cloudflare preview URLs, not fake live URLs.
- **GitHub repository creation:** must be completed by account owner with appropriate account permissions. A folder in another repository is not equivalent.
- **Official Muse listing:** Meta controls business verification, risk, tool, and end-to-end review; we can submit but cannot guarantee acceptance by Nov 10.
- **Developer community:** the independent `awesome-muse-connectors` GitHub repository is not an official Meta forum; PR acceptance depends on its maintainers.
- **Real merchants:** integrating product data and enabling checkout require explicit merchant consent, platform API access and separate authorization/review. No OAuth secrets belong in code.

## Release performance metrics

Track test pass rate, response latency p50/p95, complete-and-supported quoted total ratio, provenance coverage, Search Console indexing status, unique referring domains, agent-tool call completion and zero unapproved writes. Avoid unsupported "Muse ranking" or "guaranteed agent traffic" statements. Future transaction metrics are a later milestone.

## MisePort launch evidence ledger (update during sprint)

| Item | As of 2026-10-27 | Evidence / next check |
| --- | --- | --- |
| Brand, naming and local source migration | Done locally; not public | `docs/brand.md`; tests and package build |
| Public repository | Not created | `https://github.com/Siyuan-chat/miseport` is target only |
| Domain ownership and TLS | Not verified | Registrar purchase receipt + DNS/TLS inspection |
| MCP package import / HTTP tool calls | Not externally tested | MCP Inspector transcript + version record |
| SEO/GEO indexability | Planned, no live data | Search Console property + server response / indexing status |
| Independent community PR | Draft only | Public PR URL once sent |
| Muse custom connector | Not tested | Real host tool list and calls |
| Official Muse review | Not submitted | Submission ID, if eligible; approval is a separate state |
