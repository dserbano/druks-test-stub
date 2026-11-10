from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .db import get_session
from .models import Product
from .schemas import ProductOut

router = APIRouter()


@router.get("/products", response_model=list[ProductOut])
def list_products(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[Product]:
    stmt = (
        select(Product)
        .options(selectinload(Product.variants))
        .order_by(Product.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.execute(stmt).scalars().all())


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, session: Session = Depends(get_session)) -> Product:
    stmt = (
        select(Product)
        .options(selectinload(Product.variants))
        .where(Product.id == product_id)
    )
    product = session.execute(stmt).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
