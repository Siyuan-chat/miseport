# MisePort Roadmap — 11/10 Merchant-Usable Release

**Updated 2026-10-29 JST.** This page replaces the earlier developer-only 11/10 schedule. Planned milestones are not delivered capabilities. [Current evidence/status](../PROJECT_STATUS.md) · [Japanese detailed development plan](DEVELOPMENT_PLAN.ja.md) · [Hard release contract](RELEASE_2026-11-10.ja.md).

## P0: by 2026-11-10, a shop owner can actually use MisePort

- A merchant without programming skills can launch a Japanese Windows GUI and connect **their own BASE shop using official read-only API credentials**, fetch public products, review variants/prices/sources, and manually resync.
- The merchant can generate a shop-specific public-only catalog, JSON-LD and read-only MCP/REST hosting ZIP and deploy it at an **authorized merchant-controlled HTTPS URL** using documented steps.
- **At least one actual operating Japanese ecommerce merchant** has separately consented to data extraction and to public use of their name/URL/product examples/video. Publish a truthful real-store Agent query demo and dated case; a synthetic shop or unapproved/publicly scraped storefront does not count.
- Versioned distribution, validated Windows merchant workflow, secret-safe tests, Japanese screenshot manual and real-screen subtitled video are published.
- Optional CSV fallback is useful but **not a substitute for the API-auto-ingestion requirement**. No payments, central product index or promise of Agent automatic discovery.

### Critical path

| Date JST | Execution gate | Tracking |
| --- | --- | --- |
| **10/29** | Freeze merchant-ready scope; publish consent-based recruitment plan; check BASE API and existing core | [Release](RELEASE_2026-11-10.ja.md), [Pilot](merchant/PILOT_2026-11-10.ja.md) |
| **10/30–10/31** | Build BASE API mock and local GUI/security prototype; identify/contact 2–3 eligible merchants by authorized means; reach provisional participation | [#1](https://github.com/Siyuan-chat/miseport/issues/1), [#7](https://github.com/Siyuan-chat/miseport/issues/7), [#9](https://github.com/Siyuan-chat/miseport/issues/9) |
| **11/01** | Target one shop's separate extraction/publication permissions; successfully read real BASE API data | [#9](https://github.com/Siyuan-chat/miseport/issues/9) |
| **11/02–11/05** | Finish review/audit and merchant-specific deploy ZIP; obtain a distinct, merchant-approved HTTPS MCP/REST endpoint | [#2](https://github.com/Siyuan-chat/miseport/issues/2), [#8](https://github.com/Siyuan-chat/miseport/issues/8) |
| **11/06–11/08** | Windows distribution and independent nontechnical test; capture real shop demo and Japanese captions with permission; Agent client tests | [#4](https://github.com/Siyuan-chat/miseport/issues/4), [#9](https://github.com/Siyuan-chat/miseport/issues/9) |
| **11/09–11/10** | Merchant final approval, CI/security/rights and rollback review, GitHub Release and **one real-shop public case** | [#6](https://github.com/Siyuan-chat/miseport/issues/6) |

**Blocking dependency:** a real operating seller must consent and have eligible shop API access; there is **no confirmed participant as of this plan**. If not obtained, state that the release criterion is unmet. Do not label an internal synthetic demo as an external merchant success. Do not contact merchants or use real accounts without authorized channels/permission.

## Post-launch (only after P0)

- Extend native APIs to approved Shopify/Color Me/makeshop/EC-CUBE integrations as eligible, with version-specific permissions.
- Validate official platform CSV import **and** platform-compatible output separately; no writeback by default.
- Add optional merchant-owned scheduled sync/Webhooks, open Adapter interface, richer evidence/quality checks, and repeatable Japanese Agent benchmark.
- Remain free-first, single-shop-owned and protocol-independent; do not build a central marketplace.

**History:** The Git repository retains the superseded v0.1-developer / v0.2-December roadmap in version history. [ADR-0001](PRODUCT_STRATEGY.ja.md) and [ADR-0002](CONNECTOR_ARCHITECTURE.ja.md) still define product ownership and authorization boundaries; this page controls the immediate release scope.
