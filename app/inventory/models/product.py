from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True, index=True
    )

    supplier: Mapped["Supplier | None"] = relationship(back_populates="products")  # type: ignore[name-defined]  # noqa: F821
    stock_levels: Mapped[list["StockLevel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="product", cascade="all, delete-orphan"
    )
