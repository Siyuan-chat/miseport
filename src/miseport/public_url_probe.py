"""Bounded, read-only checks for candidate BASE public product pages.

Never use a BASE PAT, proxy, cookies, crawlers or redirect following here.
A successful canonical/og:url match is evidence for a public item page, not
an assertion of live price, merchant ownership, or agent discoverability.

Network connections pin a DNS result already verified to be globally routable
and use the merchant hostname for TLS SNI/certificate validation.
"""
from dataclasses import dataclass
from html.parser import HTMLParser
import http.client
import ipaddress
import socket
import ssl
from typing import Callable, Mapping
from urllib.parse import urlsplit

from .base_urls import BaseURLValidationError, _store_origin, validate_manual_product_urls


MAX_URL_CHECKS = 30
MAX_HTML_BYTES = 128 * 1024
DEFAULT_TIMEOUT = 4.0


@dataclass(frozen=True)
class PageEvidence:
    status_code: int
    content_type: str
    body: bytes = b""
    truncated: bool = False
    redirect_location: str | None = None
    x_robots_tag: str | None = None


@dataclass(frozen=True)
class URLCheck:
    item_id: int
    url: str
    state: str
    code: str
    http_status: int | None = None


@dataclass(frozen=True)
class URLCheckReport:
    origin: str
    results: tuple[URLCheck, ...]

    def summary(self) -> dict:
        records = [vars(x) for x in self.results]
        return {
            "origin": self.origin,
            "checked": len(records),
            "confirmed": sum(x.state == "confirmed" for x in self.results),
            "uncertain": sum(x.state == "uncertain" for x in self.results),
            "rejected": sum(x.state == "rejected" for x in self.results),
            "results": records,
            "note": "Reachability/identity check only; store owner must approve publication.",
        }


class URLProbeError(ValueError):
    """Error intentionally excludes URL query fragments, secrets, and HTTP bodies."""


class _ItemMarkers(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical = []
        self.og_urls = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() not in {"link", "meta"}:
            return
        data = dict((str(k).lower(), v or "") for k, v in attrs)
        if tag.lower() == "link" and "canonical" in data.get("rel", "").lower().split():
            self.canonical.append(data.get("href", "").strip())
        if tag.lower() == "meta" and data.get("property", "").lower() == "og:url":
            self.og_urls.append(data.get("content", "").strip())


def _global_ips(host: str, *, resolver=None) -> tuple[str, ...]:
    resolver = resolver or socket.getaddrinfo
    try:
        records = resolver(host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        ips = sorted({record[4][0] for record in records})
        if not ips or not all(ipaddress.ip_address(ip).is_global for ip in ips):
            raise URLProbeError("公開インターネット以外の接続先は検査できません。")
        return tuple(ips)
    except URLProbeError:
        raise
    except (OSError, ValueError, IndexError):
        raise URLProbeError("店舗ドメインのDNSを安全に確認できません。") from None


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float):
        super().__init__(host, port=443, timeout=timeout,
                         context=ssl.create_default_context())
        self.address = address

    def connect(self):
        # Socket targets the DNS-checked public IP, while the TLS hostname is
        # the original shop domain. No unsafe post-check DNS re-resolution.
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


def _fetch_page(url: str, timeout: float, max_bytes: int) -> PageEvidence:
    parts = urlsplit(url)
    _store_origin(url)
    host = parts.hostname
    if not host or parts.port not in (None, 443):
        raise URLProbeError("店舗の公開URLを確認してください。")
    addresses = _global_ips(host)
    conn = _PinnedHTTPS(host, addresses[0], timeout)
    try:
        conn.request("GET", parts.path, headers={
            "Host": host,
            "Accept": "text/html",
            "Accept-Encoding": "identity",
            "User-Agent": "MisePort/0.1 (merchant-approved single-shop URL check)",
            "Connection": "close",
        })
        response = conn.getresponse()
        status = response.status
        content_type = response.getheader("Content-Type", "")[:200]
        # Redirects are reported but never followed to another host or LAN.
        location = response.getheader("Location")
        if 300 <= status < 400:
            return PageEvidence(status, content_type, redirect_location=location,
                                x_robots_tag=response.getheader("X-Robots-Tag"))
        if status != 200:
            return PageEvidence(status, content_type,
                                x_robots_tag=response.getheader("X-Robots-Tag"))
        data = response.read(max_bytes + 1)
        return PageEvidence(status, content_type, data[:max_bytes],
                            truncated=len(data) > max_bytes,
                            x_robots_tag=response.getheader("X-Robots-Tag"))
    finally:
        conn.close()


def _page_result(item_id: int, url: str, evidence: PageEvidence) -> URLCheck:
    status = evidence.status_code
    if type(status) is not int or not 100 <= status <= 599:
        return URLCheck(item_id, url, "uncertain", "UNEXPECTED_STATUS")
    if 300 <= status < 400:
        return URLCheck(item_id, url, "uncertain", "REDIRECT_NOT_FOLLOWED", status)
    if status in (404, 410):
        return URLCheck(item_id, url, "rejected", "NOT_FOUND", status)
    if status != 200:
        return URLCheck(item_id, url, "uncertain", "NOT_VERIFIED", status)
    if "text/html" not in evidence.content_type.lower():
        return URLCheck(item_id, url, "uncertain", "NOT_HTML", status)
    if evidence.truncated:
        return URLCheck(item_id, url, "uncertain", "PAGE_TOO_LARGE", status)
    if not isinstance(evidence.body, bytes) or len(evidence.body) > MAX_HTML_BYTES:
        return URLCheck(item_id, url, "uncertain", "BAD_HTML", status)
    try:
        parser = _ItemMarkers()
        parser.feed(evidence.body.decode("utf-8", errors="replace"))
        links = parser.canonical + parser.og_urls
        if not links:
            return URLCheck(item_id, url, "uncertain", "NO_IDENTITY_TAG", status)
        # Conflicting canonical / OG links are not conclusive.
        if all(link.rstrip("/") == url for link in links):
            return URLCheck(item_id, url, "confirmed", "MATCHING_CANONICAL", status)
        return URLCheck(item_id, url, "uncertain", "CANONICAL_MISMATCH", status)
    except (ValueError, UnicodeError):
        return URLCheck(item_id, url, "uncertain", "BAD_HTML", status)


def check_product_urls(
    urls: Mapping[int, str],
    homepage: str,
    *,
    transport: Callable[[str, float, int], PageEvidence] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> URLCheckReport:
    """Explicit, merchant-started, limited requests. No authentication sent."""
    if (not isinstance(urls, dict) or not urls or len(urls) > MAX_URL_CHECKS
            or type(timeout) not in (int, float) or not 1.0 <= timeout <= 10.0):
        raise URLProbeError("商品URLの検査は一度に1〜30件、タイムアウト1〜10秒です。")
    try:
        validate_manual_product_urls(urls, homepage)
        origin = _store_origin(homepage)
    except BaseURLValidationError:
        raise URLProbeError("店舗と商品URLの形式を確認してください。") from None
    fetch = transport or _fetch_page
    results = []
    for item_id, url in sorted(urls.items()):
        try:
            page = fetch(url, float(timeout), MAX_HTML_BYTES)
            if not isinstance(page, PageEvidence):
                raise ValueError("invalid response type")
            checked = _page_result(item_id, url, page)
        except (OSError, ValueError, ssl.SSLError, http.client.HTTPException):
            # No host traces, response headers, API credentials or raw HTML.
            checked = URLCheck(item_id, url, "uncertain", "NETWORK_OR_DNS_ERROR")
        results.append(checked)
    return URLCheckReport(origin, tuple(results))
