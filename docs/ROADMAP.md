# MisePort roadmap — reconciled 2026-10-29

Brand and launch target come from the user's original charter: MisePort, 2026-11-10 JST. The old Oct 27–Nov 10 dates are historical planning, not proof those stages ran. **Current 2026-10-29 status:** public source, GitHub CI, a fictional Cloudflare HTTP/MCP demo, and account-local Muse connector validation have been recorded. The roadmap below is a planning baseline; production merchant integrations, independent brand approval and external submissions remain open and require the relevant authorization. `../PROJECT_STATUS.md` is the single current state entry.

| Window (JST) | Deliverable / exit criterion |
|---|---|
| Oct 29 | Reconcile recovered legacy source, current tested core and original brand; preserve input identity and incompatible API/schema differences |
| Oct 30–31 | Review original-logo production and schema/API decisions for audit, merchant provenance, quote/JSON-LD and legacy adapters; complete only selected, tested scope |
| Nov 1–2 | Finish local packaging/CI/container verification; choose and independently test remote SDK/transport before any hosted-service claim |
| Nov 3–4 | Validate bilingual website on desktop/mobile; prepare actual host/domain, SEO metadata and deployment/rollback materials |
| Nov 5–6 | Verify Muse eligibility; run fixture-bound 20-query client benchmark if access is available; otherwise document exact block and independent protocol results |
| Nov 7–8 | Candidate security/license/content review, original brand assets, demo and community drafts; obtain any needed external-action authorization |
| Nov 9–10 | Final maintainer-controlled release gates; publish/deploy/submit only when authorized and ready; record evidence and outstanding third-party review separately |

Recovered evidence audit, merchant attributes, snapshot quotes, inventory queries and Product JSON-LD have now been implemented locally with a validated legacy adapter and regression tests. The demo-only hosted service and account-local Muse client evaluation now have recorded acceptance evidence; final brand approval, real merchant integration and community/public-directory submissions remain separate gates. See `LEGACY_BASELINE.md` and `API.md`.

Repository [Siyuan-chat/miseport](https://github.com/Siyuan-chat/miseport) is now public and uploaded, with seven successful GitHub CI jobs (see `GITHUB_TESTING.md`). Domain `miseport.dev`, optional docs alias and `api.miseport.dev/mcp` remain planned targets. Merchant outreach, OAuth/platform integration, transactions, domain purchases and external directory/platform submissions are not activated by the old roadmap. No promise is made about third-party approval or merchant uptake by Nov 10.

## Product direction frozen on 2026-10-29

[Merchant-owned / local-first product charter (Japanese)](PRODUCT_STRATEGY.ja.md) is the controlling scope decision for **post-v0.1 merchant UX**: no central marketplace, open source and free-first, no-code browser import/export, optional merchant-owned hosting, versioned canonical contracts and adapters. The public demo remains synthetic-only; nontechnical self-service and actual merchant data deployment are **not implemented**. Do not expand the Nov 10 release into a centralized aggregator or payment service.

After the v0.1 release gates, the **preferred merchant entry point is API auto-ingestion**, not manual CSV: (1) a Japanese no-code connection wizard and safe read-only credential handling, with BASE v2 beta PAT as the first proposed adapter; (2) official platform CSV/JSON import as a permanent fallback and verified output profiles for major platforms; (3) merchant-owned deployable read-only package with audited publish/update/rollback steps; (4) first authorized merchant pilot measuring setup time, field fidelity, sync updates and answer accuracy; then (5) Shopify, Color Me, makeshop and other adapters. **BYO Agent** may supply data using authorized official tools but is never required. Platform export must be tested separately from the write-back operation. Each supported platform ships with Japanese illustrated instructions, error recovery, and a real screen-capture demo. See [ADR-0002](CONNECTOR_ARCHITECTURE.ja.md), [compatibility matrix](PLATFORM_COMPATIBILITY.ja.md), [merchant manual](merchant/SETUP_GUIDE.ja.md) and [video plan](merchant/VIDEO_DEMO_PLAN.ja.md). Keep hosting-account requirements visible; do not claim zero-cost, one-click setup or API compatibility before verification.
