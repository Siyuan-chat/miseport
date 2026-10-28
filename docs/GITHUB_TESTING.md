# GitHub test handoff

Prepared 2026-10-29. The local implementation and CI workflow passed local verification. User subsequently authorized repository creation and source upload. Public `https://github.com/Siyuan-chat/miseport` now exists (ID 1437666658), confirmed via GitHub connector; source upload/online CI verification is in progress. No public release, package publication or deployment is claimed.

## Target and resolved creation block

Intended repository: `Siyuan-chat/miseport`. On this check the connected account was `Siyuan-chat`, the direct repository lookup returned 404, and the owner-filtered accessible repository list did not contain MisePort. This means the target is not currently available through the connection; it does not prove no inaccessible repository exists. The connector has no create-repository operation, and no local `gh` executable was found. The project has no Git remote and no commits.

The user explicitly requested the agent create and upload. The authenticated Chrome session was used only for repository creation because the connector lacks that operation. Repository creation/access is now resolved; upload and verification use the GitHub connector. The existing local Git checkout remains separate from the API commit history until a later sync.

## Reviewable upload candidate

Run `python scripts/package_github.py`. It creates `artifacts/github-ready/MisePort-current-GitHub-ready.zip` and `manifest.json`. The archive uses an explicit source/document/asset allowlist; excludes `.git`, `.venv`, logs, caches, local wheels/builds and historical ZIP/wheel binaries; checks known credential patterns and forbidden filenames. Review the manifest before uploading. Pattern scanning is not a full secret/security audit. Keep original historical binary packages locally under `references/`.

The source archive is for a Git checkout, not a web deployment. The static site references sibling assets/docs. No live endpoint or GitHub badge should be advertised until actually verified.

## CI behavior

`.github/workflows/ci.yml` runs on push, pull_request and manual workflow_dispatch. It grants only contents:read, disables persisted checkout credentials and bounds job time. Matrix: Ubuntu and Windows × Python 3.10/3.12/3.14. Jobs install current dependencies, run contracts, static-site checks, build distributions, then `scripts/verify_distribution.py` installs the wheel and reruns the suite from site-packages. A separate Ubuntu job builds the container and validates its included catalog as the nonroot runtime user. Official current action usage was checked against [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python); v7 is used.

After upload, record the actual commit SHA and each workflow job URL/result. Diagnose failures against that exact revision, fix locally, upload again and wait for terminal CI results. Local test passes do not count as completed GitHub Actions jobs. No scheduled monitor has been created.
