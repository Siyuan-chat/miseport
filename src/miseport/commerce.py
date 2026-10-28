"""Evidence-limited snapshot operations; no network, orders or payment."""
from urllib.parse import urlsplit


def _facts(product):
    return {"product_id": product.sku, "stock": product.stock.value,
            "stock_quantity": product.stock_quantity, "stock_is_live": False,
            "is_demo": product.is_demo, "source_url": product.source_url,
            "evidence_url": product.evidence_url, "updated_at": product.updated_at.isoformat(),
            "snapshot_at": product.snapshot_at.isoformat() if product.snapshot_at else None}


def inventory(catalog, sku: str) -> dict:
    product = catalog.by_sku.get(sku)
    return ({"found": True, **_facts(product)} if product
            else {"found": False, "product_id": sku})


def quote(catalog, sku: str, quantity: int = 1) -> dict:
    if type(quantity) is not int or not 1 <= quantity <= 1000:
        raise ValueError("quantity must be an integer in 1..1000")
    product = catalog.by_sku.get(sku)
    if product is None:
        return {"found": False, "product_id": sku}
    subtotal = product.price_jpy * quantity
    total = (subtotal + product.shipping_jpy
             if product.tax_included is True and product.shipping_jpy is not None else None)
    available = (product.stock_quantity >= quantity if product.stock_quantity is not None
                 else False if product.stock.value == "out_of_stock" else None)
    return {"found": True, **_facts(product), "quantity": quantity, "currency": "JPY",
            "unit_price_jpy": product.price_jpy, "subtotal_jpy": subtotal,
            "tax_included": product.tax_included, "shipping_jpy": product.shipping_jpy,
            "total_jpy": total, "complete_total": total is not None,
            "can_fulfill_snapshot": available, "is_binding": False, "can_purchase": False,
            "shipping_basis": "catalog per-order snapshot; destination not evaluated",
            "message": "Dated reference amount, not a live checkout quote or reservation."}


def audit(catalog) -> dict:
    fields = ("tax_included", "shipping_jpy", "stock", "evidence_url", "merchant_id",
              "gift_wrapping", "origin_prefecture", "caffeine_level", "image_url")
    missing = {field: [] for field in fields}
    issues = []
    for product in catalog.products:
        for field in fields:
            value = getattr(product, field)
            if value is None or (field == "stock" and value.value == "unknown"):
                missing[field].append(product.sku)
        if product.tax_included is not True:
            issues.append({"product_id": product.sku, "code": "TAX_UNRESOLVED_FOR_TOTAL"})
        if product.evidence_url and urlsplit(product.source_url).hostname != urlsplit(product.evidence_url).hostname:
            issues.append({"product_id": product.sku, "code": "DIFFERENT_EVIDENCE_HOST"})
    return {"product_count": len(catalog.products),
            "demo_product_count": sum(product.is_demo for product in catalog.products),
            "stock_is_live": False, "missing_fields": missing, "issues": issues,
            "checks": {"schema": "validated", "crawlability": "not_tested",
                       "indexing": "not_tested", "muse_discoverability": "not_tested",
                       "transactions": "not_implemented"},
            "note": "Missingness is not an AI ranking or merchant verification score."}


def jsonld(catalog, sku: str) -> dict:
    product = catalog.by_sku.get(sku)
    if product is None:
        return {"found": False, "product_id": sku, "jsonld": None}
    offer = {"@type": "Offer", "price": str(product.price_jpy), "priceCurrency": "JPY",
             "url": product.source_url}
    if product.stock.value != "unknown":
        offer["availability"] = ("https://schema.org/InStock" if product.stock.value == "in_stock"
                                  else "https://schema.org/OutOfStock")
    properties = [{"@type": "PropertyValue", "name": name, "value": value}
                  for name, value in {"is_demo": product.is_demo, "stock_is_live": False,
                                      "updated_at": product.updated_at.isoformat(),
                                      "evidence_url": product.evidence_url,
                                      "snapshot_at": product.snapshot_at.isoformat() if product.snapshot_at else None}.items()
                  if value is not None]
    data = {"@context": "https://schema.org", "@type": "Product", "sku": product.sku,
            "name": product.name, "description": product.description,
            "url": product.source_url, "offers": offer, "additionalProperty": properties}
    if product.image_url:
        data["image"] = product.image_url
    return {"found": True, "product_id": sku, "jsonld": data}
