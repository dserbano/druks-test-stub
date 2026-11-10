from __future__ import annotations

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.shop.db import Base, get_session
from app.shop.main import create_app
from app.shop.models import Product
from app.shop.schemas import ProductOut, VariantOut


_name = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_categories=("Cs",)),
    min_size=1,
    max_size=50,
)
_sku = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=32,
).filter(lambda s: s.strip() == s and len(s) > 0)


@given(
    name=_name,
    description=st.text(max_size=200),
    variants=st.lists(
        st.fixed_dictionaries(
            {
                "sku": _sku,
                "price_cents": st.integers(min_value=0, max_value=10**9),
                "stock": st.integers(min_value=0, max_value=10**6),
            }
        ),
        min_size=0,
        max_size=5,
        unique_by=lambda d: d["sku"],
    ),
)
def test_product_schema_round_trip(name, description, variants):
    payload = {
        "id": 1,
        "name": name,
        "description": description,
        "variants": [{"id": i + 1, **v} for i, v in enumerate(variants)],
    }
    model = ProductOut.model_validate(payload)
    assert model.model_dump() == payload


@given(
    products=st.lists(
        st.fixed_dictionaries({"name": _name}),
        min_size=0,
        max_size=10,
    ),
)
@settings(max_examples=25, deadline=None)
def test_list_endpoint_returns_seeded_products(products):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with factory() as seed:
        for p in products:
            seed.add(Product(name=p["name"]))
        seed.commit()

    app = create_app()

    def _override():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = _override
    try:
        with TestClient(app) as c:
            body = c.get("/products", params={"limit": 500}).json()
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()

    assert len(body) == len(products)
    assert [p["name"] for p in body] == [p["name"] for p in products]


@given(
    price=st.integers(min_value=0, max_value=10**9),
    stock=st.integers(min_value=0, max_value=10**6),
    sku=_sku,
)
def test_variant_schema_round_trip(price, stock, sku):
    payload = {"id": 1, "sku": sku, "price_cents": price, "stock": stock}
    assert VariantOut.model_validate(payload).model_dump() == payload
