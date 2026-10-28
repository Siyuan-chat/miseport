# Deployment and submission preparation — draft

This document is a preparation guide. It does not certify deployment, security review, Muse eligibility, or submission acceptance.

## What exists in this scope

- A local Python package workflow, catalog validation/import/search/detail, inventory/reference quotes/audit/JSON-LD commands, and a read-only stdio MCP interface.
- `miseport-mcp`, configured with an absolute `MISEPORT_CATALOG` path.
- Seven MCP tools: `about_miseport`, `search_products`, `get_product`, `check_inventory`, `get_quote`, `audit_catalog`, `export_product_jsonld`.
- A static bilingual landing-page draft in `site/index.html`.

There is no public MCP service in this scope. Serving the HTML page does not make the stdio process remotely accessible. No payment, order, checkout, reservation, or customer-account capability is included.

## Local installation review

1. Use Python 3.10+ and an isolated virtual environment.
2. Install with `pip install -e '.[dev]'` from the project directory.
3. Validate the chosen catalog before connecting a client.
4. Set `MISEPORT_CATALOG` to that catalog's absolute path; confirm the client's process can read it and locate `miseport-mcp`.
5. Exercise each MCP tool and confirm protocol output is not mixed with diagnostic text. Record exact checkout, environment, input catalog, time, and failures.
6. Complete the Japanese acceptance scenarios and retain actual results separately. A planned scenario is not evidence of passing.

## Data and client boundaries

Only distribute catalog content that you are authorized to use. Exclude credentials, private supplier notes, and customer data. The connected client receives catalog results and may apply its own retention and data-processing policies. Review those policies before using real shop information.

Treat imported text and URLs as untrusted data. Do not execute catalog content, follow embedded instructions, or infer unknown tax, shipping, or stock. Preserve `source_url`, `updated_at`, and `is_demo`. A recorded stock value is not a reservation. Product source links can lead to third-party sites and must be reviewed by the user.

## Public service work that remains

A remote service would require a separately chosen supported transport, authentication and authorization, tenant isolation, rate limits, abuse handling, operational logs with a retention policy, dependency and secret management, and incident procedures. Design and review these controls before exposing a service. No remote endpoint or authentication compatibility is claimed here.

The static HTML draft has no analytics, external font, contact form, or purchase flow. Before publishing, verify all copy, accessibility, asset rights, links, and any required privacy/legal notices. Confirm the actual hosting destination and domain ownership. No production domain or repository URL is asserted by this draft.

## Muse / November 10 readiness

Muse participation, supported integration type, submission requirements, review timelines, and brand usage have **not been verified**. Confirm current official requirements before drafting a final submission. November 10 is a planning target only; neither review completion nor acceptance can be promised.

Before any public submission, record the official requirements and date checked; replace demo data only with authorized data; verify the repository and domain; provide reproducible installation evidence, real test results, support ownership, and a truthful privacy statement. Keep unsupported claims out of the site and submission.
