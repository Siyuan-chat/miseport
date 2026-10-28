# Catalog contract

JSON input is an array of products. CSV uses the same field names in a unique header row and UTF-8 (BOM accepted). Import validates every row before replacing the output atomically; a failed import preserves an existing output. Duplicate SKUs and duplicate JSON object keys are errors. Unknown fields are rejected.

Recovered version-1.0 merchant objects are also accepted through `miseport.legacy.LegacyAdapter`. Their import output uses a `miseport/1.1` envelope with validated metadata and products. This retains merchant/demo/snapshot information even for an empty catalog. Unknown object schema versions are rejected. For ordinary array/CSV input, output remains an array.

| Field | Required | Meaning |
|---|---|---|
| `sku` | yes | Nonempty case-sensitive merchant ID, at most 128 characters |
| `name` | yes | Nonempty name, at most 500 characters |
| `description` | no | Text, default empty, at most 10000 characters |
| `category` | no | Category string, default empty, at most 200 characters |
| `price_jpy` | yes | Nonnegative integer JPY; no string/float/bool coercion in JSON |
| `currency` | no | Must be `JPY`; defaults to `JPY` |
| `stock` | no | `in_stock`, `out_of_stock`, `unknown`; missing means unknown |
| `source_url` | yes | Absolute HTTP(S) URL, no credentials or whitespace; never fetched by server |
| `updated_at` | yes | ISO 8601 datetime with timezone |
| `is_demo` | yes | Explicit boolean; no automatic inference from URL/name |
| `tax_included` | no | Boolean or null (unknown) |
| `shipping_jpy` | no | Nonnegative integer or null (unknown); 0 explicitly means zero |
| `stock_quantity` | no | Nonnegative integer or null; if provided, 0 requires out_of_stock and positive requires in_stock |
| `merchant_id`, `merchant_name`, `merchant_homepage` | no | Merchant identity and validated HTTP(S) homepage, or null |
| `evidence_url`, `image_url` | no | Separate validated HTTP(S) references, or null; no URL fetched |
| `gift_wrapping` | no | Boolean or null, preserving uncertainty |
| `origin_prefecture`, `caffeine_level` | no | Supplied text or null; no product claims inferred |
| `snapshot_at` | no | Timezone-aware catalog snapshot timestamp, or null |

CSV integer cells contain ASCII digits only. Boolean cells accept `true`/`false` case-insensitively. Blank optional tax/shipping cells mean null; blank stock means unknown. Missing required columns/cells are errors. Do not include explanatory currency signs in price cells.

Expanded optional numeric/boolean/text fields also accept blank CSV cells as null. `evidence_url` is not silently filled from `source_url`; the audit reports missing evidence. The legacy adapter verifies merchant IDs, rejects contradictory metadata and preserves separate product/evidence URLs and stock quantities. Saving inconsistent canonical metadata fails before replacing an existing file.

`examples/product.schema.json` is generated from the product model. Runtime checks additionally enforce timezone-aware timestamps and the source URL rules. JSON numeric timestamps should not be used. Catalog limits: 10 MiB and 10000 rows. Empty catalogs are valid and return empty search results. Search matches normalized substrings in name/description/category/SKU, with AND semantics for whitespace-separated terms; category is an exact normalized match. Kana normalization covers standard katakana/hiragana; it does not infer synonyms or romanized forms. The core does not infer tax, shipping, freshness or purchasability. Search/detail responses preserve all product fields.

The MCP server loads a consistent snapshot at startup and has no write or refresh tool. Restart after changing the catalog. Treat source text and URLs as untrusted content. The merchant source page is the purchase destination; the server does not reserve stock or create orders.
