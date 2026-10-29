"""Explicit read-only smoke check of a merchant's published MCP/REST endpoint.

Only the host from a validated merchant HTTPS origin is contacted. DNS results
are checked for globally routable addresses and pinned during verified TLS.
No BASE PAT, Cloudflare account token, Cookie, redirects, or write methods.
"""
from dataclasses import dataclass
import http.client
import json
import ssl
from typing import Callable
from urllib.parse import urlsplit

from .merchant_onboarding import DeploymentGuideError, merchant_deploy_guide
from .public_url_probe import _PinnedHTTPS, _global_ips

MAX_RESPONSE_BYTES = 256 * 1024
MCP_PROTOCOL = "2025-11-25"
REQUIRED_TOOLS = frozenset({
    "about_miseport", "search_products", "get_product", "check_inventory",
    "get_quote", "audit_catalog", "export_product_jsonld",
})


class DeploymentCheckError(ValueError):
    """Safe UI error: does not echo arbitrary HTTP bodies or request secrets."""


@dataclass(frozen=True)
class LiveDeploymentCheck:
    origin: str
    product_count: int
    matched_sku: str
    snapshot_at: str
    mcp_tools: tuple[str, ...]
    rest_ok: bool
    mcp_ok: bool

    def summary(self):
        return {
            "origin": self.origin,
            "product_count": self.product_count,
            "matched_sku": self.matched_sku,
            "snapshot_at": self.snapshot_at,
            "mcp_tools": list(self.mcp_tools),
            "rest_ok": self.rest_ok,
            "mcp_ok": self.mcp_ok,
            "message": "Public endpoint smoke test only; Muse discovery and live stock are separate.",
        }


def _unique_object(pairs):
    value = {}
    for name, field in pairs:
        if name in value:
            raise DeploymentCheckError("JSONに重複項目があります。")
        value[name] = field
    return value


def _request_json(
    method: str, url: str, payload: dict | None,
    timeout: float, max_bytes: int
) -> tuple[int, dict]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.port not in (None, 443):
        raise DeploymentCheckError("接続先はHTTPS公開ドメインに限ります。")
    ip = _global_ips(parsed.hostname)[0]
    conn = _PinnedHTTPS(parsed.hostname, ip, timeout)
    headers = {
        "Accept": "application/json, text/event-stream" if method == "POST" else "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "MisePort/0.1 (explicit merchant deployment smoke test)",
        "Connection": "close",
    }
    data = None
    if method == "POST":
        if payload is None:
            raise DeploymentCheckError("MCPリクエストがありません。")
        data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        if len(data) > 4096:
            raise DeploymentCheckError("MCPリクエストが大きすぎます。")
        headers["Content-Type"] = "application/json"
        headers["MCP-Protocol-Version"] = MCP_PROTOCOL
    try:
        conn.request(method, parsed.path, body=data, headers=headers)
        response = conn.getresponse()
        status = response.status
        content_type = response.getheader("Content-Type", "")
        if 300 <= status < 400:
            raise DeploymentCheckError("公開先がリダイレクトしました。元の公開URLを確認してください。")
        if status != 200:
            raise DeploymentCheckError("公開先がHTTP " + str(status) + " を返しました。")
        if "application/json" not in content_type.lower():
            raise DeploymentCheckError("公開先からJSONを取得できません。")
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise DeploymentCheckError("公開応答がサイズ上限を超えました。")
        try:
            result = json.loads(raw.decode("utf-8"),
                                object_pairs_hook=_unique_object)
        except (UnicodeError, ValueError, RecursionError):
            raise DeploymentCheckError("公開先のJSON形式が正しくありません。") from None
        if not isinstance(result, dict):
            raise DeploymentCheckError("公開先のJSONが想定形式ではありません。")
        return status, result
    except DeploymentCheckError:
        raise
    except (http.client.HTTPException, OSError, ssl.SSLError, ValueError):
        raise DeploymentCheckError("公開先へのHTTPS接続を安全に確認できません。") from None
    finally:
        conn.close()


def _rpc_reply(data: dict, request_id: int) -> dict:
    if (data.get("jsonrpc") != "2.0" or data.get("id") != request_id
            or not isinstance(data.get("result"), dict) or "error" in data):
        raise DeploymentCheckError("MCPサーバーの応答が想定形式ではありません。")
    return data["result"]


def check_live_merchant_deployment(
    origin: str, *,
    expected_snapshot_at: str,
    expected_product_count: int,
    expected_sku: str,
    expected_source_url: str,
    expected_price_jpy: int,
    transport: Callable[[str, str, dict | None, float, int], tuple[int, dict]] | None = None,
    timeout: float = 5.0,
) -> LiveDeploymentCheck:
    """Check only 5 bounded reads against the exact merchant-owned origin.

    API success means this accessible server matches the bundle snapshot.
    It does not establish the identity of the user/account who deployed it.
    """
    try:
        guide = merchant_deploy_guide(origin)
    except DeploymentGuideError:
        raise DeploymentCheckError("公開先HTTPSドメインを確認してください。") from None
    if (not isinstance(expected_snapshot_at, str)
            or not 10 <= len(expected_snapshot_at) <= 80
            or type(expected_product_count) is not int or
            not 1 <= expected_product_count <= 10000
            or type(expected_sku) is not str or not 1 <= len(expected_sku) <= 128
            or type(expected_source_url) is not str or not expected_source_url.startswith("https://")
            or type(expected_price_jpy) is not int or expected_price_jpy < 0
            or type(timeout) not in (int, float) or not 1 <= timeout <= 10):
        raise DeploymentCheckError("検査する商店の情報を確認してください。")
    fetch = transport or _request_json
    allowed_paths = {
        "/healthz", "/api/products", "/mcp",
    }
    def request(method, suffix, data=None):
        if suffix not in allowed_paths or method not in ("GET", "POST"):
            raise DeploymentCheckError("許可されていない接続先です。")
        try:
            status, result = fetch(method, origin + suffix, data, timeout, MAX_RESPONSE_BYTES)
        except DeploymentCheckError:
            raise
        except (OSError, ValueError):
            raise DeploymentCheckError("公開サーバーの検査に失敗しました。") from None
        if status != 200 or type(result) is not dict:
            raise DeploymentCheckError("公開先のJSONを確認できません。")
        return result

    health = request("GET", "/healthz")
    if (health.get("ok") is not True or health.get("read_only") is not True
            or health.get("demo_only") is not False
            or health.get("product_count") != expected_product_count
            or health.get("snapshot_at") != expected_snapshot_at):
        raise DeploymentCheckError("公開中の商品数またはバージョンがZIPと一致しません。")
    rest = request("GET", "/api/products")
    if (rest.get("total") != expected_product_count
            or not isinstance(rest.get("products"), list)):
        raise DeploymentCheckError("商品REST APIの内容が一致しません。")
    hello = request("POST", "/mcp", {"jsonrpc":"2.0","id":1,"method":"initialize",
        "params":{"protocolVersion":MCP_PROTOCOL,"capabilities":{},
                  "clientInfo":{"name":"MisePort-verifier","version":"0.1"}}})
    initialized = _rpc_reply(hello, 1)
    if (initialized.get("protocolVersion") != MCP_PROTOCOL or
            initialized.get("serverInfo", {}).get("name") != "MisePort Merchant"):
        raise DeploymentCheckError("MCP initializeが一致しません。")
    response = request("POST", "/mcp", {"jsonrpc":"2.0","id":2,"method":"tools/list"})
    tools = _rpc_reply(response, 2).get("tools")
    if (not isinstance(tools, list)
            or {x.get("name") for x in tools if isinstance(x,dict)} != REQUIRED_TOOLS
            or any(x.get("annotations", {}).get("readOnlyHint") is not True
                   for x in tools if isinstance(x,dict))):
        raise DeploymentCheckError("MCPの読み取り専用ツール構成が一致しません。")
    result = request("POST", "/mcp", {"jsonrpc":"2.0","id":3,"method":"tools/call",
        "params":{"name":"get_product","arguments":{"sku":expected_sku}}})
    detail = _rpc_reply(result, 3).get("structuredContent")
    product = detail.get("product") if isinstance(detail,dict) else None
    if (not isinstance(product,dict) or detail.get("found") is not True
            or product.get("sku") != expected_sku
            or product.get("source_url") != expected_source_url
            or product.get("price_jpy") != expected_price_jpy
            or product.get("is_demo") is not False):
        raise DeploymentCheckError("MCPの商品情報が保存済みZIPと一致しません。")
    return LiveDeploymentCheck(
        origin=origin,
        product_count=expected_product_count,
        matched_sku=expected_sku,
        snapshot_at=expected_snapshot_at,
        mcp_tools=tuple(sorted(REQUIRED_TOOLS)),
        rest_ok=True, mcp_ok=True,
    )
