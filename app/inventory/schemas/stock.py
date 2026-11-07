from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.stock import MovementKind


class StockLevelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    warehouse_id: int
    on_hand: int


class StockMovementCreate(BaseModel):
    product_id: int
    warehouse_id: int
    kind: MovementKind
    quantity: int = Field(gt=0)
    dest_warehouse_id: int | None = None
    reference: str | None = None


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    warehouse_id: int
    dest_warehouse_id: int | None
    kind: MovementKind
    quantity: int
    reference: str | None
    created_at: datetime


class LowStockAlert(BaseModel):
    product_id: int
    sku: str
    name: str
    on_hand: int
    reorder_point: int
