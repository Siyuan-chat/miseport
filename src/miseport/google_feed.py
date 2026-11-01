"""Google Merchant Center CSV *local export* from reviewed MisePort Catalog.

Japan/JPY base fields only. Never uploads or authenticates with Google.
No partial feeds: one invalid product rejects the whole snapshot before write.
Official rules still depend on landing-page, account, policies and category.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path

from .core import Catalog, Stock
from .discovery import DiscoveryProfile, _https, _profile_from_file
from .importers import load_catalog
from .feed_common import FeedExportError, atomic_bytes, verified_enrichments

GOOGLE_SPEC_URL = "https://support.google.com/merchants/answer/7052112"
GOOGLE_COLUMNS = (
    "id", "title", "description", "link", "image_link", "availability",
    "price", "brand",
)


def inspect_google(catalog: Catalog, profile: DiscoveryProfile | None) -> dict:
    """Check EVERY product before mapping a complete Japan JPY base CSV."""
    extra = verified_enrichments(catalog, profile)
    rows, issues = [], []
    for p in catalog.products:
        entry = extra.get(p.sku)
        brand = entry.brand if entry and entry.brand_verified else None
        errors = []
        if not p.merchant_name or not p.merchant_homepage:
            errors.append("merchant_identity_missing")
        if len(p.sku) > 50:
            errors.append("id_over_50")
        if not p.name or len(p.name) > 150:
            errors.append("title_missing_or_over_150")
        if not p.description or len(p.description) > 5000:
            errors.append("description_missing_or_over_5000")
        if not _https(p.source_url):
            errors.append("link_https_required")
        if not _https(p.image_url):
            errors.append("image_link_https_required")
        if p.stock == Stock.unknown:
            errors.append("google_requires_known_availability")
        if p.price_jpy <= 0:
            errors.append("positive_price_required")
        if p.tax_included is not True:
            errors.append("japan_tax_included_price_unconfirmed")
        # Conservative default for new products. Unknown brand cannot be
        # replaced by shop name, "generic", or a fabricated identity.
        if not brand or len(brand) > 70:
            errors.append("verified_brand_missing_or_over_70")
        if p.is_demo:
            errors.append("demo_product_not_for_submission")
        if errors:
            issues.append({"sku": p.sku, "codes": errors})
        else:
            rows.append({
                "id": p.sku, "title": p.name, "description": p.description,
                "link": p.source_url, "image_link": p.image_url,
                "availability": p.stock.value,
                "price": str(p.price_jpy) + " JPY", "brand": brand,
            })
    return {
        "schema_version": "miseport-google-feed-export/1.0",
        "channel": "google_merchant_center",
        "target_country": "JP",
        "currency": "JPY",
        "source_spec": GOOGLE_SPEC_URL,
        "validation_scope": "local_minimum_fields_only",
        "catalog_count": len(catalog.products),
        "eligible_rows": len(rows),
        "blocked_rows": len(issues),
        "issues": issues,
        "rows": rows,
        "submitted": False, "accepted": None,
        "indexed": None, "agent_discovery_verified": False,
        "platform_policy_verified": False,
    }


def google_csv(report: dict) -> bytes:
    """Create a complete snapshot; no synthetic-data bypass exists."""
    if report["blocked_rows"]:
        raise FeedExportError("Google feed blocked; inspect report SKU/field issue codes")
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(GOOGLE_COLUMNS),
                            lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(report["rows"])
    return stream.getvalue().encode("utf-8")


def main():
    parser = argparse.ArgumentParser(prog="miseport-export-google",
        description="Local JP Google Merchant CSV; no upload or approval claim")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", help="optional JSON diagnostics (no raw product facts)")
    args = parser.parse_args()
    try:
        catalog = load_catalog(args.catalog)
        report = inspect_google(catalog, _profile_from_file(args.profile))
        if args.report:
            from .eval import write_report
            write_report(args.report, {
                k: v for k, v in report.items() if k != "rows"
            } | {"input_sha256": {
                "catalog": sha256(Path(args.catalog).read_bytes()).hexdigest(),
                "profile": sha256(Path(args.profile).read_bytes()).hexdigest(),
            }})
        content = google_csv(report)
        atomic_bytes(args.output, content)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"channel": "google_merchant_center",
                      "exported": report["eligible_rows"], "submitted": False}))


if __name__ == "__main__":
    main()
