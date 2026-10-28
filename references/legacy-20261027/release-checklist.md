# MisePort — day-0 migration and release checklist

**Snapshot:** 2026-10-27 JST. This document is an implementation and test record, not evidence of public hosting.

## Verified locally

- Naming contract: `MisePort` / `ミセポート` / `miseport` across Python, CLI, server name, `about_miseport`, `MISEPORT_*`, static pages, JSON-LD, sitemap, schema URI, community connector and launch plan.
- Python `unittest discover -s tests -v`: **14 tests passed** on this workspace (core + brand-integrity tests).
- `python -m pip wheel . --no-deps --no-build-isolation`: **success**, `miseport-0.1.0-py3-none-any.whl`.
- `PYTHONPATH=src python -m miseport.cli ... audit/search/export-jsonld`: returned valid JSON for the synthetic fixture.
- Source archive is generated from tracked-source candidates only; no `__pycache__`, build output or credentials.

## Not yet verified

- `miseport.dev` registration, trademark clearance or DNS/TLS ownership.
- Public GitHub repository (must be created separately), GitHub Actions run, PyPI publishing.
- Actual MCP SDK 2.x runtime import, tool discovery and a remote HTTPS MCP call.
- Meta Muse custom connector compatibility, directory approval, AI model recommendations.
- Search-engine crawling/indexing or real merchant adoption.

## First GitHub push (after creating an empty public repository)

```bash
unzip MisePort-v0.1.0-GitHub-ready.zip
cd miseport
git init -b main
git add .
git commit -m "Initial open-source MisePort v0.1.0 MVP"
git remote add origin https://github.com/Siyuan-chat/miseport.git
git push -u origin main
```

This will not work until the account owner creates `Siyuan-chat/miseport` and authenticates locally. Avoid pushing the code to an unrelated project. Confirm GitHub URLs and CI status before advertising them as live.

## Before publication to Muse or the community

1. Verify registrar/domain ownership, legal/trademark clearance, HTTPS, Host/Origin allowlists and abuse controls; only then promote planned hostnames to working URLs.
2. Test `initialize`, `tools/list`, `tools/call` with the actual MCP SDK, MCP Inspector and Muse custom connector; save redacted run evidence. Do not present source-defined tools as working until tested.
3. Update `docs/llms.txt`, site, README and community skill with dated **actual** availability. Read-only synthetic demo must be explicit.
4. Submit PR to community `awesome-muse-connectors` per upstream CONTRIBUTING, using `community/awesome-muse-connectors/miseport/SKILL.md` as draft; community is not Meta's official listing.
5. Submit to Meta only if eligibility, identity/security and end-to-end verification requirements are satisfied. Submission is not approval.

See [`roadmap.md`](roadmap.md) for the October 27–November 10 daily deliverables, and [`brand.md`](brand.md) for the frozen naming contract.
