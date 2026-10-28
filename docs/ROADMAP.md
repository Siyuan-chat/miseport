# MisePort roadmap — reconciled 2026-10-29

Brand and launch target come from the user's original charter: MisePort, 2026-11-10 JST. The old Oct 27–Nov 10 dates are historical planning, not proof those stages ran. Current executable scope remains local development and reviewable drafts; external actions require their corresponding authorization. `../PROJECT_STATUS.md` is the single current state entry.

| Window (JST) | Deliverable / exit criterion |
|---|---|
| Oct 29 | Reconcile recovered legacy source, current tested core and original brand; preserve input identity and incompatible API/schema differences |
| Oct 30–31 | Review original-logo production and schema/API decisions for audit, merchant provenance, quote/JSON-LD and legacy adapters; complete only selected, tested scope |
| Nov 1–2 | Finish local packaging/CI/container verification; choose and independently test remote SDK/transport before any hosted-service claim |
| Nov 3–4 | Validate bilingual website on desktop/mobile; prepare actual host/domain, SEO metadata and deployment/rollback materials |
| Nov 5–6 | Verify Muse eligibility; run fixture-bound 20-query client benchmark if access is available; otherwise document exact block and independent protocol results |
| Nov 7–8 | Candidate security/license/content review, original brand assets, demo and community drafts; obtain any needed external-action authorization |
| Nov 9–10 | Final maintainer-controlled release gates; publish/deploy/submit only when authorized and ready; record evidence and outstanding third-party review separately |

Recovered evidence audit, merchant attributes, snapshot quotes, inventory queries and Product JSON-LD have now been implemented locally with a validated legacy adapter and regression tests. Demo-only hosted service, external client evaluation, final brand approval and community submission remain separate gates. See `LEGACY_BASELINE.md` and `API.md`.

Repository [Siyuan-chat/miseport](https://github.com/Siyuan-chat/miseport) is now public and uploaded, with seven successful GitHub CI jobs (see `GITHUB_TESTING.md`). Domain `miseport.dev`, optional docs alias and `api.miseport.dev/mcp` remain planned targets. Merchant outreach, OAuth/platform integration, transactions, domain purchases and external directory/platform submissions are not activated by the old roadmap. No promise is made about third-party approval or merchant uptake by Nov 10.
