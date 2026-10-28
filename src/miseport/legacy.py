"""Explicit adapter for recovered version-1.0 merchant snapshots."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator
from .core import Catalog, Product


class Merchant(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=500)
    homepage: str = Field(max_length=2048)

    @field_validator("homepage")
    @classmethod
    def valid_homepage(cls, value):
        return Product.public_link(value)


class LegacyProduct(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=128)
    merchant_id: str = Field(min_length=1, max_length=128)
    name_ja: str = Field(min_length=1, max_length=500)
    description_ja: str = Field(max_length=10000)
    product_url: str
    price_jpy: StrictInt = Field(ge=0)
    tax_included: StrictBool
    stock: StrictInt | None = Field(default=None, ge=0)
    shipping_jpy: StrictInt | None = Field(default=None, ge=0)
    gift_wrapping: StrictBool | None = None
    origin_prefecture: str | None = None
    caffeine_level: str | None = None
    image_url: str | None = None
    evidence_url: str
    updated_at: datetime


class LegacyDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    demo_only: StrictBool
    snapshot_at: datetime
    merchant: Merchant
    products: list[LegacyProduct] = Field(max_length=10000)

    @field_validator("snapshot_at")
    @classmethod
    def aware(cls, value):
        return Product.aware_time(value)


class CanonicalMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_format: Literal["legacy-1.0"]
    snapshot_at: datetime
    merchant: Merchant
    demo_only: StrictBool

    @field_validator("snapshot_at")
    @classmethod
    def aware(cls, value):
        return Product.aware_time(value)


class CanonicalDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["miseport/1.1"]
    metadata: CanonicalMetadata
    products: list[Product] = Field(max_length=10000)


class LegacyAdapter:
    @staticmethod
    def convert(document: dict) -> Catalog:
        parsed = LegacyDocument.model_validate(document)
        products = []
        for old in parsed.products:
            if old.merchant_id != parsed.merchant.id:
                raise ValueError("product merchant_id must match merchant.id")
            products.append(Product(
                sku=old.id, name=old.name_ja, description=old.description_ja,
                price_jpy=old.price_jpy, tax_included=old.tax_included,
                stock="unknown" if old.stock is None else "in_stock" if old.stock else "out_of_stock",
                stock_quantity=old.stock, shipping_jpy=old.shipping_jpy,
                source_url=old.product_url, evidence_url=old.evidence_url, image_url=old.image_url,
                updated_at=old.updated_at, snapshot_at=parsed.snapshot_at,
                is_demo=parsed.demo_only, merchant_id=parsed.merchant.id,
                merchant_name=parsed.merchant.name, merchant_homepage=parsed.merchant.homepage,
                gift_wrapping=old.gift_wrapping, origin_prefecture=old.origin_prefecture,
                caffeine_level=old.caffeine_level))
        return Catalog(products, {"source_format": "legacy-1.0",
            "snapshot_at": parsed.snapshot_at.isoformat(), "merchant": parsed.merchant.model_dump(),
            "demo_only": parsed.demo_only})


def canonical_catalog(document: dict) -> Catalog:
    parsed = CanonicalDocument.model_validate(document)
    meta = parsed.metadata
    for product in parsed.products:
        if (product.merchant_id != meta.merchant.id or product.merchant_name != meta.merchant.name
                or product.merchant_homepage != meta.merchant.homepage
                or product.is_demo != meta.demo_only or product.snapshot_at != meta.snapshot_at):
            raise ValueError("product metadata must match catalog metadata")
    return Catalog(parsed.products, meta.model_dump(mode="json"))
