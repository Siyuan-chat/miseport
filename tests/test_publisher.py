"""Merchant-owned publication ZIP tests. All products and hosts are fictional."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

from miseport.core import Catalog, Product
from miseport.publisher import PublicationError, build_merchant_zip


def catalog(**changed):
    data = dict(
        sku="base-1", name="京都のお茶", price_jpy=1850, stock="in_stock",
        stock_quantity=2, source_url="https://shop.example.org/items/1",
        updated_at="2026-10-29T00:00:00Z",
        snapshot_at=datetime(2026, 10, 29, tzinfo=timezone.utc),
        is_demo=True, tax_included=True, shipping_jpy=None,
        merchant_id="tea-shop", merchant_name="お茶の商店",
        merchant_homepage="https://shop.example.org/",
    )
    data.update(changed)
    return Catalog([Product(**data)])


def archive(tmp_path, cat=None, approved=True, demo=True, origin="https://tea.pages.dev"):
    out=tmp_path / "public.zip"
    data=build_merchant_zip(cat or catalog(), out, origin=origin,
                            merchant_approved=approved, demo_mode=demo)
    return out,data


def test_publication_package_has_separate_read_only_worker_and_no_internal_docs(tmp_path):
    path, manifest=archive(tmp_path)
    assert manifest["demo_only"] and manifest["product_count"] == 1
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist())
        assert {"_worker.js","index.html","catalog.json","manifest.json",
                "sitemap.xml","robots.txt","README.txt"} == names
        assert not any("docs/" in x or "PROJECT_STATUS" in x or "references" in x for x in names)
        worker=z.read("_worker.js").decode()
        assert "tea.pages.dev" in worker and "MisePort" in worker
        assert "__MISEPORT_DATA__" not in worker and "__MISEPORT_HOST__" not in worker
        assert "Bearer" not in worker and "PAT" not in worker
        for row in manifest["files"]:
            from hashlib import sha256
            assert sha256(z.read(row["path"])).hexdigest() == row["sha256"]
        assert "お茶の商店" in z.read("index.html").decode()
        contents=json.loads(z.read("catalog.json"))
        assert contents["metadata"]["merchant"]["id"] == "tea-shop"
        assert contents["products"][0]["is_demo"] is True


def test_publication_is_explicitly_approved_and_separates_real_from_demo(tmp_path):
    with pytest.raises(PublicationError, match="確認"):
        archive(tmp_path,approved=False)
    with pytest.raises(PublicationError,match="混ぜ"):
        archive(tmp_path,demo=False)
    real=catalog(is_demo=False)
    out, manifest=archive(tmp_path,cat=real,demo=False)
    assert manifest["demo_only"] is False
    assert out.exists()


def test_bad_origin_and_nonmerchant_catalog_blocked(tmp_path):
    for origin in ("http://tea.pages.dev","https://tea.pages.dev/path",
                   "https://user:pass@tea.pages.dev","https://tea.pages.dev:8080"):
        with pytest.raises(PublicationError):
            archive(tmp_path,origin=origin)
    with pytest.raises(PublicationError,match="店舗"):
        archive(tmp_path,cat=catalog(merchant_id=None))


def test_cannot_publish_http_product_source_or_secret_text(tmp_path):
    with pytest.raises(PublicationError,match="商品URL"):
        archive(tmp_path,cat=catalog(source_url="http://shop.example.org/items/1"))
    with pytest.raises(PublicationError,match="機密"):
        archive(tmp_path,cat=catalog(description="api_key="+"X"*40))


def test_failed_publication_does_not_replace_existing_bundle(tmp_path):
    bundle=tmp_path/"public.zip"
    bundle.write_bytes(b"keep existing good snapshot")
    with pytest.raises(PublicationError):
        build_merchant_zip(catalog(),bundle,origin="https://tea.pages.dev",merchant_approved=False,demo_mode=True)
    assert bundle.read_bytes()==b"keep existing good snapshot"


@pytest.mark.skipif(not shutil.which("node"),reason="Node unavailable")
def test_generated_worker_real_initialize_tool_calls_and_host_origin(tmp_path):
    path,_=archive(tmp_path)
    with zipfile.ZipFile(path) as z:
        worker=tmp_path/"deployed.mjs"
        worker.write_bytes(z.read("_worker.js"))
    code=r'''
import assert from "node:assert/strict";
const {default:worker} = await import(process.argv[1]);
const headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"};
async function rpc(id,method,params={}) {
  const response=await worker.fetch(new Request("https://tea.pages.dev/mcp",
    {method:"POST",headers,body:JSON.stringify({jsonrpc:"2.0",id,method,params})}),{});
  assert.equal(response.status,200);
  return await response.json();
}
let hello=await rpc(1,"initialize",{protocolVersion:"2025-11-25",capabilities:{},
  clientInfo:{name:"test",version:"1"}});
assert.equal(hello.result.serverInfo.name,"MisePort Merchant");
const tools=(await rpc(2,"tools/list")).result.tools;
assert.equal(tools.length,7);
const search=(await rpc(3,"tools/call",{name:"search_products",arguments:{query:"京都"}}))
  .result.structuredContent;
assert.equal(search.total,1);
const product=(await rpc(4,"tools/call",{name:"get_product",arguments:{sku:"base-1"}}))
  .result.structuredContent;
assert.equal(product.found,true);
const quote=(await rpc(5,"tools/call",{name:"get_quote",arguments:{sku:"base-1",quantity:2}}))
  .result.structuredContent;
assert.equal(quote.total_jpy,null);
assert.equal(quote.can_purchase,false);
const jsonld=(await rpc(6,"tools/call",{name:"export_product_jsonld",arguments:{sku:"base-1"}}))
  .result.structuredContent;
assert.equal(jsonld.jsonld["@type"],"Product");
const invalid=await worker.fetch(new Request("https://other.pages.dev/healthz"),{});
assert.equal(invalid.status,403);
const rejected=await worker.fetch(new Request("https://tea.pages.dev/mcp",{
  method:"POST",headers:{...headers,Origin:"https://evil.example"},
  body:JSON.stringify({jsonrpc:"2.0",id:7,method:"tools/list"})}),{});
assert.equal(rejected.status,403);
const noGet=await worker.fetch(new Request("https://tea.pages.dev/mcp"),{});
assert.equal(noGet.status,405);
console.log("MisePort merchant prototype MCP/REST: initialize, list, call, quote, JSON-LD, Origin/Host OK");
'''
    result=subprocess.run(["node","--input-type=module","-e",code,worker.as_uri()],
        capture_output=True,text=True,timeout=15)
    assert result.returncode==0, result.stderr
    assert "MisePort merchant prototype" in result.stdout
