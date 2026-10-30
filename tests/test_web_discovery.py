"""Web discovery audit: no live merchant network requests in tests."""
import json
from pathlib import Path

import pytest

from miseport.importers import load_catalog
from miseport.public_url_probe import PageEvidence
from miseport.web_discovery import audit_offline, audit_live, audit_web_pages, WebAuditError

CAT = Path(__file__).resolve().parents[1] / "tests/fixtures/demo-store.reference.json"
URL = "https://example.org/products/tea-001"


def catalog():
    return load_catalog(CAT)


def html(*, canonical=URL, price="1850", available="InStock", noindex=False):
    return (
        '<html><head><link rel="canonical" href="' + canonical + '">'
        + ('<meta name="robots" content="noindex, nofollow">' if noindex else '')
        + '<script type="application/ld+json">'
        + json.dumps({"@context": "https://schema.org", "@type": "Product",
            "sku": "tea-001", "name": "京都産ほうじ茶 ギフト 80g", "url": URL,
            "offers": {"@type": "Offer", "price": price, "priceCurrency": "JPY",
                       "availability": "https://schema.org/" + available}})
        + '</script></head><body>架空商品（テスト）</body></html>'
    ).encode("utf-8")


def page(body=None, status=200, x_robots_tag=None):
    return PageEvidence(status, "text/html; charset=utf-8",
                        html() if body is None else body, x_robots_tag=x_robots_tag)


def test_original_page_local_evidence_reports_observations_not_search_indexing():
    report = audit_web_pages(catalog(), {"tea-001": page()},
        robots_text="User-agent: *\nAllow: /\nSitemap: https://example.org/sitemap.xml\n",
        robots_http_status=200)
    row = report["products"][0]
    assert report["checked"] == 1 and report["with_issues"] == 0
    assert report["sitemap_advertised_in_robots"] is True
    assert row["canonical"] == row["jsonld_price"] == row["jsonld_availability"] == "matches"
    assert row["page_evidence_sufficient"] is True
    assert row["robots_allow"] == {"Googlebot": True, "OAI-SearchBot": True}
    assert row["indexed"] is None and row["search_visibility_observed"] is None
    assert report["agent_natural_discovery_verified"] is False


def test_robots_noindex_and_price_mismatch_remain_separate_issues():
    report = audit_web_pages(catalog(), {"tea-001": page(html(price="1851", noindex=True),
                        x_robots_tag="googlebot: noindex")},
        robots_text="User-agent: Googlebot\nDisallow: /products/\n"
                    "User-agent: OAI-SearchBot\nAllow: /\n")
    row = report["products"][0]
    assert row["jsonld_price"] == "mismatch"
    assert row["noindex_detected"] is True
    assert row["robots_allow"]["Googlebot"] is False
    assert row["robots_allow"]["OAI-SearchBot"] is True
    assert "googlebot_robots_disallow" in row["issues"]
    assert "jsonld_price_mismatch" in row["issues"]


def test_unknown_stock_is_not_implicitly_available():
    original = catalog()
    product = original.by_sku["tea-002"]
    body = ('<html><head><link rel="canonical" href="' + product.source_url
            + '"><script type="application/ld+json">'
            + json.dumps({"@type": "Product", "sku": "tea-002", "url": product.source_url,
                "offers": {"price": "3100", "priceCurrency": "JPY",
                           "availability": "https://schema.org/InStock"}})
            + '</script></head></html>').encode()
    row = audit_web_pages(original, {"tea-002": page(body)})["products"][0]
    assert row["jsonld_availability"] == "unknown_source_stock"
    assert row["robots_allow"]["OAI-SearchBot"] is None


def test_canonical_mismatch_and_redirect_are_not_positively_verified():
    not_me = page(html(canonical="https://example.org/products/other"))
    first = audit_web_pages(catalog(), {"tea-001": not_me})["products"][0]
    assert "canonical_mismatch" in first["issues"]
    second = audit_web_pages(catalog(), {"tea-001": PageEvidence(
        302, "text/html", b"", redirect_location="https://example.org/products/other")
    })["products"][0]
    assert "redirect_not_followed" in second["issues"]
    assert second["page_evidence_sufficient"] is False


def test_online_requires_merchant_approval_before_transport_call():
    invoked = []
    def fake(*args):
        invoked.append(args)
        return page()
    with pytest.raises(WebAuditError, match="approve"):
        audit_live(catalog(), transport=fake)
    assert invoked == []
    report = audit_live(catalog(), approved=True, max_products=1,
        transport=lambda url, timeout, maxlen: (
            PageEvidence(200, "text/plain", b"User-agent: *\nAllow: /\n")
            if url.endswith("/robots.txt") else page()))
    assert report["checked"] == 1
    assert report["robots_observed"] is True


def test_offline_manifest_uses_local_bounded_files_only(tmp_path):
    (tmp_path / "one.html").write_bytes(html())
    (tmp_path / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    manifest = {"schema_version": "miseport-web-evidence/1.0",
                "robots_file": "robots.txt", "items": [
                    {"sku": "tea-001", "filename": "one.html", "http_status": 200}]}
    (tmp_path / "pages.json").write_text(json.dumps(manifest), encoding="utf-8")
    report = audit_offline(catalog(), tmp_path / "pages.json")
    assert report["checked"] == 1 and report["with_issues"] == 0
    manifest["items"][0]["filename"] = "../private"
    (tmp_path / "pages.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(WebAuditError, match="basename"):
        audit_offline(catalog(), tmp_path / "pages.json")


def test_offline_rejects_unknown_or_duplicate_products_and_too_large_html(tmp_path):
    (tmp_path / "one.html").write_bytes(b"<html></html>")
    manifest = {"schema_version": "miseport-web-evidence/1.0",
        "items": [{"sku": "missing", "filename": "one.html", "http_status": 200}]}
    file = tmp_path / "manifest.json"
    file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(WebAuditError, match="absent"):
        audit_offline(catalog(), file)
    manifest["items"] = [
        {"sku": "tea-001", "filename": "one.html", "http_status": 200},
        {"sku": "tea-001", "filename": "one.html", "http_status": 200}]
    file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(WebAuditError, match="duplicate"):
        audit_offline(catalog(), file)
    (tmp_path / "one.html").write_bytes(b"x" * (128 * 1024 + 1))
    manifest["items"] = [manifest["items"][0]]
    file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(WebAuditError, match="size"):
        audit_offline(catalog(), file)
