from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.inventory import db as db_module
from app.inventory.db import Base, get_db
from app.inventory.main import create_app


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    # Import models so metadata is populated.
    from app.inventory import models  # noqa: F401

    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(engine, session_factory):
    application = create_app(db_engine=engine, init=False)

    def _get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = _get_db
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def supplier_factory(client):
    counter = {"n": 0}

    def _make(name: str | None = None, **extra):
        counter["n"] += 1
        payload = {"name": name or f"Supplier {counter['n']}"}
        payload.update(extra)
        resp = client.post("/suppliers", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture
def warehouse_factory(client):
    counter = {"n": 0}

    def _make(name: str | None = None, **extra):
        counter["n"] += 1
        payload = {"name": name or f"Warehouse {counter['n']}"}
        payload.update(extra)
        resp = client.post("/warehouses", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture
def product_factory(client, supplier_factory):
    counter = {"n": 0}

    def _make(sku: str | None = None, **extra):
        counter["n"] += 1
        payload = {
            "sku": sku or f"SKU-{counter['n']:04d}",
            "name": extra.pop("name", f"Product {counter['n']}"),
        }
        payload.update(extra)
        resp = client.post("/products", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make
