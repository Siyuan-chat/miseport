"""Offline test doubles for read-only remote deployment verification."""
import pytest

from miseport.deployment_probe import (
    DeploymentCheckError, MCP_PROTOCOL, REQUIRED_TOOLS, check_live_merchant_deployment
)

ORIGIN = "https://tea.pages.dev"
STAMP = "2026-10-29T11:01:00+00:00"
SKU = "base-17"
SOURCE = "https://shop.example.org/items/17"


def fake_transport(modifications=None):
    mods = modifications or {}
    calls = []
    tools = [
        {"name": name, "annotations": {"readOnlyHint": True}}
        for name in sorted(REQUIRED_TOOLS)
    ]
    result_for = {
        ("GET", "/healthz"): {"ok": True, "read_only": True,
                              "demo_only": False, "product_count": 2,
                              "snapshot_at": STAMP},
        ("GET", "/api/products"): {"products": [], "total": 2,
                                   "offset": 0, "limit": 20},
        ("POST", "/mcp:initialize"): {"jsonrpc":"2.0","id":1,
                "result":{"protocolVersion":MCP_PROTOCOL,
                          "serverInfo":{"name":"MisePort Merchant","version":"0.1"}}},
        ("POST", "/mcp:tools/list"): {"jsonrpc":"2.0","id":2,
                "result":{"tools":tools}},
        ("POST", "/mcp:tools/call"): {"jsonrpc":"2.0","id":3,
                "result":{"structuredContent":{"found":True,
                       "product":{"sku":SKU,"source_url":SOURCE,
                                  "price_jpy":1800,"is_demo":False}}}},
    }
    result_for.update(mods)
    def fetch(method,url,payload,timeout,max_bytes):
        assert url.startswith(ORIGIN+"/")
        assert timeout == 5.0 and max_bytes == 256*1024
        assert payload is None or "Authorization" not in str(payload)
        suffix = url.removeprefix(ORIGIN)
        if method=="POST":
            suffix += ":" + payload.get("method", "")
        key=(method,suffix)
        calls.append(key)
        return 200, result_for[key]
    return fetch,calls


def check(transport=None, **kwargs):
    values=dict(
        origin=ORIGIN, expected_snapshot_at=STAMP, expected_product_count=2,
        expected_sku=SKU, expected_source_url=SOURCE,
        expected_price_jpy=1800,
    )
    values.update(kwargs)
    return check_live_merchant_deployment(
        transport=transport or fake_transport()[0], **values
    )


def test_successfully_identifies_exact_deployed_snapshot_and_mcp_tool():
    fetch, calls = fake_transport()
    report = check(fetch).summary()
    assert report["rest_ok"] is True and report["mcp_ok"] is True
    assert report["product_count"] == 2
    assert report["matched_sku"] == SKU
    assert report["snapshot_at"] == STAMP
    assert set(report["mcp_tools"]) == REQUIRED_TOOLS
    assert calls == [
        ("GET", "/healthz"), ("GET", "/api/products"),
        ("POST", "/mcp:initialize"), ("POST", "/mcp:tools/list"),
        ("POST", "/mcp:tools/call"),
    ]


@pytest.mark.parametrize("patch,code", [
    ({("GET", "/healthz"): {"ok":True,"read_only":True,"demo_only":True,
                              "product_count":2,"snapshot_at":STAMP}}, "ZIPと一致"),
    ({("GET", "/healthz"): {"ok":True,"read_only":True,"demo_only":False,
                              "product_count":2,"snapshot_at":"old-version"}}, "ZIPと一致"),
    ({("GET", "/healthz"): {"ok":True,"read_only":False,"demo_only":False,
                              "product_count":2,"snapshot_at":STAMP}}, "ZIPと一致"),
    ({("GET", "/api/products"): {"total":1,"products":[]}}, "REST"),
    ({("POST", "/mcp:initialize"): {"jsonrpc":"2.0","id":1,
                              "result":{"protocolVersion":"unknown",
                                        "serverInfo":{"name":"MisePort Merchant"}}}}, "initialize"),
    ({("POST", "/mcp:tools/list"): {"jsonrpc":"2.0","id":2,"result":{"tools":[]}}}, "ツール"),
    ({("POST", "/mcp:tools/call"): {"jsonrpc":"2.0","id":3,
            "result":{"structuredContent":{"found":True,
                   "product":{"sku":SKU,"price_jpy":2000,
                              "source_url":SOURCE,"is_demo":False}}}}}, "商品情報"),
])
def test_wrong_store_version_tool_or_product_never_passes(patch, code):
    with pytest.raises(DeploymentCheckError, match=code):
        check(fake_transport(patch)[0])


@pytest.mark.parametrize("origin", [
    "http://tea.pages.dev", "https://tea.pages.dev/",
    "https://localhost", "https://127.0.0.1",
    "https://tea.pages.dev:8443", "https://other.pages.dev/path",
    "https://user:password@tea.pages.dev",
])
def test_invalid_target_refused_before_any_transport(origin):
    def never(*args):
        raise AssertionError("should not access any remote host")
    with pytest.raises(DeploymentCheckError):
        check(never, origin=origin)


def test_errors_are_redacted_not_raw_network_errors():
    def broken(*args):
        raise OSError("BASE_PAT=SECRET_SHOULD_NOT_BE_DISPLAYED")
    with pytest.raises(DeploymentCheckError) as err:
        check(broken)
    assert "SECRET_SHOULD_NOT_BE_DISPLAYED" not in str(err.value)


def test_unexpected_rpc_error_cannot_be_accepted():
    r = {"jsonrpc":"2.0", "id":2, "error":{"code":-32000,"message":"bad"}}
    with pytest.raises(DeploymentCheckError):
        check(fake_transport({("POST","/mcp:tools/list"):r})[0])


def test_unreadable_product_source_or_invalid_expected_fields():
    for bad in [
        {"expected_product_count":0},
        {"expected_product_count":"2"},
        {"expected_source_url":"http://example.org/1"},
        {"expected_sku":""},
        {"expected_price_jpy":-1},
        {"expected_snapshot_at":""},
        {"timeout":0},
    ]:
        with pytest.raises(DeploymentCheckError):
            check(**bad)


def test_no_unexpected_rpc_tool_access():
    fetch,calls=fake_transport()
    check(fetch)
    assert set(calls) == {
        ("GET","/healthz"),("GET","/api/products"),
        ("POST","/mcp:initialize"),("POST","/mcp:tools/list"),("POST","/mcp:tools/call"),
    }
