import asyncio
import json
import os
from pathlib import Path
import sysconfig
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def test_real_stdio_protocol():
    async def exercise():
        entry = Path(sysconfig.get_path("scripts")) / ("miseport-mcp.exe" if os.name == "nt" else "miseport-mcp")
        parameters = StdioServerParameters(command=str(entry), args=[],
            env={**os.environ, "MISEPORT_CATALOG": str(ROOT / "examples/products.json")})
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=10)) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {t.name for t in tools.tools} == {
                    "about_miseport", "search_products", "get_product", "check_inventory",
                    "get_quote", "audit_catalog", "export_product_jsonld"}
                assert all(t.annotations.readOnlyHint for t in tools.tools)
                async def call(name, arguments):
                    result = await session.call_tool(name, arguments)
                    assert not result.isError, result
                    return json.loads(result.content[0].text)
                about = await call("about_miseport", {})
                assert about["read_only"] and about["demo_product_count"] == 4
                result = await call("search_products", {"query": "こーひー", "in_stock_only": True})
                assert result["total"] == 1
                product = result["products"][0]
                assert product["currency"] == "JPY" and product["is_demo"]
                assert product["source_url"].startswith("https://") and product["updated_at"]
                assert (await call("get_product", {"sku": "tea-002"}))["product"]["stock"] == "unknown"
                assert (await call("search_products", {"query": "該当なし"}))["products"] == []
                assert not (await call("get_product", {"sku": "missing"}))["found"]
                inventory = await call("check_inventory", {"sku": "coffee-001"})
                assert inventory["found"] and inventory["stock_is_live"] is False
                quote = await call("get_quote", {"sku": "coffee-001", "quantity": 2})
                assert quote["quantity"] == 2 and quote["subtotal_jpy"] == 2960
                assert quote["is_binding"] is False and quote["stock_is_live"] is False
                audit = await call("audit_catalog", {})
                assert audit["product_count"] == 4 and audit["demo_product_count"] == 4
                jsonld = await call("export_product_jsonld", {"sku": "coffee-001"})
                assert jsonld["jsonld"]["@type"] == "Product"
                assert (await call("check_inventory", {"sku": "missing"})) == {
                    "found": False, "product_id": "missing"}
                assert (await call("get_quote", {"sku": "missing"}))["found"] is False
                for quantity in (True, 1.0, "2", 0, 1001):
                    assert (await session.call_tool("get_quote", {
                        "sku": "coffee-001", "quantity": quantity})).isError
                bad = await session.call_tool("search_products", {"limit": 101})
                assert bad.isError
                for arguments in ({"limit": True}, {"min_price_jpy": 1.0},
                                  {"min_price_jpy": "1480"}, {"in_stock_only": "true"}):
                    assert (await session.call_tool("search_products", arguments)).isError
                unknown = await session.call_tool("nonexistent", {})
                assert unknown.isError
    asyncio.run(asyncio.wait_for(exercise(), timeout=30))
