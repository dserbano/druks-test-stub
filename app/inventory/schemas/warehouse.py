from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WarehouseBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    location: str | None = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = None


class WarehouseRead(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
