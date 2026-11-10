from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    price_cents: int
    stock: int


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    variants: list[VariantOut] = []
