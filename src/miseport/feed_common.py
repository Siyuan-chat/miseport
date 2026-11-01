"""Common local feed infrastructure; never publishes or contacts vendors.

The Google and OpenAI adapters share profile identity checks and atomic output
handling while retaining their own vendor-specific field validation.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from .core import Catalog
from .discovery import DiscoveryProfile


class FeedExportError(ValueError):
    """Safe validation error; avoid exposing merchant product data or secrets."""


def verified_enrichments(catalog: Catalog, profile: DiscoveryProfile | None) -> dict:
    """Reject cross-shop/unknown SKU enrichment before any feed is generated."""
    if not isinstance(catalog, Catalog) or not catalog.products:
        raise FeedExportError("nonempty validated catalog required")
    if not isinstance(profile, DiscoveryProfile):
        raise FeedExportError("shop-reviewed discovery profile required")
    if {product.merchant_id for product in catalog.products} != {profile.merchant_id}:
        raise FeedExportError("merchant identity mismatch")
    lookup = {item.sku: item for item in profile.products}
    if set(lookup) - set(catalog.by_sku):
        raise FeedExportError("profile contains unknown SKUs")
    return lookup


def atomic_bytes(output: str | Path, content: bytes) -> None:
    """Replace a complete local output only after validation succeeds."""
    dest = Path(output)
    if not dest.parent.is_dir() or dest.is_symlink():
        raise FeedExportError("output parent must exist, and output must not be a symlink")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="wb", dir=dest.parent, prefix=".miseport-feed-",
                suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, dest)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
