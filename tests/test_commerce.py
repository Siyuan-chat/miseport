"""Commerce boundaries are snapshot facts, never binding checkout promises."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from miseport.core import Catalog, Product

ROOT = Path(__file__).resolve().parents[1]


def product(**changes):
    row = dict(sku="tea", name="お茶", price_jpy=1850, stock="in_stock",
               stock_quantity=12, source_url="https://example.org/tea",
               evidence_url="https://example.org/evidence", updated_at="2026-10-27T00:00:00+09:00",
               is_demo=True, tax_included=True, shipping_jpy=450,
               merchant_id="shop", merchant_name="茶店", merchant_homepage="https://example.org/",
               gift_wrapping=True, origin_prefecture="京都府", caffeine_level=None, image_url=None)
    row.update(changes)
    return Product(**row)


def test_quantity_quote_charges_shipping_once_and_flags_snapshot():
    catalog = Catalog([product()])
    quote = catalog.quote("tea", 3)
    assert quote["found"] and quote["product_id"] == "tea"
    assert quote["quantity"] == 3 and quote["currency"] == "JPY"
    assert quote["unit_price_jpy"] == 1850 and quote["subtotal_jpy"] == 5550
    assert quote["shipping_jpy"] == 450 and quote["total_jpy"] == 6000
    assert quote["tax_included"] is True and quote["can_fulfill_snapshot"] is True
    assert quote["stock_quantity"] == 12 and quote["stock"] == "in_stock"
    assert quote["is_binding"] is False and quote["stock_is_live"] is False
    assert quote["is_demo"] is True and quote["evidence_url"] == "https://example.org/evidence"
    assert quote["source_url"] == "https://example.org/tea" and quote["updated_at"]
    assert catalog.quote("tea", 13)["can_fulfill_snapshot"] is False


@pytest.mark.parametrize("tax,shipping", [(False, 450), (None, 450), (True, None), (None, None)])
def test_incomplete_costs_never_invent_total(tax, shipping):
    quote = Catalog([product(tax_included=tax, shipping_jpy=shipping)]).quote("tea", 2)
    assert quote["subtotal_jpy"] == 3700 and quote["total_jpy"] is None


@pytest.mark.parametrize("stock,quantity,expected", [
    ("unknown", None, None), ("in_stock", None, None), ("out_of_stock", 0, False),
    ("out_of_stock", None, False), ("in_stock", 1, True),
])
def test_inventory_and_fulfillment_keep_unknown_distinct(stock, quantity, expected):
    catalog = Catalog([product(stock=stock, stock_quantity=quantity)])
    inventory = catalog.inventory("tea")
    assert inventory["stock"] == stock and inventory["stock_quantity"] == quantity
    assert inventory["found"] and inventory["product_id"] == "tea"
    assert inventory["stock_is_live"] is False and inventory["is_demo"] is True
    assert inventory["source_url"] and inventory["evidence_url"] and inventory["updated_at"]
    assert catalog.quote("tea")["can_fulfill_snapshot"] is expected


@pytest.mark.parametrize("quantity", [True, False, 1.0, "1", 0, -1, 1001, None])
def test_quote_quantity_is_strict_and_bounded(quantity):
    with pytest.raises(ValueError):
        Catalog([product()]).quote("tea", quantity)


@pytest.mark.parametrize("change", [
    {"stock_quantity": True}, {"stock_quantity": 1.0}, {"stock_quantity": -1},
    {"stock_quantity": "2"}, {"stock_quantity": 0},
    {"stock": "out_of_stock", "stock_quantity": 1},
    {"stock": "unknown", "stock_quantity": 2},
    {"evidence_url": "javascript:alert(1)"}, {"merchant_homepage": "https://u:p@example.org"},
    {"image_url": "https://example.org:bad/image"}, {"gift_wrapping": "true"},
])
def test_new_metadata_rejects_unsafe_or_contradictory_values(change):
    with pytest.raises(ValueError):
        product(**change)


def test_missing_sku_and_audit_do_not_fill_evidence():
    catalog = Catalog([product(stock="unknown", stock_quantity=None, evidence_url=None,
                               merchant_id=None, tax_included=None, shipping_jpy=None)])
    assert catalog.inventory("missing") == {"found": False, "product_id": "missing"}
    assert catalog.quote("missing") == {"found": False, "product_id": "missing"}
    assert catalog.jsonld("missing") == {"found": False, "product_id": "missing", "jsonld": None}
    audit = catalog.audit()
    assert audit["product_count"] == 1 and audit["demo_product_count"] == 1
    assert audit["stock_is_live"] is False
    for field in ("stock", "evidence_url", "merchant_id", "tax_included", "shipping_jpy"):
        assert audit["missing_fields"][field] == ["tea"]
    assert catalog.detail("tea")["product"]["evidence_url"] is None


def test_jsonld_preserves_price_and_unknown_stock_without_reviews():
    catalog = Catalog([product(stock="unknown", stock_quantity=None)])
    result = catalog.jsonld("tea")
    assert result["found"]
    data = result["jsonld"]
    assert data["@type"] == "Product" and data["sku"] == "tea" and data["name"] == "お茶"
    assert data["url"] == "https://example.org/tea"
    assert data["offers"]["priceCurrency"] == "JPY" and data["offers"]["price"] == "1850"
    assert data["offers"]["url"] == "https://example.org/tea"
    assert "availability" not in data["offers"]
    assert "aggregateRating" not in data and "review" not in data
    properties = {item["name"]: item["value"] for item in data["additionalProperty"]}
    assert properties["evidence_url"] == "https://example.org/evidence"
    assert properties["updated_at"] and properties["is_demo"] is True


def test_structured_filters_and_original_positional_search_contract():
    catalog = Catalog([product(), product(sku="other", gift_wrapping=False, origin_prefecture="静岡県")])
    assert catalog.search(gift_wrapping=True)["products"][0]["sku"] == "tea"
    assert catalog.search(origin_prefecture="静岡県")["products"][0]["sku"] == "other"
    assert catalog.search("", None, None, None, False, 1, 0)["limit"] == 1


@pytest.mark.parametrize("command,arguments", [
    ("inventory", ["tea"]), ("quote", ["tea", "--quantity", "3"]),
    ("audit", []), ("export-jsonld", ["tea"]),
])
def test_cli_commerce_commands_use_selected_catalog(tmp_path, command, arguments):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps([product().model_dump(mode="json")]), encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "miseport.cli", command, *arguments,
                             "--catalog", str(path)], capture_output=True, encoding="utf-8", timeout=15)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    if command == "quote":
        assert data["total_jpy"] == 6000
    elif command == "audit":
        assert data["product_count"] == 1
    else:
        assert data["found"]


@pytest.mark.parametrize("quantity", ["0", "-1", "1001"])
def test_cli_quote_invalid_quantity_has_json_error_without_output(tmp_path, quantity):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps([product().model_dump(mode="json")]), encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "miseport.cli", "quote", "tea",
                             "--quantity", quantity, "--catalog", str(path)],
                            capture_output=True, encoding="utf-8", timeout=15)
    assert result.returncode == 2 and result.stdout == ""
    assert "quantity" in json.loads(result.stderr)["error"]


def test_cli_search_structured_flags_filter_selected_catalog(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps([product().model_dump(mode="json"),
                                product(sku="other", gift_wrapping=False).model_dump(mode="json")]),
                    encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "miseport.cli", "search", "",
                             "--gift-wrapping", "true", "--origin-prefecture", "京都府",
                             "--catalog", str(path)],
                            capture_output=True, encoding="utf-8", timeout=15)
    assert result.returncode == 0, result.stderr
    assert [p["sku"] for p in json.loads(result.stdout)["products"]] == ["tea"]
