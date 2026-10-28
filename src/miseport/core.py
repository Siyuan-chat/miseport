"""Validated catalog model and deterministic Japanese substring search."""
from datetime import datetime
from enum import Enum
import unicodedata
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator, model_validator


class Stock(str, Enum):
    in_stock = "in_stock"
    out_of_stock = "out_of_stock"
    unknown = "unknown"


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sku: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    category: str = Field(default="", max_length=200)
    price_jpy: StrictInt = Field(ge=0)
    currency: str = "JPY"
    stock: Stock = Stock.unknown
    source_url: str = Field(max_length=2048)
    updated_at: datetime
    is_demo: StrictBool
    tax_included: StrictBool | None = None
    shipping_jpy: StrictInt | None = Field(default=None, ge=0)
    stock_quantity: StrictInt | None = Field(default=None, ge=0)
    merchant_id: str | None = Field(default=None, min_length=1, max_length=128)
    merchant_name: str | None = Field(default=None, min_length=1, max_length=500)
    merchant_homepage: str | None = Field(default=None, max_length=2048)
    evidence_url: str | None = Field(default=None, max_length=2048)
    image_url: str | None = Field(default=None, max_length=2048)
    gift_wrapping: StrictBool | None = None
    origin_prefecture: str | None = Field(default=None, min_length=1, max_length=200)
    caffeine_level: str | None = Field(default=None, min_length=1, max_length=500)
    snapshot_at: datetime | None = None

    @field_validator("currency")
    @classmethod
    def jpy_only(cls, value: str) -> str:
        if value != "JPY":
            raise ValueError("only JPY is supported")
        return value

    @field_validator("source_url")
    @classmethod
    def public_link(cls, value: str) -> str:
        try:
            parts = urlsplit(value)
            _ = parts.port
        except ValueError as exc:
            raise ValueError("invalid source URL") from exc
        if (parts.scheme not in {"https", "http"} or not parts.hostname
                or parts.username or parts.password or any(c.isspace() for c in value)
                or any(ord(c) < 32 for c in value) or "\\" in value):
            raise ValueError("source_url must be an absolute HTTP(S) URL without credentials")
        return value

    @field_validator("merchant_homepage", "evidence_url", "image_url")
    @classmethod
    def optional_link(cls, value: str | None) -> str | None:
        return None if value is None else cls.public_link(value)

    @field_validator("updated_at", "snapshot_at")
    @classmethod
    def aware_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def consistent_stock(self):
        if self.stock_quantity is not None:
            expected = Stock.in_stock if self.stock_quantity > 0 else Stock.out_of_stock
            if self.stock != expected:
                raise ValueError("stock_quantity contradicts stock status")
        return self


def normalize(text: str) -> str:
    """NFKC + casefold + katakana-to-hiragana; no semantic inference."""
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


class Catalog:
    def __init__(self, products: list[Product], metadata: dict | None = None):
        self.products = products
        self.metadata = metadata or {}
        self.by_sku: dict[str, Product] = {}
        for product in products:
            if product.sku in self.by_sku:
                raise ValueError(f"duplicate SKU: {product.sku}")
            self.by_sku[product.sku] = product

    def detail(self, sku: str) -> dict:
        product = self.by_sku.get(sku)
        return {"product": product.model_dump(mode="json") if product else None,
                "found": product is not None}

    def inventory(self, sku: str) -> dict:
        from .commerce import inventory
        return inventory(self, sku)

    def quote(self, sku: str, quantity: int = 1) -> dict:
        from .commerce import quote
        return quote(self, sku, quantity)

    def audit(self) -> dict:
        from .commerce import audit
        return audit(self)

    def jsonld(self, sku: str) -> dict:
        from .commerce import jsonld
        return jsonld(self, sku)

    def search(self, query: str = "", category: str | None = None,
               min_price_jpy: int | None = None, max_price_jpy: int | None = None,
               in_stock_only: bool = False, limit: int = 20, offset: int = 0,
               gift_wrapping: bool | None = None, origin_prefecture: str | None = None) -> dict:
        if type(query) is not str or (category is not None and type(category) is not str):
            raise ValueError("query and category must be text")
        if type(in_stock_only) is not bool or (gift_wrapping is not None and type(gift_wrapping) is not bool):
            raise ValueError("stock/gift filters must be booleans")
        if origin_prefecture is not None and (type(origin_prefecture) is not str or len(origin_prefecture) > 200):
            raise ValueError("origin_prefecture must be text at most 200 characters")
        if (len(query) > 500 or type(limit) is not int or type(offset) is not int
                or not 1 <= limit <= 100 or offset < 0):
            raise ValueError("query max 500 chars; limit 1..100; offset >= 0")
        if any(v is not None and (type(v) is not int or v < 0)
               for v in (min_price_jpy, max_price_jpy)):
            raise ValueError("prices must be nonnegative integer JPY")
        if min_price_jpy is not None and max_price_jpy is not None and min_price_jpy > max_price_jpy:
            raise ValueError("min price exceeds max price")
        terms = normalize(query).split()
        matches = []
        for product in self.products:
            haystack = normalize(" ".join([product.name, product.description, product.category,
                                           product.sku, product.origin_prefecture or "",
                                           product.caffeine_level or ""]))
            if not all(term in haystack for term in terms):
                continue
            if category is not None and normalize(category) != normalize(product.category):
                continue
            if min_price_jpy is not None and product.price_jpy < min_price_jpy:
                continue
            if max_price_jpy is not None and product.price_jpy > max_price_jpy:
                continue
            if in_stock_only and product.stock != Stock.in_stock:
                continue
            if gift_wrapping is not None and product.gift_wrapping is not gift_wrapping:
                continue
            if origin_prefecture is not None and normalize(product.origin_prefecture or "") != normalize(origin_prefecture):
                continue
            matches.append(product)
        matches.sort(key=lambda p: (p.price_jpy, p.sku))
        return {"products": [p.model_dump(mode="json") for p in matches[offset:offset + limit]],
                "total": len(matches), "offset": offset, "limit": limit}
