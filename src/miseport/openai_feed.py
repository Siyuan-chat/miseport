"""OpenAI Stable product-feed JSONL.gz *preview*, never a partner upload.

The stable file-upload format currently targets the US by default. Japanese
JPY storefronts require explicit OpenAI partner/market approval not provided
by this software. The output suffix is deliberately .preview.jsonl.gz.
"""
from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path

from .core import Catalog
from .discovery import DiscoveryProfile, _https, _profile_from_file
from .feed_common import FeedExportError, atomic_bytes, verified_enrichments
from .importers import load_catalog

OPENAI_STABLE_SPEC = "https://developers.openai.com/commerce/specs/file-upload/products"
OPENAI_MARKET_SPEC = "https://developers.openai.com/commerce/specs/file-upload/overview"
REQUIRED_FIELDS = (
    "item_id", "title", "description", "url", "brand", "seller_name",
    "image_url", "availability", "price",
)


def inspect_openai(catalog: Catalog, profile: DiscoveryProfile | None) -> dict:
    """Validate the nine stable discovery fields without guessing attributes."""
    extensions = verified_enrichments(catalog, profile)
    rows, problems = [], []
    for product in catalog.products:
        enrichment = extensions.get(product.sku)
        brand = enrichment.brand if enrichment and enrichment.brand_verified else None
        missing = []
        if not product.sku:
            missing.append("item_id_missing")
        if not product.name or len(product.name) > 150:
            missing.append("title_missing_or_over_150")
        if not product.description or len(product.description) > 5000:
            missing.append("description_missing_or_over_5000")
        if not _https(product.source_url):
            missing.append("product_url_https_required")
        if not brand:
            missing.append("merchant_verified_brand_missing")
        if not product.merchant_name:
            missing.append("seller_name_missing")
        if not _https(product.image_url):
            missing.append("image_url_https_required")
        if product.price_jpy <= 0:
            missing.append("positive_price_required")
        # Unlike Google, the Stable OpenAI specification accepts "unknown".
        if product.stock.value not in (
                "in_stock", "out_of_stock", "unknown"):
            missing.append("invalid_availability")
        if missing:
            problems.append({"sku": product.sku, "codes": missing})
        else:
            row = {
                "item_id": product.sku, "title": product.name,
                "description": product.description, "url": product.source_url,
                "brand": brand, "seller_name": product.merchant_name,
                "image_url": product.image_url,
                "availability": product.stock.value,
                "price": str(product.price_jpy) + " JPY",
            }
            assert set(row) == set(REQUIRED_FIELDS)
            rows.append(row)
    return {
        "schema_version": "miseport-openai-feed-preview/1.0",
        "channel": "openai_stable_product_discovery",
        "schema_status": "stable_file_upload_fields",
        "output_status": "local_preview_only",
        "market": "JP",
        "market_approved": False,
        "partner_approved": False,
        "default_upload_market": "US",
        "catalog_count": len(catalog.products),
        "preview_rows": len(rows),
        "blocked_rows": len(problems),
        "issues": problems,
        "contains_synthetic": any(p.is_demo for p in catalog.products),
        "source_spec": OPENAI_STABLE_SPEC,
        "market_spec": OPENAI_MARKET_SPEC,
        "submitted": False, "accepted": None, "indexed": None,
        "agent_discovery_verified": False,
        "rows": rows,
    }


def openai_preview_gzip(report: dict) -> bytes:
    """Generate deterministic UTF-8 JSONL gzip; fail for any missing fields."""
    if report["blocked_rows"] or report["catalog_count"] != len(report["rows"]):
        raise FeedExportError("OpenAI preview blocked; inspect SKU/field diagnostics")
    if report["output_status"] != "local_preview_only":
        raise FeedExportError("only local previews are supported")
    ordered = sorted(report["rows"], key=lambda row: row["item_id"])
    lines = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")) + "\n" for row in ordered)
    # gzip header mtime=0 for reproducible byte-level comparisons.
    return gzip.compress(lines.encode("utf-8"), mtime=0)


def main():
    parser = argparse.ArgumentParser(
        prog="miseport-export-openai-preview",
        description="OpenAI Stable Schema preview, NOT a JP market/partner submission")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", required=True,
                        help="must end in .preview.jsonl.gz")
    parser.add_argument("--report", help="optional diagnostics JSON")
    args = parser.parse_args()
    if not args.output.endswith(".preview.jsonl.gz"):
        parser.error("output MUST end in .preview.jsonl.gz; not an authorized OpenAI upload")
    try:
        report = inspect_openai(
            load_catalog(args.catalog), _profile_from_file(args.profile))
        if args.report:
            from .eval import write_report
            write_report(args.report, {
                k: v for k, v in report.items() if k != "rows"
            } | {"input_sha256": {
                "catalog": sha256(Path(args.catalog).read_bytes()).hexdigest(),
                "profile": sha256(Path(args.profile).read_bytes()).hexdigest(),
            }})
        result = openai_preview_gzip(report)
        atomic_bytes(args.output, result)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"preview_rows": report["preview_rows"],
                      "output_status": "local_preview_only",
                      "market_approved": False, "submitted": False}))


if __name__ == "__main__":
    main()
