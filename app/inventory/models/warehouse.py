from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)

    stock_levels: Mapped[list["StockLevel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="warehouse", cascade="all, delete-orphan"
    )
