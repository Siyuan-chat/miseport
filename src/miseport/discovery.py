"""Offline preflight for merchant-owned product discovery channels.

Readiness is only *local field completeness*, never platform admission,
indexing, a live store verification or AI recommendation evidence. Keep
channel-specific enrichment separate from the stable Product contract.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from .core import Catalog
from .importers import load_catalog


class ProductEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sku: str = Field(min_length=1, max_length=128)
    brand: str | None = Field(default=None, min_length=1, max_length=150)
    brand_verified: StrictBool = False

    @model_validator(mode="after")
    def brand_evidence(self):
        if self.brand_verified and not self.brand:
            raise ValueError("verified brand requires a nonempty brand")
        return self


class DiscoveryProfile(BaseModel):
    """Merchant-reviewed supplement; never silently substitute merchant name for brand."""
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["miseport-discovery/1.0"]
    merchant_id: str = Field(min_length=1, max_length=128)
    products: list[ProductEnrichment] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def no_duplicate_skus(self):
        keys = [p.sku for p in self.products]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate profile SKU")
        return self


CHANNELS = {
    "google_merchant_feed_preflight": "https://support.google.com/merchants/answer/7052112",
    "openai_stable_feed_preflight": "https://developers.openai.com/commerce/specs/file-upload/products",
}


def _https(url: str | None) -> bool:
    if not isinstance(url, str) or not url:
        return False
    try:
        parts = urlsplit(url)
        return (parts.scheme == "https" and parts.hostname is not None
                and parts.username is None and parts.password is None
                and parts.port in (None, 443) and not any(c.isspace() for c in url))
    except ValueError:
        return False


def _channel_row(product, brand):
    """Return conservative mapping diagnostics, not a feed accepted by a vendor."""
    common = {
        "sku": product.sku, "merchant_name": product.merchant_name,
        "source_url": product.source_url, "price_jpy": product.price_jpy,
        "stock": product.stock.value, "image_url": product.image_url,
        "brand": brand, "name": product.name, "description": product.description,
    }
    google = []
    if len(product.sku) > 50:
        google.append("id_exceeds_50_chars")
    if not product.name or len(product.name) > 150:
        google.append("title_missing_or_too_long")
    if not product.description or len(product.description) > 5000:
        google.append("description_missing_or_too_long")
    if not _https(product.source_url):
        google.append("product_https_url_required")
    if not _https(product.image_url):
        google.append("image_url_missing_or_invalid")
    if product.stock.value == "unknown":
        google.append("availability_unknown")
    # A passing field mapping cannot prove site/checkout policy compliance.
    openai = []
    if not product.sku:
        openai.append("item_id_missing")
    if not product.name or len(product.name) > 150:
        openai.append("title_missing_or_too_long")
    if not product.description or len(product.description) > 5000:
        openai.append("description_missing_or_too_long")
    if not _https(product.source_url):
        openai.append("product_https_url_required")
    if not brand:
        openai.append("merchant_verified_brand_missing")
    if not product.merchant_name:
        openai.append("seller_name_missing")
    if not _https(product.image_url):
        openai.append("image_url_missing_or_invalid")
    # OpenAI stable feed explicitly permits the string "unknown".
    result = {}
    for key, blockers in (("google_merchant_feed_preflight", google),
                          ("openai_stable_feed_preflight", openai)):
        result[key] = {"local_fields_complete": not blockers,
                       "blocking_codes": blockers,
                       "submitted": False, "accepted": None, "indexed": None,
                       "agent_discovery_observed": None}
    return common, result


def assess_discovery(catalog: Catalog, profile: DiscoveryProfile | None = None) -> dict:
    """Only compute local field readiness. Never infer vendor approval or crawling."""
    if not isinstance(catalog, Catalog):
        raise ValueError("expected a validated Catalog")
    products = catalog.products
    identities = {p.merchant_id for p in products}
    if profile is not None:
        if not isinstance(profile, DiscoveryProfile):
            raise ValueError("profile must have a validated discovery schema")
        if len(identities) != 1 or None in identities or profile.merchant_id not in identities:
            raise ValueError("discovery profile belongs to a different merchant")
        unknown = {p.sku for p in profile.products} - set(catalog.by_sku)
        if unknown:
            raise ValueError("profile contains unrecognized SKU")
    enrichment = {p.sku: p for p in profile.products} if profile else {}
    rows = []
    for p in products:
        extra = enrichment.get(p.sku)
        brand = extra.brand if extra and extra.brand_verified else None
        _, channels = _channel_row(p, brand)
        issues = []
        if p.is_demo:
            issues.append("synthetic_demo_product")
        if p.tax_included is None:
            issues.append("tax_treatment_unknown")
        if p.snapshot_at is None:
            issues.append("catalog_snapshot_unavailable")
        rows.append({"sku": p.sku, "is_demo": p.is_demo,
                     "verified_brand_present": brand is not None,
                     "warnings": issues, "channels": channels})
    counts = {}
    for channel in CHANNELS:
        counts[channel] = {
            "structurally_complete": sum(
                r["channels"][channel]["local_fields_complete"] for r in rows),
            "needs_data": sum(
                not r["channels"][channel]["local_fields_complete"] for r in rows),
        }
    return {
        "schema_version": "miseport-discovery-audit/1.0",
        "scope": "offline_channel_field_preflight_only",
        "merchant_data_sent": False,
        "original_pages_inspected": False,
        "channel_submission_performed": False,
        "platform_eligibility_verified": False,
        "agent_discovery_verified": False,
        "catalog_product_count": len(rows), "demo_only": all(p.is_demo for p in products),
        "channel_specifications": CHANNELS,
        "channel_counts": counts, "products": rows,
    }


def _profile_from_file(path):
    source = Path(path)
    if not source.is_file() or source.stat().st_size > 1024 * 1024:
        raise ValueError("profile missing or larger than 1 MiB")
    return DiscoveryProfile.model_validate_json(source.read_bytes())


def main():
    parser = argparse.ArgumentParser(prog="miseport-discovery-readiness")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--profile", help="Optional separately confirmed brand profile")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        report = assess_discovery(load_catalog(args.catalog),
                                  _profile_from_file(args.profile) if args.profile else None)
        report["input_sha256"] = {"catalog": sha256(Path(args.catalog).read_bytes()).hexdigest(),
            "profile": sha256(Path(args.profile).read_bytes()).hexdigest()
                       if args.profile else None}
        from .eval import write_report
        write_report(args.output, report)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"products": report["catalog_product_count"],
                      "channels": report["channel_counts"]}))
    # A diagnostics tool is successful if it generated the diagnostics,
    # even when a merchant has incomplete product data.


if __name__ == "__main__":
    main()
