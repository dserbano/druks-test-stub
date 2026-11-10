from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.shop import db as shop_db
from app.shop.db import Base, get_session
from app.shop.main import create_app
from app.shop.models import Product, Variant


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture()
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    s = session_factory()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app = create_app()

    def _override() -> Iterator[Session]:
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def make_product(session: Session):
    def _make(
        name: str = "Widget",
        description: str = "",
        variants: list[dict] | None = None,
    ) -> Product:
        product = Product(name=name, description=description)
        for v in variants or []:
            product.variants.append(
                Variant(
                    sku=v["sku"],
                    price_cents=v["price_cents"],
                    stock=v.get("stock", 0),
                )
            )
        session.add(product)
        session.commit()
        session.refresh(product)
        return product

    return _make


@pytest.fixture()
def make_variant(session: Session):
    def _make(product: Product, sku: str, price_cents: int = 100, stock: int = 0) -> Variant:
        variant = Variant(product=product, sku=sku, price_cents=price_cents, stock=stock)
        session.add(variant)
        session.commit()
        session.refresh(variant)
        return variant

    return _make


@pytest.fixture(autouse=True)
def _reset_default_db_singleton() -> Iterator[None]:
    saved_engine = shop_db._engine
    saved_factory = shop_db._SessionLocal
    shop_db._engine = None
    shop_db._SessionLocal = None
    yield
    shop_db._engine = saved_engine
    shop_db._SessionLocal = saved_factory
