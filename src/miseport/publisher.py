"""Prepare an owner-controlled single-merchant static + MCP/REST ZIP.

This is a prototype package builder. It does not upload, buy a domain,
change merchant products, or claim live stock or platform approval.
"""
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from importlib.resources import files
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
import zipfile

from .core import Catalog

SENSITIVE_TEXT = re.compile(
    r"(?i)(?:gh[pousr]_[a-z0-9]{30,}|AKIA[0-9A-Z]{16}|"
    r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----|"
    r"(?:access[_-]?token|client[_-]?secret|api[_-]?key)\s*[:=]\s*\S{12,})"
)
MAX_PUBLISHED_PRODUCTS = 10000


class PublicationError(ValueError):
    pass


def _json(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_merchant_zip(catalog: Catalog, destination: str | Path, *, origin: str,
                       merchant_approved: bool, demo_mode: bool = False) -> dict:
    """Build a reviewed, read-only Cloudflare Pages Advanced Mode ZIP.

    Caller must explicitly attest publication rights. For real data the Merchant
    must confirm source URLs and publication scope before calling this function.
    """
    if merchant_approved is not True:
        raise PublicationError("商品の公開範囲を商店主が確認してください。")
    parts = urlsplit(origin)
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.path or parts.query or parts.fragment or parts.port not in (None, 443)
            or origin != "https://" + parts.hostname):
        raise PublicationError("公開先はHTTPSの正確なドメインを指定してください。")
    products = catalog.products
    if not products or len(products) > MAX_PUBLISHED_PRODUCTS:
        raise PublicationError("公開できる商品の数を確認してください。")
    if type(demo_mode) is not bool:
        raise PublicationError("demo_mode must be a boolean")
    if any(p.is_demo != demo_mode for p in products):
        raise PublicationError("デモ商品と実商品を混ぜて公開できません。")
    first = products[0]
    if not first.merchant_id or not first.merchant_name or not first.merchant_homepage:
        raise PublicationError("店舗情報を確認してください。")
    if any(p.merchant_id != first.merchant_id or p.merchant_name != first.merchant_name
           or p.merchant_homepage != first.merchant_homepage for p in products):
        raise PublicationError("異なる店舗の商品を混在させないでください。")
    if any(not p.source_url.startswith("https://") or p.stock_quantity is not None
           and p.stock_quantity < 0 for p in products):
        raise PublicationError("商品URLまたは在庫を確認してください。")
    for p in products:
        if p.price_jpy > 9_007_199_254_740 or (p.shipping_jpy is not None
              and p.shipping_jpy > 9_007_199_254_740):
            raise PublicationError("金額がJSの安全な整数範囲を超えます。")
    payload = [p.model_dump(mode="json") for p in products]
    as_ld = {p.sku: catalog.jsonld(p.sku)["jsonld"] for p in products}
    stamp = datetime.now(timezone.utc).isoformat()
    meta = {
        "schema_version": "miseport/published-0.1",
        "merchant": {"id": first.merchant_id, "name": first.merchant_name,
                     "homepage": first.merchant_homepage},
        "origin": origin, "snapshot_generated_at": stamp, "demo_only": demo_mode,
        "stock_is_live": False, "checkout": False,
    }
    records = {"products": payload, "jsonld": as_ld, "snapshot_at": stamp,
               "demo_only": demo_mode}
    try:
        worker = files("miseport").joinpath("merchant_worker.js").read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        raise PublicationError("商品配信用のWorkerテンプレートが見つかりません。") from None
    if worker.count("__MISEPORT_DATA__") != 1 or worker.count("__MISEPORT_HOST__") != 1:
        raise PublicationError("Workerテンプレートが不正です。")
    compiled = worker.replace("__MISEPORT_DATA__", json.dumps(records, ensure_ascii=True))
    compiled = compiled.replace("__MISEPORT_HOST__", json.dumps(parts.hostname))
    logo = "MisePort — " + first.merchant_name
    product_rows = "".join(
        '<li><a href="' + escape(p.source_url, quote=True) + '" rel="noopener">'
        + escape(p.name) + "</a> — " + str(p.price_jpy)
        + "円 / " + escape(p.stock.value) + "</li>"
        for p in products[:250]
    )
    html = ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + escape(logo) + '</title></head><body><main><h1>'
            + escape(first.merchant_name) + '</h1><p>商品情報の記録スナップショットです。'
            '現在の在庫・送料や価格を保証しません。実購入は販売元ページでご確認ください。</p>'
            '<p><a href="' + escape(first.merchant_homepage, quote=True)
            + '" rel="noopener">ショップへ</a></p><ul>' + product_rows + '</ul>'
            '<p>商品検索 API: /api/products ｜ Agent MCP: /mcp</p></main></body></html>')
    entries = {
        "_worker.js": compiled.encode("utf-8"),
        "index.html": html.encode("utf-8"),
        "catalog.json": _json({"metadata": meta, "products": payload}),
        "robots.txt": ("User-agent: *\nAllow: /\nSitemap: " + origin + "/sitemap.xml\n").encode(),
        "sitemap.xml": ('<?xml version="1.0" encoding="UTF-8"?>'
                        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                        '<url><loc>' + escape(origin) + '/</loc></url></urlset>').encode(),
        "README.txt": ("MisePort single-merchant, read-only publication bundle.\n"
                       "Shop owner approved the public-product scope.\n"
                       "No live stock or checkout. This does not edit the original shop.\n"
                       "Deploy to the exact HTTPS origin selected during build.\n"
                       "Manual updates require a new complete ZIP.\n").encode(),
    }
    # Keep only reviewed structured data. No credential files, internal docs, logs,
    # order/customer records, raw source API responses or unapproved images.
    for name, body in entries.items():
        if SENSITIVE_TEXT.search(body.decode("utf-8", errors="replace")):
            raise PublicationError("機密情報らしい内容を検出しました: " + name)
    manifest = {"version": "merchant-bundle-0.1", **meta, "product_count": len(products),
                "files": [{"path": key, "size": len(value),
                           "sha256": sha256(value).hexdigest()}
                          for key, value in sorted(entries.items())]}
    entries["manifest.json"] = _json(manifest)
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, suffix=".tmp", delete=False) as fp:
            temp = Path(fp.name)
        with zipfile.ZipFile(temp, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, body in sorted(entries.items()):
                archive.writestr(name, body)
        os.replace(temp, dest)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
    return manifest


def main():
    import argparse
    from .importers import load_catalog
    parser = argparse.ArgumentParser(
        description="Build a read-only single-merchant publication bundle (no upload)."
    )
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--origin", required=True, help="Exact merchant-owned HTTPS origin")
    parser.add_argument("--merchant-approved", action="store_true",
                        help="Shop owner approved all product data for public delivery")
    parser.add_argument("--demo", action="store_true",
                        help="Only publish explicitly synthetic is_demo=true products")
    args = parser.parse_args()
    try:
        catalog = load_catalog(args.catalog)
        result = build_merchant_zip(catalog, args.output, origin=args.origin,
                                    merchant_approved=args.merchant_approved,
                                    demo_mode=args.demo)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output":args.output,"products":result["product_count"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
