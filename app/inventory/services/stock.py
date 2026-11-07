from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    MovementKind,
    Product,
    StockLevel,
    StockMovement,
    Warehouse,
)


class StockError(ValueError):
    pass


def _get_or_create_level(db: Session, product_id: int, warehouse_id: int) -> StockLevel:
    level = db.execute(
        select(StockLevel).where(
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
        )
    ).scalar_one_or_none()
    if level is None:
        level = StockLevel(product_id=product_id, warehouse_id=warehouse_id, on_hand=0)
        db.add(level)
        db.flush()
    return level


def post_movement(
    db: Session,
    *,
    product_id: int,
    warehouse_id: int,
    kind: MovementKind,
    quantity: int,
    dest_warehouse_id: int | None = None,
    reference: str | None = None,
) -> StockMovement:
    if quantity <= 0:
        raise StockError("quantity must be positive")

    product = db.get(Product, product_id)
    if product is None:
        raise StockError(f"product {product_id} not found")
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise StockError(f"warehouse {warehouse_id} not found")

    if kind == MovementKind.TRANSFER:
        if dest_warehouse_id is None:
            raise StockError("transfer requires dest_warehouse_id")
        if dest_warehouse_id == warehouse_id:
            raise StockError("transfer source and destination must differ")
        dest = db.get(Warehouse, dest_warehouse_id)
        if dest is None:
            raise StockError(f"dest warehouse {dest_warehouse_id} not found")
    else:
        if dest_warehouse_id is not None:
            raise StockError("dest_warehouse_id only valid for transfer")

    # All reads + writes in a single transaction (the Session). Commit once.
    try:
        src_level = _get_or_create_level(db, product_id, warehouse_id)

        if kind == MovementKind.IN:
            src_level.on_hand += quantity
        elif kind == MovementKind.OUT:
            if src_level.on_hand < quantity:
                raise StockError("insufficient stock")
            src_level.on_hand -= quantity
        elif kind == MovementKind.TRANSFER:
            if src_level.on_hand < quantity:
                raise StockError("insufficient stock")
            src_level.on_hand -= quantity
            dest_level = _get_or_create_level(db, product_id, dest_warehouse_id)  # type: ignore[arg-type]
            dest_level.on_hand += quantity

        movement = StockMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            dest_warehouse_id=dest_warehouse_id,
            kind=kind,
            quantity=quantity,
            reference=reference,
        )
        db.add(movement)
        db.commit()
        db.refresh(movement)
        return movement
    except Exception:
        db.rollback()
        raise


def low_stock_products(db: Session, warehouse_id: int | None = None) -> list[dict]:
    products = db.execute(select(Product)).scalars().all()
    alerts: list[dict] = []
    for product in products:
        levels_q = select(StockLevel).where(StockLevel.product_id == product.id)
        if warehouse_id is not None:
            levels_q = levels_q.where(StockLevel.warehouse_id == warehouse_id)
        levels = db.execute(levels_q).scalars().all()
        on_hand = sum(level.on_hand for level in levels)
        if on_hand <= product.reorder_point:
            alerts.append(
                {
                    "product_id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "on_hand": on_hand,
                    "reorder_point": product.reorder_point,
                }
            )
    return alerts
