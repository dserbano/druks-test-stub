from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Warehouse
from ..schemas import WarehouseCreate, WarehouseRead, WarehouseUpdate
from ..schemas.common import Page

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.get("", response_model=Page[WarehouseRead])
def list_warehouses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    name: str | None = None,
    db: Session = Depends(get_db),
):
    q = select(Warehouse)
    if name:
        q = q.where(Warehouse.name.ilike(f"%{name}%"))
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()
    items = (
        db.execute(q.order_by(Warehouse.id).offset(skip).limit(limit)).scalars().all()
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("", response_model=WarehouseRead, status_code=201)
def create_warehouse(payload: WarehouseCreate, db: Session = Depends(get_db)):
    warehouse = Warehouse(**payload.model_dump())
    db.add(warehouse)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="name already exists")
    db.refresh(warehouse)
    return warehouse


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="warehouse not found")
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseRead)
def update_warehouse(
    warehouse_id: int, payload: WarehouseUpdate, db: Session = Depends(get_db)
):
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="warehouse not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(warehouse, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="name already exists")
    db.refresh(warehouse)
    return warehouse


@router.delete("/{warehouse_id}", status_code=204)
def delete_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="warehouse not found")
    db.delete(warehouse)
    db.commit()
    return None
