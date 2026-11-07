from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import LowStockAlert
from ..services.stock import low_stock_products

router = APIRouter(prefix="/low-stock-alerts", tags=["alerts"])


@router.get("", response_model=list[LowStockAlert])
def list_low_stock_alerts(
    warehouse_id: int | None = None, db: Session = Depends(get_db)
):
    return low_stock_products(db, warehouse_id=warehouse_id)
