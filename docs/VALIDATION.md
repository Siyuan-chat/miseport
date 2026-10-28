# Local validation — 2026-10-28

## GitHub validation — 2026-10-29 (latest)

Public repository: [Siyuan-chat/miseport](https://github.com/Siyuan-chat/miseport). Tested code commit: `cf8e70005ece393e87507e40571c5f72a9f15e38`. [Run 40779008149](https://github.com/Siyuan-chat/miseport/actions/runs/40779008149) completed **7/7 jobs successfully**: Ubuntu and Windows with Python 3.10/3.12/3.14, each running source tests, static checks, build and installed-wheel tests; plus the Docker build/nonroot catalog validation job. Online checks are actual results, not the local-only historical counts below.

First online run `40778720332` failed because installed-wheel verification assumed an existing artifacts parent directory. The product/source tests and container were not the cause of that failure. Fixed explicit parent creation and disabled matrix fail-fast for complete diagnostics. Reproduced a clean source-only extraction locally with no artifacts directory: 106 passed in 5.79 s (`artifacts/clean-checkout-ci-fix-log/`). Corrected online run then passed. Raw first-failure log saved locally at `artifacts/remote-ci/run-40778720332-failure.log`. Windows MCP entry-point lookup uses the interpreter's scripts directory; targeted local protocol regression passed.

Remote initial upload had 76 file blobs, all matched against local Git hashes. No credential files, virtual environments, local logs or historical ZIP/wheel binaries were uploaded. Public source/CI are complete for this phase; domain, remote service, Muse client scenarios and final visual signoff remain outside these passing checks.

## Earlier local records

Expanded development 2026-10-29: **106 passed in 6.17 s** on Python 3.14 current source (`artifacts/commerce-final314.xml`), after legacy/canonical adapters, quantity quotes, inventory, audit, JSON-LD and seven stdio tools. Final wheel independently installed in Python 3.10.11: **106 passed in 6.63 s**, dependency check passed, import confirmed from site-packages; full logs in `artifacts/commerce-wheel310-20261029/` and JUnit in `artifacts/wheel-verification.xml`. Build logs: `artifacts/commerce-build-20261029/`. Tests include actual CLI subprocesses, provenance tamper rejection, import atomicity, full protocol tools and fixture-bound price/evidence assertions. These are not Muse language-model evaluations. Current schemas exported from models; site static checks still pass. GitHub owner/target lookup conditions are in `GITHUB_TESTING.md`; Actions have not run.

Legacy reconciliation verification 2026-10-29: supplied standalone brand/checklist match their ZIP members; historical wheel's five modules match ZIP source. Input SHA-256: `references/legacy-20261027/provenance.json`. No legacy code executed. Current Python 3.14 suite after canonical about-tool metadata restoration: **36 passed in 3.78 s**, `artifacts/tests-legacy-reconcile.xml`. Static site: 24 complete translation pairs and 5 valid local links/assets. See `LEGACY_BASELINE.md` for incompatible contracts and deferred features.

Brand update 2026-10-29: the user supplied the original storefront logo and visual board. The v01 logo checks below remain historical and apply only to the superseded M candidate. Current original PNGs are preserved byte-for-byte; see `assets/original/provenance.json` and `docs/BRAND.md`. Browser verification remains pending.

This is evidence for the new implementation in this checkout, not the historical ZIP. No Git commit existed at baseline. All checks below ran on Windows; CI and container files are drafts until their target environments run them.

| Check | Actual result | Evidence |
|---|---|---|
| Editable install, Python 3.14 | Passed, MCP 1.28.0 / Pydantic 2.14.1 | `.venv`, installed package metadata |
| Full suite, Python 3.14 | 36 passed in 3.11 s | `artifacts/tests.xml` |
| Built wheel installed separately, Python 3.10.11 | Passed; imported from wheel environment site-packages | `artifacts/wheel-env/` |
| Full suite against installed wheel, Python 3.10.11 | 36 passed in 4.89 s | `artifacts/tests-wheel310.xml` |
| Installed `miseport` entry point | Validated 4 products | local command `artifacts/wheel-env/Scripts/miseport.exe validate examples/products.json` |
| Dependency consistency, wheel environment | No broken requirements | `pip check` |
| Build wheel from sdist + sdist | Passed | `artifacts/final-build/` complete stdout/stderr and index |
| Static site | 24 translation pairs / 5 local links-assets valid | `scripts/check_site.py` |
| Light/dark SVG and favicon structure | Passed strict contours; self-contained | skill validation helper; local SVG files |
| Logo rendering | Actual SVG rasterized at 4×; light/dark, normal size, favicon reviewed | `assets/brand-v01-review.png` |

Tests cover malformed/missing/oversized catalogs, invalid product fields, duplicate SKU/JSON fields, CSV consistency, unknown stock and costs, Japanese normalization/AND queries, filters/pagination, import atomicity, CLI subprocesses and actual MCP stdio initialization/list/call. Protocol tests invoke the installed `miseport-mcp` entry point, check exact tools and read-only annotations, empty/missing results, strict integer arguments and unknown-tool errors. Client read timeout is 10 s; overall protocol test bound is 30 s. These bounds are configured, not a separate induced-timeout test.

The first sandbox run had temp-directory and subprocess permission failures (8 passed, 24 errors, 1 failed); an authorized local-process rerun passed. Review then identified deep JSON error handling and MCP parameter coercion; both were fixed and regression-tested. An intermediate regression used a decoder-specific error expectation and failed on Python 3.14, which parses that nesting depth before rejecting the row; the test now checks the catalog-error contract across both Python versions.

Still unverified: browser rendering/mobile layout/language-button interaction, Docker build/run, Linux and Python 3.12 matrix, public package-name availability, final GitHub repository/domain ownership, hosted transport/auth, Muse eligibility/Japan availability and real client end-to-end behavior. Browser file preview was blocked by the browser URL security policy, so no alternate browser route was attempted. The 20 Japanese client scenarios remain an acceptance plan, not 20 passing tests. Brand v01 is a candidate, not user-approved final art. No public deployment, push, publication, payment, order or scheduled process has occurred.
