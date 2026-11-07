from __future__ import annotations

from fastapi import FastAPI

from .db import engine, init_db
from .routers import (
    alerts,
    csv_router,
    products,
    purchase_orders,
    stock_movements,
    suppliers,
    warehouses,
)


def create_app(*, db_engine=None, init: bool = True) -> FastAPI:
    app = FastAPI(title="Inventory Management")
    if init:
        init_db(bind=db_engine or engine)
    app.include_router(products.router)
    app.include_router(suppliers.router)
    app.include_router(warehouses.router)
    app.include_router(stock_movements.router)
    app.include_router(purchase_orders.router)
    app.include_router(alerts.router)
    app.include_router(csv_router.router)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    return app


