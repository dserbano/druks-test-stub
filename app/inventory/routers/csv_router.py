from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..csv_io import import_rows, parse_csv, serialize_csv
from ..db import get_db
from ..models import Product, Supplier

router = APIRouter(prefix="/csv", tags=["csv"])

PRODUCT_FIELDS = ["sku", "name", "description", "price", "reorder_point", "supplier_id"]
SUPPLIER_FIELDS = ["name", "email", "phone", "address"]


def _read_text(upload: UploadFile) -> str:
    raw = upload.file.read()
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="csv must be utf-8")
    return raw


@router.get("/products/export", response_class=PlainTextResponse)
def export_products(db: Session = Depends(get_db)):
    products = db.execute(select(Product).order_by(Product.id)).scalars().all()
    rows = [{f: getattr(p, f) for f in PRODUCT_FIELDS} for p in products]
    return serialize_csv(PRODUCT_FIELDS, rows)


@router.post("/products/import")
def import_products(file: UploadFile, db: Session = Depends(get_db)):
    text = _read_text(file)
    _, rows = parse_csv(text)

    def handler(row: dict) -> None:
        sku = row["sku"].strip()
        existing = db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()
        price = float(row.get("price") or 0)
        reorder_point = int(row.get("reorder_point") or 0)
        if price < 0 or reorder_point < 0:
            raise ValueError("price and reorder_point must be non-negative")
        supplier_id_raw = (row.get("supplier_id") or "").strip()
        supplier_id = int(supplier_id_raw) if supplier_id_raw else None
        if supplier_id is not None and db.get(Supplier, supplier_id) is None:
            raise ValueError(f"supplier {supplier_id} not found")
        name = row["name"].strip()
        description = (row.get("description") or "").strip() or None
        if existing is not None:
            existing.name = name
            existing.description = description
            existing.price = price
            existing.reorder_point = reorder_point
            existing.supplier_id = supplier_id
        else:
            db.add(
                Product(
                    sku=sku,
                    name=name,
                    description=description,
                    price=price,
                    reorder_point=reorder_point,
                    supplier_id=supplier_id,
                )
            )
        db.flush()

    result = import_rows(rows, ["sku", "name"], handler)
    db.commit()
    return result.as_response()


@router.get("/suppliers/export", response_class=PlainTextResponse)
def export_suppliers(db: Session = Depends(get_db)):
    suppliers = db.execute(select(Supplier).order_by(Supplier.id)).scalars().all()
    rows = [{f: getattr(s, f) for f in SUPPLIER_FIELDS} for s in suppliers]
    return serialize_csv(SUPPLIER_FIELDS, rows)


@router.post("/suppliers/import")
def import_suppliers(file: UploadFile, db: Session = Depends(get_db)):
    text = _read_text(file)
    _, rows = parse_csv(text)

    def handler(row: dict) -> None:
        name = row["name"].strip()
        existing = db.execute(
            select(Supplier).where(Supplier.name == name)
        ).scalar_one_or_none()
        email = (row.get("email") or "").strip() or None
        phone = (row.get("phone") or "").strip() or None
        address = (row.get("address") or "").strip() or None
        if email is not None and "@" not in email:
            raise ValueError("email must contain '@'")
        if existing is not None:
            existing.email = email
            existing.phone = phone
            existing.address = address
        else:
            db.add(Supplier(name=name, email=email, phone=phone, address=address))
        db.flush()

    result = import_rows(rows, ["name"], handler)
    db.commit()
    return result.as_response()
