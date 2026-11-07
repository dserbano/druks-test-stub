from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import (
    MovementKind,
    POStatus,
    PurchaseOrder,
    StockMovement,
)
from .stock import _get_or_create_level


class POError(ValueError):
    pass


_ALLOWED = {
    POStatus.DRAFT: {POStatus.PLACED, POStatus.CANCELLED},
    POStatus.PLACED: {POStatus.RECEIVED, POStatus.CANCELLED},
    POStatus.RECEIVED: set(),
    POStatus.CANCELLED: set(),
}


def transition(db: Session, po: PurchaseOrder, new_status: POStatus) -> PurchaseOrder:
    current = po.status
    if new_status == current:
        return po
    if new_status not in _ALLOWED[current]:
        raise POError(f"cannot transition {current.value} -> {new_status.value}")

    try:
        if new_status == POStatus.RECEIVED:
            if not po.lines:
                raise POError("cannot receive a PO with no lines")
            for line in po.lines:
                level = _get_or_create_level(db, line.product_id, po.warehouse_id)
                level.on_hand += line.quantity
                movement = StockMovement(
                    product_id=line.product_id,
                    warehouse_id=po.warehouse_id,
                    kind=MovementKind.IN,
                    quantity=line.quantity,
                    reference=f"PO:{po.id}",
                )
                db.add(movement)
            po.received_at = datetime.now(timezone.utc)

        po.status = new_status
        db.commit()
        db.refresh(po)
        return po
    except Exception:
        db.rollback()
        raise
