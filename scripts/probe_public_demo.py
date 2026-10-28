"""Bounded, read-only acceptance of the deliberately public synthetic demo."""
import asyncio
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ORIGIN = "https://miseport.pages.dev"


async def main():
    evidence = {"origin": ORIGIN, "checked_at": datetime.now(timezone.utc).isoformat(), "http": [], "mcp": []}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for path in ("/", "/docs/", "/privacy.html", "/terms.html", "/assets/original/miseport-logo.png", "/healthz", "/openapi.json", "/api/products?query=お茶", "/api/quote/tea-001?quantity=2"):
            response = await client.get(ORIGIN + path)
            response.raise_for_status()
            evidence["http"].append({"path": path, "status": response.status_code, "bytes": len(response.content)})
        for path, headers, expected in (("/mcp", {}, 405), ("/healthz", {"Origin": "https://unlisted.example"}, 403), ("/api/products/missing", {}, 404), ("/api/products?limit=true", {}, 400)):
            response = await client.get(ORIGIN + path, headers=headers)
            assert response.status_code == expected, (path, response.status_code, response.text)
            evidence["http"].append({"path": path, "status": response.status_code, "negative_case": True})
    async with streamable_http_client(ORIGIN + "/mcp") as (read, write, _):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=20)) as session:
            initialized = await session.initialize()
            evidence["protocol"] = initialized.protocolVersion
            tools = await session.list_tools()
            assert len(tools.tools) == 7 and all(t.annotations.readOnlyHint for t in tools.tools)
            calls = [("about_miseport", {}), ("search_products", {"query": "お茶"}), ("get_product", {"sku": "tea-001"}), ("check_inventory", {"sku": "tea-001"}), ("get_quote", {"sku": "tea-001", "quantity": 2}), ("audit_catalog", {}), ("export_product_jsonld", {"sku": "tea-001"}), ("get_product", {"sku": "missing"})]
            for name, arguments in calls:
                result = await session.call_tool(name, arguments)
                assert not result.isError, result
                value = json.loads(result.content[0].text)
                if name == "get_quote":
                    assert value["total_jpy"] == 4150 and value["is_binding"] is False
                if name == "get_product" and arguments["sku"] == "tea-001":
                    assert value["product"]["is_demo"] and value["product"]["source_url"] and value["product"]["updated_at"]
                if name == "get_product" and arguments["sku"] == "missing":
                    assert value["found"] is False
                evidence["mcp"].append({"tool": name, "arguments": arguments, "result": value})
            assert (await session.call_tool("get_quote", {"sku": "tea-001", "quantity": 0})).isError
    evidence["result"] = "passed; Muse account connection not covered"
    target = Path("artifacts/public-demo-acceptance.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Public HTTPS + seven MCP tools passed. Evidence: {target}")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=120))
