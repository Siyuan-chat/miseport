"""D5 disclosure and export boundaries, without Tk or real merchant network."""
from pathlib import Path
from miseport.discovery_gui import discovery_view
from miseport.discovery import DiscoveryProfile
from miseport.importers import load_catalog

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "tests/fixtures/demo-store.reference.json"


def test_discovery_dialog_model_requires_profile_before_export():
    model = discovery_view(load_catalog(CATALOG))
    assert model["scope"] == "local_readiness_only"
    assert model["product_count"] == 2 and not model["profile_loaded"]
    assert model["google_export_blocked"] is True
    assert model["openai_preview_blocked"] is True
    assert model["submitted"] is False
    assert model["indexed"] is None
    assert model["agent_discovered"] is None
    assert model["rows"][0]["google"] == "要確認"


def test_loaded_merchant_profile_does_not_override_missing_image_or_stock():
    profile = DiscoveryProfile.model_validate_json(
        (ROOT / "examples/discovery-profile.example.json").read_bytes())
    model = discovery_view(load_catalog(CATALOG), profile)
    assert model["profile_loaded"] is True
    assert model["google_export_blocked"] is True
    assert model["openai_preview_blocked"] is True
    a, b = model["rows"]
    assert a["sku"] == "tea-001" and b["sku"] == "tea-002"
    assert "image_link_https_required" in a["google_issues"]
    assert "image_url_https_required" in a["openai_issues"]
    assert "google_requires_known_availability" in b["google_issues"]


def test_gui_button_wiring_keeps_review_and_stale_guard():
    source = (ROOT / "src/miseport/gui.py").read_text(encoding="utf-8")
    assert 'discovery_btn = ttk.Button(output,' in source
    assert 'state="disabled")\n    discovery_btn.pack(' in source
    assert 'discovery_btn.configure(state="normal" if result.publishable else "disabled")' in source
    assert 'current_inputs == review_inputs() and imported_for_current_shop()' in source
    assert 'is_approved=lambda: consent.get()' in source
    assert 'discovery_disabled_until_review' in source
