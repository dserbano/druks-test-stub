from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.purchase_order import POStatus


class PurchaseOrderLineCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: float = Field(default=0.0, ge=0)


class PurchaseOrderLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    unit_price: float


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    lines: list[PurchaseOrderLineCreate] = Field(default_factory=list)


class PurchaseOrderUpdate(BaseModel):
    supplier_id: int | None = None
    warehouse_id: int | None = None
    status: POStatus | None = None
    lines: list[PurchaseOrderLineCreate] | None = None


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_id: int
    warehouse_id: int
    status: POStatus
    created_at: datetime
    received_at: datetime | None
    lines: list[PurchaseOrderLineRead]
