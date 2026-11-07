from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import POStatus, PurchaseOrder, PurchaseOrderLine
from ..schemas import (
    PurchaseOrderCreate,
    PurchaseOrderRead,
    PurchaseOrderUpdate,
)
from ..schemas.common import Page
from ..services.purchase_order import POError, transition

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


@router.get("", response_model=Page[PurchaseOrderRead])
def list_purchase_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status: POStatus | None = None,
    supplier_id: int | None = None,
    warehouse_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = select(PurchaseOrder)
    if status is not None:
        q = q.where(PurchaseOrder.status == status)
    if supplier_id is not None:
        q = q.where(PurchaseOrder.supplier_id == supplier_id)
    if warehouse_id is not None:
        q = q.where(PurchaseOrder.warehouse_id == warehouse_id)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()
    items = (
        db.execute(q.order_by(PurchaseOrder.id).offset(skip).limit(limit))
        .scalars()
        .all()
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("", response_model=PurchaseOrderRead, status_code=201)
def create_purchase_order(
    payload: PurchaseOrderCreate, db: Session = Depends(get_db)
):
    po = PurchaseOrder(
        supplier_id=payload.supplier_id,
        warehouse_id=payload.warehouse_id,
        status=POStatus.DRAFT,
    )
    for line in payload.lines:
        po.lines.append(
            PurchaseOrderLine(
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
            )
        )
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.get("/{po_id}", response_model=PurchaseOrderRead)
def get_purchase_order(po_id: int, db: Session = Depends(get_db)):
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="purchase order not found")
    return po


@router.put("/{po_id}", response_model=PurchaseOrderRead)
def update_purchase_order(
    po_id: int, payload: PurchaseOrderUpdate, db: Session = Depends(get_db)
):
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="purchase order not found")

    data = payload.model_dump(exclude_unset=True)
    new_status = data.pop("status", None)
    lines = data.pop("lines", None)

    if po.status != POStatus.DRAFT and (data or lines is not None):
        raise HTTPException(
            status_code=400,
            detail="can only edit fields of a draft purchase order",
        )

    for key, value in data.items():
        setattr(po, key, value)

    if lines is not None:
        po.lines.clear()
        for line in lines:
            po.lines.append(
                PurchaseOrderLine(
                    product_id=line["product_id"],
                    quantity=line["quantity"],
                    unit_price=line.get("unit_price", 0.0),
                )
            )

    db.commit()

    if new_status is not None and new_status != po.status:
        try:
            po = transition(db, po, POStatus(new_status))
        except POError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    db.refresh(po)
    return po


@router.post("/{po_id}/receive", response_model=PurchaseOrderRead)
def receive_purchase_order(po_id: int, db: Session = Depends(get_db)):
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="purchase order not found")
    if po.status == POStatus.DRAFT:
        try:
            po = transition(db, po, POStatus.PLACED)
        except POError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    try:
        po = transition(db, po, POStatus.RECEIVED)
    except POError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return po


@router.delete("/{po_id}", status_code=204)
def delete_purchase_order(po_id: int, db: Session = Depends(get_db)):
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="purchase order not found")
    if po.status != POStatus.DRAFT:
        raise HTTPException(
            status_code=400, detail="only draft purchase orders can be deleted"
        )
    db.delete(po)
    db.commit()
    return None
