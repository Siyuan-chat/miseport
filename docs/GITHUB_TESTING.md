# GitHub test handoff

> **2026-10-29 update:** this handoff records the earlier GitHub creation/upload phase. Since that snapshot, a separate fictional Cloudflare HTTP/MCP demo and account-local Muse validation have been documented in [PROJECT_STATUS](../PROJECT_STATUS.md), [Cloudflare](CLOUDFLARE.md) and [Muse integration](MUSE_INTEGRATION.md). The historical statements below must not be interpreted as current availability.

Completed 2026-10-29. User authorized creation/upload of public [Siyuan-chat/miseport](https://github.com/Siyuan-chat/miseport) (repository ID 1437666658). Reviewed source was uploaded via GitHub connector, with 76 remote blob hashes checked against local content. Tested code commit: `cf8e70005ece393e87507e40571c5f72a9f15e38`. [Online test run](https://github.com/Siyuan-chat/miseport/actions/runs/40779008149) passed all seven jobs: Ubuntu/Windows × Python 3.10/3.12/3.14, plus container. No tagged release, package publication, hosted service or Muse integration is claimed.

The [first run](https://github.com/Siyuan-chat/miseport/actions/runs/40778720332) passed the container but failed installed-wheel verification because `artifacts` did not yet exist in a clean checkout; fail-fast cancelled remaining jobs. The verification script now creates the parent directory explicitly; a fresh local extraction passed 106 tests before the corrected complete online matrix succeeded. Matrix fail-fast is disabled so independent failures remain visible. The Windows executable path was also made installation-layout independent using `sysconfig.get_path('scripts')`.

## Target and resolved creation block

Intended repository: `Siyuan-chat/miseport`. On this check the connected account was `Siyuan-chat`, the direct repository lookup returned 404, and the owner-filtered accessible repository list did not contain MisePort. This means the target is not currently available through the connection; it does not prove no inaccessible repository exists. The connector has no create-repository operation, and no local `gh` executable was found. The project has no Git remote and no commits.

The authenticated Chrome session was used only for repository creation because the connector lacks that operation. Upload, commit and verification used the GitHub connector. Local Git main was attached to the same published history using an index-only operation without replacing working files; origin tracks the verified repository.

## Reviewable upload candidate

Run `python scripts/package_github.py`. It creates `artifacts/github-ready/MisePort-current-GitHub-ready.zip` and `manifest.json`. The archive uses an explicit source/document/asset allowlist; excludes `.git`, `.venv`, logs, caches, local wheels/builds and historical ZIP/wheel binaries; checks known credential patterns and forbidden filenames. Review the manifest before uploading. Pattern scanning is not a full secret/security audit. Keep original historical binary packages locally under `references/`.

The source archive is for a Git checkout, not a web deployment. The static site references sibling assets/docs. No live endpoint or GitHub badge should be advertised until actually verified.

## CI behavior

`.github/workflows/ci.yml` runs on push, pull_request and manual workflow_dispatch. It grants only contents:read, disables persisted checkout credentials and bounds job time. Matrix: Ubuntu and Windows × Python 3.10/3.12/3.14. Jobs install current dependencies, run contracts, static-site checks, build distributions, then `scripts/verify_distribution.py` installs the wheel and reruns the suite from site-packages. A separate Ubuntu job builds the container and validates its included catalog as the nonroot runtime user. Official current action usage was checked against [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python); v7 is used.

The result-recording follow-up changes documentation only and uses GitHub's supported `[skip ci]` commit message marker; the full successful code run above remains the test evidence. See `VALIDATION.md`. Future code changes require a fresh normal CI run. Local logs and `artifacts/github-ready/` are not committed; the GitHub repository is the published source of truth for uploaded history. No scheduled monitor has been created.
