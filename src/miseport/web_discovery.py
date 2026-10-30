"""Read-only, bounded discovery audit of ORIGINAL merchant product pages.

Default mode accepts an offline merchant-provided HTML snapshot. The opt-in
network mode uses the existing public-IP-pinned TLS transport. This tool does
not submit a feed, alter shops, verify platform indexing or score AI ranking.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
import json
import re
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser

from .base_urls import _store_origin, BaseURLValidationError
from .importers import load_catalog
from .public_url_probe import PageEvidence, _fetch_page, MAX_HTML_BYTES

MAX_PAGES = 10
MAX_ROBOTS_BYTES = 64 * 1024
_USER_AGENTS = ("Googlebot", "OAI-SearchBot")
_FILE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")


class WebAuditError(ValueError):
    """Only concise messages; never include website response bodies or secrets."""


class _Markers(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonicals = []
        self.robots = {}
        self.jsonld = []
        self._collect = False
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        data = {str(k).lower(): (v or "") for k, v in attrs}
        if tag.lower() == "link" and "canonical" in data.get("rel", "").lower().split():
            self.canonicals.append(data.get("href", "").strip())
        if tag.lower() == "meta":
            key = data.get("name", "").lower().strip()
            if key in ("robots", "googlebot", "oai-searchbot"):
                self.robots.setdefault(key, []).append(data.get("content", "").lower())
        if tag.lower() == "script" and data.get("type", "").lower().strip() == "application/ld+json":
            self._collect = True
            self._buffer = []

    def handle_data(self, data):
        if self._collect:
            self._buffer.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._collect:
            self.jsonld.append("".join(self._buffer))
            self._collect = False
            self._buffer = []


def _product_nodes(value):
    if isinstance(value, list):
        for node in value:
            yield from _product_nodes(node)
    elif isinstance(value, dict):
        kind = value.get("@type", "")
        kinds = kind if isinstance(kind, list) else [kind]
        if any(str(k).split("/")[-1].split(":")[-1] == "Product" for k in kinds):
            yield value
        if "@graph" in value:
            yield from _product_nodes(value["@graph"])


def _find_jsonld(marker, product):
    nodes = []
    for text in marker.jsonld[:16]:
        if len(text) > MAX_HTML_BYTES:
            continue
        try:
            nodes.extend(_product_nodes(json.loads(text)))
        except (ValueError, RecursionError, TypeError):
            continue
    if not nodes:
        return None, "not_present"
    matching = [p for p in nodes if
                (str(p.get("sku", "")) == product.sku or
                 p.get("url") == product.source_url)]
    if len(matching) != 1:
        return None, "ambiguous_or_unmatched"
    return matching[0], "matched"


def _offer_data(node):
    offers = node.get("offers")
    if isinstance(offers, list):
        if len(offers) != 1:
            return None
        offers = offers[0]
    return offers if isinstance(offers, dict) else None


def _price_state(offer, product):
    if offer is None or offer.get("price") is None or offer.get("priceCurrency") != "JPY":
        return "not_verifiable"
    raw = offer["price"]
    if type(raw) not in (int, float, str) or not str(raw).strip():
        return "invalid"
    try:
        amount = Decimal(str(raw))
        if not amount.is_finite():
            return "invalid"
    except (ValueError, InvalidOperation):
        return "invalid"
    return "matches" if amount == Decimal(product.price_jpy) else "mismatch"


def _availability_state(offer, product):
    if product.stock.value == "unknown":
        return "unknown_source_stock"
    if offer is None or "availability" not in offer:
        return "not_verifiable"
    end = str(offer["availability"]).rsplit("/", 1)[-1]
    expected = "InStock" if product.stock.value == "in_stock" else "OutOfStock"
    return "matches" if end == expected else "mismatch"


def _robots_states(text: str | None, url: str):
    if text is None:
        return {agent: None for agent in _USER_AGENTS}
    reader = RobotFileParser()
    reader.parse(text.splitlines())
    return {agent: bool(reader.can_fetch(agent, url)) for agent in _USER_AGENTS}


def _noindex(markers, evidence):
    raw = " ".join(markers.robots.get("robots", [])
        + markers.robots.get("googlebot", [])
        + markers.robots.get("oai-searchbot", [])
        + [evidence.x_robots_tag or ""])
    # Conservative diagnostic: noindex for ANY relevant bot blocks universal
    # crawlability claims, including bot-specific X-Robots-Tag.
    return "noindex" in {bit.strip().lower() for bit in re.split(r"[,;\s]+", raw)}


def audit_web_pages(catalog, pages: dict[str, PageEvidence], *,
                    robots_text: str | None = None, robots_http_status: int | None = None):
    """Inspect supplied bounded evidence; no network requests are performed."""
    if not isinstance(pages, dict) or not pages or len(pages) > MAX_PAGES:
        raise WebAuditError("provide 1 to 10 product page records")
    if set(pages) - set(catalog.by_sku):
        raise WebAuditError("page evidence SKU is absent from catalog")
    if robots_text is not None and (
            not isinstance(robots_text, str)
            or len(robots_text.encode("utf-8")) > MAX_ROBOTS_BYTES):
        raise WebAuditError("robots.txt text exceeds size limit")
    values = []
    for sku in sorted(pages):
        product, evidence = catalog.by_sku[sku], pages[sku]
        try:
            origin = _store_origin(product.merchant_homepage)
            if _store_origin(product.source_url) != origin:
                raise WebAuditError("product URL does not match merchant origin")
        except (BaseURLValidationError, TypeError):
            raise WebAuditError("merchant/product URLs must share a verified HTTPS origin") from None
        if not isinstance(evidence, PageEvidence):
            raise WebAuditError("invalid PageEvidence")
        reasons = []
        if evidence.status_code != 200:
            reasons.append("page_not_http_200")
        if 300 <= evidence.status_code < 400:
            reasons.append("redirect_not_followed")
        if "text/html" not in evidence.content_type.lower():
            reasons.append("content_type_not_html")
        if evidence.truncated or len(evidence.body) > MAX_HTML_BYTES:
            reasons.append("html_truncated")
        marker = _Markers()
        if not reasons:
            marker.feed(evidence.body.decode("utf-8", "replace"))
        canonical_urls = [urljoin(product.source_url, x) for x in marker.canonicals]
        canonical = ("missing" if not canonical_urls else
            "matches" if len(set(canonical_urls)) == 1 and
                         canonical_urls[0].rstrip("/") == product.source_url.rstrip("/")
            else "mismatch")
        if canonical != "matches":
            reasons.append("canonical_" + canonical)
        noindex = _noindex(marker, evidence)
        if noindex:
            reasons.append("noindex_directive_detected")
        robot_permission = _robots_states(robots_text, product.source_url)
        for agent, permitted in robot_permission.items():
            if permitted is False:
                reasons.append(agent.lower() + "_robots_disallow")
        node, structured = _find_jsonld(marker, product)
        if structured != "matched":
            reasons.append("product_jsonld_" + structured)
        offer = _offer_data(node) if node is not None else None
        price = _price_state(offer, product)
        availability = _availability_state(offer, product)
        if price == "mismatch":
            reasons.append("jsonld_price_mismatch")
        if availability == "mismatch":
            reasons.append("jsonld_availability_mismatch")
        values.append({
            "sku": sku, "http_status": evidence.status_code,
            "canonical": canonical, "noindex_detected": noindex,
            "robots_allow": robot_permission, "product_jsonld": structured,
            "jsonld_price": price, "jsonld_availability": availability,
            "issues": reasons, "page_evidence_sufficient": not reasons,
            "indexed": None, "search_visibility_observed": None,
        })
    return {
        "schema_version": "miseport-web-discovery-audit/1.0",
        "inspection_type": "bounded_original_page_evidence",
        "web_crawl_indexing_verified": False,
        "agent_natural_discovery_verified": False,
        "merchant_authorization_verified_by_software": False,
        "robots_http_status": robots_http_status,
        "robots_observed": robots_text is not None,
        "sitemap_advertised_in_robots": (
            any(line.strip().lower().startswith("sitemap:")
                for line in robots_text.splitlines()) if robots_text is not None else None),
        "checked": len(values),
        "with_issues": sum(bool(r["issues"]) for r in values),
        "products": values,
    }


def _safe_local_filename(directory: Path, value):
    if (not isinstance(value, str) or value in (".", "..")
            or not _FILE_NAME.fullmatch(value)):
        raise WebAuditError("evidence filename must be a simple local basename")
    p = directory / value
    if not p.is_file() or p.is_symlink():
        raise WebAuditError("evidence file unavailable or symlink")
    return p


def _read_limited(path, max_bytes):
    with Path(path).open("rb") as handle:
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise WebAuditError("evidence file exceeds size limit")
    return data


def audit_offline(catalog, manifest):
    manifest = Path(manifest)
    data = json.loads(_read_limited(manifest, 128 * 1024).decode("utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != "miseport-web-evidence/1.0":
        raise WebAuditError("invalid offline page manifest")
    records = data.get("items")
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_PAGES:
        raise WebAuditError("expected 1 to 10 offline pages")
    pages = {}
    for row in records:
        if not isinstance(row, dict) or set(row) != {"sku", "filename", "http_status"}:
            raise WebAuditError("invalid page record fields")
        sku = row["sku"]
        if not isinstance(sku, str) or sku in pages or type(row["http_status"]) is not int:
            raise WebAuditError("invalid or duplicate offline SKU")
        path = _safe_local_filename(manifest.parent, row["filename"])
        pages[sku] = PageEvidence(row["http_status"], "text/html; charset=utf-8",
                                  _read_limited(path, MAX_HTML_BYTES))
    robots_file = data.get("robots_file")
    text = (_read_limited(_safe_local_filename(manifest.parent, robots_file),
                          MAX_ROBOTS_BYTES).decode("utf-8")
            if robots_file is not None else None)
    return audit_web_pages(catalog, pages, robots_text=text,
                           robots_http_status=200 if text is not None else None)


def audit_live(catalog, *, approved=False, max_products=MAX_PAGES,
               transport=None):
    """Run only on explicit request, without PAT, cookies, login or redirects."""
    if approved is not True:
        raise WebAuditError("merchant must explicitly approve public page checks")
    if type(max_products) is not int or not 1 <= max_products <= MAX_PAGES:
        raise WebAuditError("product count must be 1..10")
    products = catalog.products[:max_products]
    if not products:
        raise WebAuditError("catalog has no products")
    try:
        origin = _store_origin(products[0].merchant_homepage)
        for product in products:
            if _store_origin(product.merchant_homepage) != origin or \
               _store_origin(product.source_url) != origin:
                raise WebAuditError("shop product URLs must share origin")
            # Existing safe HTTPS transport supports only paths without query.
            if urlsplit(product.source_url).query or urlsplit(product.source_url).fragment:
                raise WebAuditError("URL with query/fragment needs offline review")
    except (BaseURLValidationError, TypeError):
        raise WebAuditError("invalid owner-controlled HTTPS shop URL") from None
    fetch = transport or _fetch_page
    robot_text, robot_status = None, None
    try:
        robot = fetch(origin + "/robots.txt", 4.0, MAX_ROBOTS_BYTES)
        if not isinstance(robot, PageEvidence):
            raise ValueError("invalid robots response")
        robot_status = robot.status_code
        if robot.status_code == 200 and not robot.truncated and \
                len(robot.body) <= MAX_ROBOTS_BYTES:
            robot_text = robot.body.decode("utf-8", "replace")
    except (OSError, ValueError):
        pass
    pages = {}
    for p in products:
        try:
            evidence = fetch(p.source_url, 4.0, MAX_HTML_BYTES)
            if not isinstance(evidence, PageEvidence):
                raise ValueError("invalid page response")
        except (OSError, ValueError):
            evidence = PageEvidence(0, "", b"")
        pages[p.sku] = evidence
    return audit_web_pages(catalog, pages, robots_text=robot_text,
                           robots_http_status=robot_status)


def main():
    parser = argparse.ArgumentParser(prog="miseport-web-discovery-audit")
    parser.add_argument("--catalog", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline-manifest")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--merchant-approved", action="store_true")
    parser.add_argument("--max-products", type=int, default=MAX_PAGES)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        catalog = load_catalog(args.catalog)
        if args.live:
            report = audit_live(catalog, approved=args.merchant_approved,
                                max_products=args.max_products)
        else:
            report = audit_offline(catalog, args.offline_manifest)
        from .eval import write_report
        write_report(args.output, report)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"checked": report["checked"], "with_issues": report["with_issues"]}))
    # A diagnostic report is useful even when page issues were found.


if __name__ == "__main__":
    main()
