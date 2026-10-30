"""Deterministic, offline comparison of reviewed source and published catalogs.

Checks identity, individual product facts, removals and optional snapshot age.
This does not authenticate the platform, visit product URLs or infer SEO impact.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from .importers import load_catalog

FACTS = (
    "merchant_id", "merchant_name", "merchant_homepage",
    "name", "description", "category", "price_jpy", "currency",
    "tax_included", "shipping_jpy", "stock", "stock_quantity",
    "source_url", "evidence_url", "image_url", "gift_wrapping",
    "origin_prefecture", "caffeine_level", "is_demo", "updated_at",
)


def _identity(catalog):
    identities = {(p.merchant_id, p.merchant_name, p.merchant_homepage)
                  for p in catalog.products}
    if len(identities) != 1:
        return None
    identity = next(iter(identities))
    return identity if all(identity) else None


def _snapshot(catalog):
    values = [p.snapshot_at for p in catalog.products if p.snapshot_at is not None]
    if not values or len(values) != len(catalog.products):
        return None
    return min(values)


def compare_catalogs(source, published, *, as_of=None, max_age_hours=None):
    """Compare two fully validated catalogs; caller identifies source authority."""
    if (max_age_hours is not None and
            (type(max_age_hours) not in (float, int) or max_age_hours <= 0
             or as_of is None)):
        raise ValueError("positive max_age_hours requires explicit as_of")
    if as_of is not None and (not isinstance(as_of, datetime)
                              or as_of.tzinfo is None or as_of.utcoffset() is None):
        raise ValueError("as_of must have a timezone")
    source_id, published_id = _identity(source), _identity(published)
    issues = []
    if source_id is None or published_id is None:
        issues.append({"code": "MERCHANT_IDENTITY_UNVERIFIED", "sku": None})
    elif source_id != published_id:
        issues.append({"code": "MERCHANT_IDENTITY_MISMATCH", "sku": None})
    a = set(source.by_sku)
    b = set(published.by_sku)
    for sku in sorted(a - b):
        issues.append({"code": "MISSING_PUBLISHED_SKU", "sku": sku})
    for sku in sorted(b - a):
        issues.append({"code": "UNEXPECTED_PUBLISHED_SKU", "sku": sku})
    for sku in sorted(a & b):
        original, outgoing = source.by_sku[sku], published.by_sku[sku]
        mismatched = [field for field in FACTS
            if getattr(original, field) != getattr(outgoing, field)]
        if mismatched:
            issues.append({"code": "PRODUCT_FACT_MISMATCH", "sku": sku,
                           "fields": mismatched})
    if not a:
        issues.append({"code": "EMPTY_SOURCE_CATALOG", "sku": None})
    source_snapshot, target_snapshot = _snapshot(source), _snapshot(published)
    if source_snapshot is not None and target_snapshot is not None:
        if target_snapshot < source_snapshot:
            issues.append({"code": "PUBLISHED_SNAPSHOT_OLDER_THAN_SOURCE", "sku": None})
        if target_snapshot > source_snapshot:
            issues.append({"code": "PUBLISHED_SNAPSHOT_NEWER_THAN_SOURCE", "sku": None})
    elif source_snapshot is None or target_snapshot is None:
        issues.append({"code": "SNAPSHOT_TIMESTAMP_INCOMPLETE", "sku": None})
    if max_age_hours is not None and target_snapshot is not None:
        hours = (as_of - target_snapshot).total_seconds() / 3600
        if hours < 0:
            issues.append({"code": "PUBLISHED_SNAPSHOT_FROM_FUTURE", "sku": None})
        elif hours > max_age_hours:
            issues.append({"code": "PUBLISHED_SNAPSHOT_STALE", "sku": None})
    return {
        "schema_version": "miseport-catalog-comparison/1.0",
        "comparison_type": "offline_local_snapshots",
        "source_authenticity_verified": False,
        "web_pages_verified": False,
        "agent_discovery_verified": False,
        "source_product_count": len(a),
        "published_product_count": len(b),
        "source_snapshot_at": (source_snapshot.isoformat()
                               if source_snapshot else None),
        "published_snapshot_at": (target_snapshot.isoformat()
                                  if target_snapshot else None),
        "as_of": as_of.isoformat() if as_of is not None else None,
        "max_age_hours": max_age_hours,
        "issue_count": len(issues),
        "ready_for_review": not issues,
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(prog="miseport-compare-catalogs")
    parser.add_argument("--source", required=True,
                        help="Merchant-reviewed reference catalog (not auto-authenticated)")
    parser.add_argument("--published", required=True,
                        help="Published/export candidate canonical catalog")
    parser.add_argument("--as-of", help="Explicit ISO timestamp for freshness checks")
    parser.add_argument("--max-age-hours", type=float)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        moment = datetime.fromisoformat(args.as_of.replace("Z", "+00:00")) if args.as_of else None
        result = compare_catalogs(load_catalog(args.source), load_catalog(args.published),
                                  as_of=moment, max_age_hours=args.max_age_hours)
        result["input_sha256"] = {
            "source": sha256(Path(args.source).read_bytes()).hexdigest(),
            "published": sha256(Path(args.published).read_bytes()).hexdigest(),
        }
        # Use the project's existing atomic JSON artifact writer.
        from .eval import write_report
        write_report(args.output, result)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"issue_count": result["issue_count"],
                      "ready_for_review": result["ready_for_review"]}))
    if not result["ready_for_review"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
