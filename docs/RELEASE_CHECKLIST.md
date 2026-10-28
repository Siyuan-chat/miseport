# MisePort release gates

Reference: user-supplied 2026-10-27 checklist; reconciled 2026-10-29. Current status and evidence authority: `../PROJECT_STATUS.md` and `VALIDATION.md`. This is a checklist, not authorization to publish. The old 14-test record is historical; current local protocol evidence applies only to the current implementation.

## Local baseline

- [x] Canonical MisePort / ミセポート / `miseport`, CLI, `about_miseport`, `MISEPORT_` and Apache-2.0 established.
- [x] Original storefront logo and brand board preserved; canonical taglines restored.
- [x] Current JSON/CSV → validation → search/detail → merchant URL chain tested.
- [x] Current seven-tool stdio MCP initialize/list/call tested; strict arguments, unknown facts and errors covered.
- [x] Expanded 106-test suite passed on Python 3.14 editable and Python 3.10 installed-wheel environments (see dated validation).
- [x] Local wheel/sdist built; original images and historical reference provenance recorded.
- [x] Original-logo vector/transparent/reverse/favicon reconstruction candidate produced and structurally/render reviewed.
- [ ] Original-logo reconstruction approved by user as final master.
- [ ] Desktop/mobile website and language interaction visually verified.
- [x] CI matrix and container built/run in GitHub target environments; all seven jobs passed at `cf8e700` (see `GITHUB_TESTING.md`).
- [x] Public `Siyuan-chat/miseport` repository created and reviewed source uploaded under explicit user authorization.

## Before public hosting or package release

- [ ] Verify account ownership, target repository, package-name availability and chosen host/domain; do not advertise targets as live.
- [ ] Choose remote transport/API compatibility and complete SDK migration tests if changing the current pin.
- [ ] Implement/review auth, tenant isolation or demo-only gate, Host/Origin controls, request/rate limits, privacy/log retention and incident contact.
- [ ] Confirm catalog rights and exclude secrets/customer/private merchant data; verify distribution contents and dependency/license inventory.
- [ ] Verify HTTPS endpoint with Inspector and an independent host; retain redacted initialize/list/call/error evidence.
- [ ] Publish only after the corresponding user authorization; verify actual URL, commit/tag, artifact hashes and CI evidence afterward.
- [ ] Check canonical/hreflang/robots/sitemap against actual public destinations before indexing submissions. Do not ship invented live URLs or search ranking guarantees.

## Muse and community

- [ ] Verify official platform requirements, account eligibility and Japan availability with current primary sources.
- [ ] Run at least 20 Japanese shopping scenarios on a clearly identified fixture and host; record date, tool calls, unknown facts, errors and outcome. Legacy expected IDs/totals apply only to its legacy fixture.
- [ ] Adapt old community drafts to the actual current API and verified endpoint; inspect upstream contribution rules.
- [ ] Obtain authorization for external submission/messages, then retain submission evidence.
- [ ] Record submitted, accepted/listed and officially approved separately. A community directory is not official platform approval; neither guarantees recommendations or traffic.

## Cutover and rollback

Before the first release, assign one canonical artifact identity and version, checksum and changelog; old and new local packages both use 0.1.0 and must not be confused. Record the deployed commit/config/catalog identity, restore procedure and service owner. No copied shell command in the historical checklist is permission for a push, purchase, deployment or submission.
