"""Discovery readiness checks: deterministic, synthetic, and no platform claims."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from miseport.discovery import DiscoveryProfile, assess_discovery
from miseport.importers import load_catalog

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/demo-store.reference.json"


def test_channels_are_only_offline_preflight_and_never_false_eligibility():
    report = assess_discovery(load_catalog(FIXTURE))
    assert report["catalog_product_count"] == 2
    assert report["demo_only"] is True
    assert report["agent_discovery_verified"] is False
    assert report["channel_submission_performed"] is False
    assert report["platform_eligibility_verified"] is False
    assert report["channel_counts"]["google_merchant_feed_preflight"]["needs_data"] == 2
    row = report["products"][0]
    assert row["sku"] == "tea-001"
    assert "image_url_missing_or_invalid" in row["channels"]["google_merchant_feed_preflight"]["blocking_codes"]
    assert "merchant_verified_brand_missing" in row["channels"]["openai_stable_feed_preflight"]["blocking_codes"]
    assert row["channels"]["openai_stable_feed_preflight"]["indexed"] is None


def test_openai_unknown_stock_is_allowed_but_google_blocks_it():
    report = assess_discovery(load_catalog(FIXTURE))
    matcha = report["products"][1]["channels"]
    assert "availability_unknown" in matcha["google_merchant_feed_preflight"]["blocking_codes"]
    assert "availability_unknown" not in matcha["openai_stable_feed_preflight"]["blocking_codes"]


def test_brand_must_be_explicitly_confirmed_and_shop_bound():
    catalog = load_catalog(FIXTURE)
    base = {"schema_version": "miseport-discovery/1.0", "merchant_id": "demo-kyoto-tea",
            "products": [{"sku": "tea-001", "brand": "架空ブランド", "brand_verified": True}]}
    profile = DiscoveryProfile.model_validate(base)
    report = assess_discovery(catalog, profile)
    first = report["products"][0]
    assert first["verified_brand_present"] is True
    assert "merchant_verified_brand_missing" not in first["channels"]["openai_stable_feed_preflight"]["blocking_codes"]
    base["merchant_id"] = "other-shop"
    with pytest.raises(ValueError, match="different merchant"):
        assess_discovery(catalog, DiscoveryProfile.model_validate(base))


def test_unverified_brand_does_not_count_and_unknown_sku_is_rejected():
    catalog = load_catalog(FIXTURE)
    raw = {"schema_version": "miseport-discovery/1.0", "merchant_id": "demo-kyoto-tea",
           "products": [{"sku": "tea-001", "brand": "Unconfirmed", "brand_verified": False}]}
    assert assess_discovery(catalog, DiscoveryProfile.model_validate(raw))["products"][0]["verified_brand_present"] is False
    raw["products"][0]["sku"] = "missing"
    with pytest.raises(ValueError, match="unrecognized"):
        assess_discovery(catalog, DiscoveryProfile.model_validate(raw))


def test_schema_rejects_duplicates_unknown_fields_and_false_brand_attestations():
    data = {"schema_version": "miseport-discovery/1.0", "merchant_id": "shop",
            "products": [{"sku": "x", "brand": "X"}, {"sku": "x", "brand": "X"}]}
    with pytest.raises(ValidationError):
        DiscoveryProfile.model_validate(data)
    data["products"] = [{"sku": "x", "brand_verified": True}]
    with pytest.raises(ValidationError):
        DiscoveryProfile.model_validate(data)
    data["products"] = [{"sku": "x", "not_real": "field"}]
    with pytest.raises(ValidationError):
        DiscoveryProfile.model_validate(data)
    schema = DiscoveryProfile.model_json_schema()
    assert schema["properties"]["schema_version"] and schema["$defs"]["ProductEnrichment"]



def test_checked_in_discovery_profile_json_schema_matches_pydantic():
    expected = DiscoveryProfile.model_json_schema()
    actual = json.loads((Path(__file__).resolve().parents[1]
        / "examples/discovery-profile.schema.json").read_text(encoding="utf-8"))
    assert actual == expected
