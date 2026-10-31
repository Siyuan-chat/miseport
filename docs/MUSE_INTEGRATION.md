# Muse account-local integration acceptance

On **2026-10-29 (Asia/Tokyo)**, the account-local custom connector `custom.miseport-demo` (MisePort Demo) was created in Muse and then rediscovered and reused in a separate request. The endpoint is `https://miseport.pages.dev/mcp`, using stateless MCP Streamable HTTP, negotiated version `2025-11-25`, with no credentials. This verifies this account's custom connector against a fixed synthetic catalog. It is not a public connector-directory submission, Meta approval, a live merchant integration, or checkout support.

## Results

| Round | Actual tool call | Verified result |
|---|---|---|
| 1 | `get_product`, tea-001 | Fictional product, JPY 1,850, source and dated snapshot preserved |
| 1 | `check_inventory`, tea-001 | Recorded quantity 12; `stock_is_live: false` |
| 1 | `get_quote`, tea-001, quantity 2 | JPY 3,700 + 450 shipping = 4,150; nonbinding and not purchasable |
| 2 | `search_products`, ほうじ茶, in-stock only | One result; unknown-stock product excluded |
| 2 | `check_inventory`, tea-002 | `stock: unknown`, quantity null |
| 2 | `get_quote`, tea-002, quantity 2 | Subtotal 6,200; shipping and total null; incomplete total |
| 2 | `get_product`, does-not-exist | `found: false`, product null; normal domain result |

All seven recorded client calls exited 0 and returned `isError: false`. Root independently parsed the saved text content, checked it against `structuredContent`, and compared every result against the current Python catalog operations loaded from the legacy synthetic reference fixture: **7/7 exact matches**. Second-round client-process durations were 905, 626, 649 and 852 ms; these include initialization and notification overhead, not just server latency. First-round durations were not recorded and remain null.

Raw account-local test transcripts remain in an owner-controlled working archive and are not included in the public release source. This page summarizes the verified **synthetic-only** tool calls, their status and limits; it does not expose account-specific client workspace records. UI discovery and reuse traces, the local comparison script, and the completion screenshot are retained under `artifacts/muse-acceptance/` locally. The file-download event timed out; the JSON was saved through the file preview's Copy action and parsed successfully.

## Observed client issues and limits

Muse's initial generated client had compilation errors and attempted an incorrect direct JSON-RPC tool method. It was corrected to `method: tools/call`, with `params.name` and `params.arguments`, using `sku` rather than `product_id` as input. These initial attempts are not counted as successful acceptance calls. The final independent reuse round used the existing connector without rebuilding it.

Muse also reported a default Python User-Agent being rejected with Cloudflare error 1010 and incomplete urllib reads. Its final client used a project User-Agent and its existing requests library. These are observations from the Muse environment, not a diagnosis of every possible client. Cloudflare security settings were not weakened. The local standard MCP SDK client also passed independently; do not infer unrestricted client compatibility from either result.

The custom connector runs in Muse's account workspace under `~/workspace/custom-connectors/custom.miseport-demo/`, with `CONNECTOR.md`, `connector.yaml`, MCP client and REST fallback client. `muse.connector_search` returned that exact path in both discovery checks. The no-auth setup used the supported template manually because the setup helper expected registered credentials; no dummy credential was created. This workflow does not demonstrate a native platform-wide MCP registration or directory listing.

For another account, ask Muse to create its own Custom Connector from the [connection guide](https://miseport.pages.dev/docs/) and discover actual tool schemas before calling. Only send sample queries. No private merchant data, live orders, payments, unrelated connectors or scheduled tasks were part of this acceptance.
