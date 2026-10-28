"""Real SDK ASGI requests and resource-boundary checks; no background servers."""
import asyncio
import json
from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

from miseport.http import ServiceLimits, create_app

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples/products.json"
HEADERS = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25"}


def app(**kwargs):
    return create_app(SAMPLE, allowed_hosts=["testserver", "demo.example:*"],
                      allowed_origins=["https://client.example"], **kwargs)


def test_real_http_initialize_list_and_quote():
    with TestClient(app()) as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        assert set(health.json()) == {"ready", "demo", "version", "count"}
        assert health.json()["ready"] and health.json()["demo"] and health.json()["count"] == 4
        initialized = client.post("/mcp", headers=HEADERS, json={"jsonrpc": "2.0", "id": 1,
            "method": "initialize", "params": {"protocolVersion": "2025-11-25",
                "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}})
        assert initialized.status_code == 200, initialized.text
        assert initialized.json()["result"]["serverInfo"]["name"] == "MisePort"
        listing = client.post("/mcp", headers=HEADERS,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = listing.json()["result"]["tools"]
        assert len(tools) == 7 and all(t["annotations"]["readOnlyHint"] for t in tools)
        called = client.post("/mcp", headers=HEADERS, json={"jsonrpc": "2.0", "id": 3,
            "method": "tools/call", "params": {"name": "get_quote",
                "arguments": {"sku": "coffee-001", "quantity": 2}}})
        result = json.loads(called.json()["result"]["content"][0]["text"])
        assert result["subtotal_jpy"] == 2960 and result["is_demo"] is True
        assert result["is_binding"] is False and result["stock_is_live"] is False
        about = client.post("/mcp", headers=HEADERS, json={"jsonrpc": "2.0", "id": 4,
            "method": "tools/call", "params": {"name": "about_miseport", "arguments": {}}})
        assert json.loads(about.json()["result"]["content"][0]["text"])["transport"] == "streamable-http"


@pytest.mark.parametrize("path", ["/healthz", "/mcp"])
def test_host_and_origin_checks_cover_health_and_mcp(path):
    with TestClient(app()) as client:
        assert client.get(path, headers={"Host": "evil.example"}).status_code == 421
        assert client.get(path, headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.get(path, headers={"Host": "demo.example:443.evil"}).status_code == 421
        assert client.get("/healthz", headers={"Host": "demo.example:443",
                                              "Origin": "https://client.example"}).status_code == 200


@pytest.mark.parametrize("hosts,origins", [
    (None, None), (["demo.example"], None), (["*"], ["https://client.example"]),
    (["*.example"], ["https://client.example"]), (["demo.example:*"], ["*"]),
    (["demo.example"], ["https://client.example/path"]),
    (["https://demo.example"], ["https://client.example"]),
])
def test_public_bind_requires_specific_allowlists(hosts, origins):
    with pytest.raises(ValueError):
        create_app(SAMPLE, host="0.0.0.0", allowed_hosts=hosts, allowed_origins=origins)


@pytest.mark.parametrize("kind", ["empty", "real", "mixed"])
def test_non_demo_or_empty_catalog_never_served(tmp_path, kind):
    rows = json.loads(SAMPLE.read_text(encoding="utf-8"))
    if kind == "empty":
        rows = []
    elif kind == "real":
        for row in rows:
            row["is_demo"] = False
    else:
        rows[0]["is_demo"] = False
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError, match="demo catalog"):
        create_app(path)


def test_body_limit_checks_declared_and_chunked_body():
    with TestClient(app(body_limit=16)) as client:
        assert client.post("/mcp", content=b"x" * 17).status_code == 413
        assert client.post("/mcp", content=iter([b"x" * 8, b"x" * 9])).status_code == 413
        assert client.post("/mcp", headers={"Content-Length": "x"}).status_code == 400


def test_process_rate_limit_and_recovery():
    service = app(requests_per_minute=2)
    with TestClient(service) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/healthz").status_code == 200
        assert client.get("/healthz").status_code == 429
        service.requests.clear()
        assert client.get("/healthz").status_code == 200


def test_explicit_public_binding_accepts_exact_host_and_native_client():
    service = app(host="0.0.0.0")
    with TestClient(service, base_url="https://demo.example:8443") as client:
        assert client.get("/healthz").status_code == 200


def test_slow_body_and_duplicate_headers_are_bounded():
    async def exercise():
        async def unused(scope, receive, send):
            raise AssertionError("invalid request reached application")

        service = ServiceLimits(unused, ["testserver"], [], timeout=0.02)
        scope = {"type": "http", "method": "POST", "path": "/mcp",
                 "headers": [(b"host", b"testserver")]}

        async def slow_receive():
            await asyncio.sleep(1)

        sent = []

        async def collect(message):
            sent.append(message)

        await service(scope, slow_receive, collect)
        assert sent[0]["status"] == 504 and service.active == 0
        sent.clear()
        scope["headers"].append((b"host", b"evil.example"))
        await service(scope, slow_receive, collect)
        assert sent[0]["status"] == 400
    asyncio.run(exercise())


def test_request_deadline_and_concurrency_release():
    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()

        async def slow(scope, receive, send):
            entered.set()
            await release.wait()

        service = ServiceLimits(slow, ["testserver"], [], timeout=0.05, max_concurrency=1)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=service),
                                     base_url="http://testserver") as client:
            pending = asyncio.create_task(client.get("/mcp"))
            await asyncio.wait_for(entered.wait(), 1)
            assert (await client.get("/mcp")).status_code == 503
            assert (await pending).status_code == 504
            assert service.active == 0
    asyncio.run(exercise())
