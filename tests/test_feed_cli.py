"""Black-box CLI smoke tests use temporary fictional records only.

Test records are in a disposable temp directory, not real merchant products.
"""
import csv
import gzip
import json
from pathlib import Path
import subprocess
import sys


def _inputs(tmp_path):
    catalog = tmp_path / "synthetic-test.json"
    catalog.write_text(json.dumps([{
        "sku": "00001", "name": "架空のほうじ茶 80g",
        "description": "試験用商品の説明。実際の販売はありません。",
        "price_jpy": 1800, "stock": "in_stock",
        "image_url": "https://shop.example.org/assets/tea.png",
        "source_url": "https://shop.example.org/items/1",
        "updated_at": "2026-10-30T10:00:00+09:00",
        "is_demo": False,  # Proves CLI structure only; record is fictional.
        "tax_included": True, "merchant_id": "test-shop",
        "merchant_name": "架空商店",
        "merchant_homepage": "https://shop.example.org",
    }], ensure_ascii=False), encoding="utf-8")
    profile = tmp_path / "discovery.json"
    profile.write_text(json.dumps({
        "schema_version": "miseport-discovery/1.0",
        "merchant_id": "test-shop",
        "products": [{"sku": "00001", "brand": "架空ブランド",
                      "brand_verified": True}],
    }, ensure_ascii=False), encoding="utf-8")
    return catalog, profile


def _run(module, *args):
    return subprocess.run([sys.executable, "-m", module, *map(str, args)],
                          capture_output=True, text=True, timeout=15)


def test_two_real_clis_generate_complete_local_files(tmp_path):
    catalog, profile = _inputs(tmp_path)
    google = tmp_path / "google.csv"
    openai = tmp_path / "products.preview.jsonl.gz"
    g = _run("miseport.google_feed", "--catalog", catalog, "--profile", profile,
             "--output", google)
    assert g.returncode == 0, g.stderr
    rows = list(csv.DictReader(google.open(encoding="utf-8", newline="")))
    assert len(rows) == 1 and rows[0]["id"] == "00001"
    assert rows[0]["price"] == "1800 JPY"
    o = _run("miseport.openai_feed", "--catalog", catalog, "--profile", profile,
             "--output", openai)
    assert o.returncode == 0, o.stderr
    result = json.loads(gzip.decompress(openai.read_bytes()).decode().strip())
    assert result["item_id"] == "00001"
    assert result["price"] == "1800 JPY"


def test_openai_cli_refuses_non_preview_output_filename(tmp_path):
    cat, prof = _inputs(tmp_path)
    result = _run("miseport.openai_feed", "--catalog", cat, "--profile", prof,
                  "--output", tmp_path / "submission.jsonl.gz")
    assert result.returncode != 0
    assert not (tmp_path / "submission.jsonl.gz").exists()
