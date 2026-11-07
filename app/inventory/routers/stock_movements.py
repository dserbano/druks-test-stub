from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MovementKind, StockMovement
from ..schemas import StockMovementCreate, StockMovementRead
from ..schemas.common import Page
from ..services.stock import StockError, post_movement

router = APIRouter(prefix="/stock-movements", tags=["stock-movements"])


@router.get("", response_model=Page[StockMovementRead])
def list_stock_movements(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    product_id: int | None = None,
    warehouse_id: int | None = None,
    kind: MovementKind | None = None,
    db: Session = Depends(get_db),
):
    q = select(StockMovement)
    if product_id is not None:
        q = q.where(StockMovement.product_id == product_id)
    if warehouse_id is not None:
        q = q.where(StockMovement.warehouse_id == warehouse_id)
    if kind is not None:
        q = q.where(StockMovement.kind == kind)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()
    items = (
        db.execute(q.order_by(StockMovement.id).offset(skip).limit(limit))
        .scalars()
        .all()
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("", response_model=StockMovementRead, status_code=201)
def create_stock_movement(
    payload: StockMovementCreate, db: Session = Depends(get_db)
):
    try:
        return post_movement(
            db,
            product_id=payload.product_id,
            warehouse_id=payload.warehouse_id,
            kind=payload.kind,
            quantity=payload.quantity,
            dest_warehouse_id=payload.dest_warehouse_id,
            reference=payload.reference,
        )
    except StockError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{movement_id}", response_model=StockMovementRead)
def get_stock_movement(movement_id: int, db: Session = Depends(get_db)):
    movement = db.get(StockMovement, movement_id)
    if movement is None:
        raise HTTPException(status_code=404, detail="movement not found")
    return movement
