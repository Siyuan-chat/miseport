"""Independent verification of a merchant deployment package before upload."""
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import zipfile

import pytest

from miseport.bundle_probe import BundleVerificationError, inspect_merchant_zip
from miseport.core import Catalog, Product
from miseport.publisher import build_merchant_zip


def fixture_catalog():
    product = Product(
        sku="base-12", name="京都ほうじ茶", price_jpy=1850,
        stock="in_stock", stock_quantity=3, is_demo=True,
        merchant_id="shop", merchant_name="京都茶店",
        merchant_homepage="https://shop.example.org/",
        source_url="https://shop.example.org/items/12",
        updated_at="2026-10-29T00:00:00Z",
        snapshot_at=datetime(2026, 10, 29, tzinfo=timezone.utc),
        tax_included=True, shipping_jpy=None,
    )
    return Catalog([product])


def bundle(tmp_path):
    path = tmp_path / "merchant.zip"
    build_merchant_zip(fixture_catalog(), path, origin="https://shop.pages.dev",
                       merchant_approved=True, demo_mode=True)
    return path


def rewrite(path, changes):
    with zipfile.ZipFile(path, "r") as z:
        body = {n: z.read(n) for n in z.namelist()}
    body.update(changes)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, value in sorted(body.items()):
            z.writestr(name, value)


def test_exact_generated_bundle_passes(tmp_path):
    result = inspect_merchant_zip(bundle(tmp_path), expected_origin="https://shop.pages.dev")
    assert result["valid"] is True
    assert result["product_count"] == 1
    assert result["merchant_id"] == "shop"
    assert result["files_verified"] == 7
    assert result["read_only"] and result["demo_only"]


def test_expected_origin_mismatch_is_blocking(tmp_path):
    with pytest.raises(BundleVerificationError, match="ドメイン"):
        inspect_merchant_zip(bundle(tmp_path), expected_origin="https://other.pages.dev")


def test_tampered_worker_fails_even_with_updated_manifest_hash(tmp_path):
    path = bundle(tmp_path)
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read("manifest.json"))
        worker = z.read("_worker.js") + b"\n// malicious or stale build\n"
    for entry in manifest["files"]:
        if entry["path"] == "_worker.js":
            entry["sha256"] = sha256(worker).hexdigest()
            entry["size"] = len(worker)
    rewrite(path, {
        "_worker.js": worker,
        "manifest.json": json.dumps(manifest).encode(),
    })
    with pytest.raises(BundleVerificationError, match="Worker"):
        inspect_merchant_zip(path)


def test_catalog_changed_even_if_hash_updated_does_not_match_worker(tmp_path):
    path = bundle(tmp_path)
    with zipfile.ZipFile(path) as z:
        catalog = json.loads(z.read("catalog.json"))
        manifest = json.loads(z.read("manifest.json"))
    catalog["products"][0]["price_jpy"] = 10
    content = (json.dumps(catalog, ensure_ascii=False) + "\n").encode()
    for entry in manifest["files"]:
        if entry["path"] == "catalog.json":
            entry["size"] = len(content)
            entry["sha256"] = sha256(content).hexdigest()
    rewrite(path, {"catalog.json": content,
                   "manifest.json": json.dumps(manifest).encode()})
    with pytest.raises(BundleVerificationError, match="Worker"):
        inspect_merchant_zip(path)


def test_extra_internal_file_rejected(tmp_path):
    path = bundle(tmp_path)
    rewrite(path, {"PROJECT_STATUS.md": "INTERNAL RELEASE EXCLUDE".encode()})
    with pytest.raises(BundleVerificationError, match="構成"):
        inspect_merchant_zip(path)


def test_bad_zip_and_missing_file_rejected(tmp_path):
    path = tmp_path / "fake.zip"
    path.write_text("not a zip", encoding="utf-8")
    with pytest.raises(BundleVerificationError):
        inspect_merchant_zip(path)
    path.unlink()
    with pytest.raises(BundleVerificationError):
        inspect_merchant_zip(path)


def test_secrets_in_public_index_are_rejected(tmp_path):
    path = bundle(tmp_path)
    with zipfile.ZipFile(path) as z:
        html = z.read("index.html") + b"\napi_key=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    rewrite(path, {"index.html": html})
    with pytest.raises(BundleVerificationError, match="機密"):
        inspect_merchant_zip(path)


def test_changed_manifest_hash_fails(tmp_path):
    path = bundle(tmp_path)
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read("manifest.json"))
    manifest["files"][0]["sha256"] = "0" * 64
    rewrite(path, {"manifest.json": json.dumps(manifest).encode()})
    with pytest.raises(BundleVerificationError, match="ハッシュ"):
        inspect_merchant_zip(path)
