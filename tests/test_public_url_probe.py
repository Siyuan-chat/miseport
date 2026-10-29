"""All URL checks are offline / mocked. No real merchant endpoints contacted."""
import socket

import pytest

from miseport.public_url_probe import (
    MAX_URL_CHECKS, PageEvidence, URLProbeError, _global_ips, check_product_urls
)

HOME = "https://shop.example.org/"
URL1 = "https://shop.example.org/items/1"
URL2 = "https://shop.example.org/items/2"


def response(status=200, body=None, content_type="text/html; charset=utf-8",
             truncated=False):
    if body is None:
        body = '<html><head><link rel="canonical" href="' + URL1 + '"></head></html>'
    return PageEvidence(status, content_type, body.encode(), truncated=truncated)


def test_exact_canonical_is_confirmed_without_network():
    calls = []
    def fake(url, timeout, max_size):
        calls.append((url, timeout, max_size))
        return response()
    report = check_product_urls({1: URL1}, HOME, transport=fake)
    assert report.summary()["confirmed"] == 1
    assert report.summary()["uncertain"] == 0
    assert report.results[0].code == "MATCHING_CANONICAL"
    assert calls[0][0] == URL1
    assert calls[0][1] == 4.0


def test_og_url_identity_supported_when_canonical_missing():
    page = '<html><head><meta property="og:url" content="' + URL1 + '"></head></html>'
    report = check_product_urls({1: URL1}, HOME,
                                transport=lambda *_: response(body=page))
    assert report.summary()["confirmed"] == 1


@pytest.mark.parametrize("body,code", [
    ("<html><title>商品</title></html>", "NO_IDENTITY_TAG"),
    ('<link rel="canonical" href="' + URL2 + '">', "CANONICAL_MISMATCH"),
    ('<link rel="canonical" href="' + URL1 + '">'
     '<meta property="og:url" content="' + URL2 + '">', "CANONICAL_MISMATCH"),
    ('<link rel="canonical" href="https://evil.example.org/items/1">', "CANONICAL_MISMATCH"),
    ('<link rel="canonical" href="/items/1">', "CANONICAL_MISMATCH"),
])
def test_missing_or_conflicting_public_page_identity_is_not_confirmed(body, code):
    r = check_product_urls({1: URL1}, HOME,
        transport=lambda *_: response(body=body))
    assert r.results[0].state == "uncertain"
    assert r.results[0].code == code


@pytest.mark.parametrize("status, expected_state, code", [
    (301, "uncertain", "REDIRECT_NOT_FOLLOWED"),
    (302, "uncertain", "REDIRECT_NOT_FOLLOWED"),
    (307, "uncertain", "REDIRECT_NOT_FOLLOWED"),
    (404, "rejected", "NOT_FOUND"),
    (410, "rejected", "NOT_FOUND"),
    (403, "uncertain", "NOT_VERIFIED"),
    (429, "uncertain", "NOT_VERIFIED"),
    (500, "uncertain", "NOT_VERIFIED"),
])
def test_response_codes_do_not_falsely_confirm(status, expected_state, code):
    r = check_product_urls({1: URL1}, HOME,
        transport=lambda *_: response(status))
    assert (r.results[0].state, r.results[0].code) == (expected_state, code)


def test_bad_content_and_large_page_not_trusted():
    for page, code in [
        (response(content_type="application/json"), "NOT_HTML"),
        (response(truncated=True), "PAGE_TOO_LARGE"),
        (PageEvidence(200, "text/html", b"x" * (129 * 1024)), "BAD_HTML"),
        (PageEvidence(200, "text/html", b"", False), "NO_IDENTITY_TAG"),
    ]:
        r = check_product_urls({1: URL1}, HOME, transport=lambda *_: page)
        assert r.results[0].state == "uncertain"
        assert r.results[0].code == code


def test_failed_dns_never_echoes_header_or_local_path():
    def forbidden(*_):
        raise RuntimeError("No request allowed")
    # RuntimeError is not one of the safe transport failures; test with OSError.
    def offline(*_):
        raise OSError("API_TOKEN=SHOULD_NOT_SHOW")
    summary = check_product_urls({1: URL1}, HOME, transport=offline).summary()
    assert summary["uncertain"] == 1
    assert summary["results"][0]["code"] == "NETWORK_OR_DNS_ERROR"
    assert "SHOULD_NOT_SHOW" not in str(summary)


def test_different_merchant_private_network_and_unbounded_scan_rejected():
    for bad in [
        {1: "http://shop.example.org/items/1"},
        {1: "https://evil.example.org/items/1"},
        {1: "https://shop.example.org/items/2"},
        {1: "https://localhost/items/1"},
        {1: "https://127.0.0.1/items/1"},
        {1: "https://shop.example.org:8443/items/1"},
        {1: "https://shop.example.org/items/1?token=secret"},
    ]:
        with pytest.raises(URLProbeError):
            check_product_urls(bad, HOME, transport=lambda *_: response())
    huge = {x: f"https://shop.example.org/items/{x}" for x in range(1, MAX_URL_CHECKS + 2)}
    with pytest.raises(URLProbeError, match="30件"):
        check_product_urls(huge, HOME, transport=lambda *_: response())


def test_batch_counts_and_stable_order():
    outcomes = {
        URL1: response(body=f'<link rel="canonical" href="{URL1}">'),
        URL2: response(status=404),
    }
    report = check_product_urls({2: URL2, 1: URL1}, HOME,
                                transport=lambda url, *_: outcomes[url]).summary()
    assert report["checked"] == 2
    assert report["confirmed"] == 1 and report["rejected"] == 1
    assert [x["item_id"] for x in report["results"]] == [1, 2]


def _dns(host, port, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.215.14", 443))]


def test_global_address_allowed_and_private_rejected_before_connect():
    assert _global_ips("shop.example.org", resolver=_dns) == ("93.184.215.14",)
    for ip in ("127.0.0.1", "10.0.0.5", "192.168.2.3",
               "169.254.169.254", "0.0.0.0", "198.51.100.10", "100.64.0.1"):
        def resolve(*args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]
        with pytest.raises(URLProbeError):
            _global_ips("shop.example.org", resolver=resolve)


def test_dns_with_both_public_and_private_ip_is_rejected():
    def resolve(*args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.215.14", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ]
    with pytest.raises(URLProbeError):
        _global_ips("shop.example.org", resolver=resolve)


def test_invalid_timeout_and_missing_mapping_are_rejected():
    for timeout in (0.1, 20, "3", True):
        with pytest.raises(URLProbeError):
            check_product_urls({1: URL1}, HOME, transport=lambda *_: response(),
                               timeout=timeout)
    with pytest.raises(URLProbeError):
        check_product_urls({}, HOME, transport=lambda *_: response())
