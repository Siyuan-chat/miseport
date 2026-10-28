import json
from pathlib import Path
import subprocess
import sys

import pytest
from miseport.core import Catalog, Product
from miseport.importers import CatalogError, load_catalog, save_catalog

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples/products.json"


@pytest.fixture
def row():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))[0]


def test_adapter_equivalence_and_roundtrip(tmp_path):
    source = load_catalog(SAMPLE)
    csv = load_catalog(ROOT / "examples/products.csv")
    assert source.search() == csv.search()
    output = tmp_path / "catalog.json"
    save_catalog(csv, output)
    assert load_catalog(output).search() == source.search()


@pytest.mark.parametrize("change", [
    {"price_jpy": None}, {"price_jpy": -1}, {"price_jpy": 1.5}, {"price_jpy": True},
    {"source_url": "javascript:alert(1)"}, {"source_url": "https://u:p@example.com"},
    {"source_url": "https://example.com:bad"}, {"currency": "USD"},
    {"updated_at": "2026-10-28T12:00:00"}, {"is_demo": "false"},
    {"stock": "available"}, {"shipping_jpy": -1}, {"name": " "}, {"invented": 1},
])
def test_reject_invalid_rows(tmp_path, row, change):
    row.update(change)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([row]), encoding="utf-8")
    with pytest.raises(CatalogError, match="row 1"):
        load_catalog(path)


def test_required_price_and_duplicate(tmp_path, row):
    with pytest.raises(ValueError, match="duplicate SKU"):
        Catalog([Product(**row), Product(**row)])
    del row["price_jpy"]
    with pytest.raises(ValueError):
        Product(**row)


def test_unknown_stock_and_costs(row):
    row.pop("stock")
    row.pop("tax_included")
    row.pop("shipping_jpy")
    catalog = Catalog([Product(**row)])
    result = catalog.detail(row["sku"])["product"]
    assert result["stock"] == "unknown"
    assert result["tax_included"] is None and result["shipping_jpy"] is None
    assert catalog.search(in_stock_only=True)["total"] == 0


def test_filters_japanese_normalization_and_pagination():
    catalog = load_catalog(SAMPLE)
    assert catalog.search("ｺｰﾋｰ")["total"] == 2
    assert catalog.search("こーひー 豆")["total"] == 1
    assert catalog.search(category="食品", min_price_jpy=1500)["products"][0]["sku"] == "tea-002"
    assert catalog.search(in_stock_only=True)["total"] == 2
    assert catalog.search(max_price_jpy=1480)["total"] == 1
    assert catalog.search("存在しない")["products"] == []
    assert catalog.detail("missing") == {"found": False, "product": None}
    assert catalog.search(limit=1, offset=1)["products"][0]["sku"] == "cup-003"


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": 101}, {"offset": -1},
    {"min_price_jpy": -1}, {"min_price_jpy": 5, "max_price_jpy": 4}, {"query": "x" * 501},
    {"limit": True}, {"offset": 1.5}])
def test_bad_filters(kwargs):
    with pytest.raises(ValueError):
        load_catalog(SAMPLE).search(**kwargs)


@pytest.mark.parametrize("filename,text", [
    ("a.json", "{"), ("a.json", "{}"), ("a.csv", "sku,sku\na,a\n"),
    ("a.csv", "sku,name\na,b,c\n"), ("a.csv", "sku,name\na\n"), ("a.txt", "[]")])
def test_bad_files(tmp_path, filename, text):
    path = tmp_path / filename
    path.write_text(text, encoding="utf-8")
    with pytest.raises(CatalogError):
        load_catalog(path)


def test_missing_and_size_limit(tmp_path):
    with pytest.raises(CatalogError):
        load_catalog(tmp_path / "missing.json")
    path = tmp_path / "large.json"
    path.write_bytes(b" " * (10 * 1024 * 1024 + 1))
    with pytest.raises(CatalogError, match="10 MiB"):
        load_catalog(path)


def test_deep_json_and_duplicate_fields(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[" * 10000 + "]" * 10000, encoding="utf-8")
    # Some Python JSON decoders parse deeply without recursion; the row must
    # still be rejected as a catalog error rather than escape with traceback.
    with pytest.raises(CatalogError):
        load_catalog(path)
    path.write_text('[{"sku":"a","sku":"b"}]', encoding="utf-8")
    with pytest.raises(CatalogError, match="duplicate JSON field"):
        load_catalog(path)


def test_cli_vertical_chain_and_atomic_failure(tmp_path):
    output = tmp_path / "catalog.json"
    def run(*args):
        return subprocess.run([sys.executable, "-m", "miseport.cli", *map(str, args)],
                              capture_output=True, encoding="utf-8", timeout=15)
    result = run("import", ROOT / "examples/products.csv", "--output", output)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["count"] == 4
    result = run("search", "コーヒー", "--catalog", output, "--in-stock-only")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["products"][0]["sku"] == "coffee-001"
    result = run("detail", "tea-002", "--catalog", output)
    assert json.loads(result.stdout)["product"]["stock"] == "unknown"
    before = output.read_bytes()
    bad = tmp_path / "bad.json"
    bad.write_text('[{}]', encoding="utf-8")
    result = run("import", bad, "--output", output)
    assert result.returncode == 2 and "error" in json.loads(result.stderr)
    assert not result.stdout and output.read_bytes() == before
