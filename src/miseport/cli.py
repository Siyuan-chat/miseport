"""JSON output for scripts; diagnostics use stderr and exit code 2."""
import argparse
import json
import os
import sys
from .importers import load_catalog, save_catalog


def emit(value, stream=sys.stdout):
    print(json.dumps(value, ensure_ascii=False, indent=2), file=stream)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="miseport")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("input")
    ingest = commands.add_parser("import")
    ingest.add_argument("input")
    ingest.add_argument("--output", required=True)
    for name in ("search", "detail", "inventory", "quote", "audit", "export-jsonld"):
        sub = commands.add_parser(name)
        if name != "audit":
            sub.add_argument("query" if name == "search" else "sku")
        sub.add_argument("--catalog", default=os.environ.get("MISEPORT_CATALOG"))
        if name == "quote":
            sub.add_argument("--quantity", type=int, default=1)
        if name == "search":
            sub.add_argument("--category")
            sub.add_argument("--min-price-jpy", type=int)
            sub.add_argument("--max-price-jpy", type=int)
            sub.add_argument("--in-stock-only", action="store_true")
            sub.add_argument("--limit", type=int, default=20)
            sub.add_argument("--offset", type=int, default=0)
            sub.add_argument("--gift-wrapping", choices=("true", "false"))
            sub.add_argument("--origin-prefecture")
    args = parser.parse_args(argv)
    try:
        path = args.input if args.command in {"validate", "import"} else args.catalog
        if not path:
            raise ValueError("provide --catalog or MISEPORT_CATALOG")
        catalog = load_catalog(path)
        if args.command in {"validate", "import"}:
            if args.command == "import":
                save_catalog(catalog, args.output)
            emit({"valid": True, "count": len(catalog.products)})
        elif args.command == "detail":
            emit(catalog.detail(args.sku))
        elif args.command == "inventory":
            emit(catalog.inventory(args.sku))
        elif args.command == "quote":
            emit(catalog.quote(args.sku, args.quantity))
        elif args.command == "audit":
            emit(catalog.audit())
        elif args.command == "export-jsonld":
            emit(catalog.jsonld(args.sku))
        else:
            emit(catalog.search(args.query, args.category, args.min_price_jpy,
                                args.max_price_jpy, args.in_stock_only, args.limit, args.offset,
                                None if args.gift_wrapping is None else args.gift_wrapping == "true",
                                args.origin_prefecture))
        return 0
    except (ValueError, OSError) as exc:
        emit({"error": str(exc)}, sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
