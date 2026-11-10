from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.shop.models import Product, Variant


def test_create_product_without_variants(session, make_product):
    product = make_product(name="Bare", description="no variants")
    assert product.id is not None
    assert product.variants == []


def test_create_product_with_variants(session, make_product):
    product = make_product(
        name="Shirt",
        variants=[
            {"sku": "shirt-s", "price_cents": 1000, "stock": 3},
            {"sku": "shirt-m", "price_cents": 1100, "stock": 1},
        ],
    )
    assert len(product.variants) == 2
    assert {v.sku for v in product.variants} == {"shirt-s", "shirt-m"}


def test_variant_foreign_key_populated(session, make_product):
    product = make_product(
        name="Hat",
        variants=[{"sku": "hat-1", "price_cents": 500}],
    )
    variant = product.variants[0]
    assert variant.product_id == product.id
    assert variant.product is product


def test_variant_backref_points_to_product(session, make_product):
    product = make_product(
        name="Mug",
        variants=[{"sku": "mug-a", "price_cents": 300}],
    )
    variant = session.execute(select(Variant).where(Variant.sku == "mug-a")).scalar_one()
    assert variant.product.id == product.id
    assert variant.product.name == "Mug"


def test_variants_relationship_is_list(session, make_product):
    product = make_product(name="Empty")
    assert isinstance(product.variants, list)


def test_sku_unique_constraint(session, make_product):
    make_product(name="A", variants=[{"sku": "dup", "price_cents": 100}])
    with pytest.raises(IntegrityError):
        make_product(name="B", variants=[{"sku": "dup", "price_cents": 200}])


def test_cascade_delete_removes_variants(session, make_product):
    product = make_product(
        name="Cascade",
        variants=[
            {"sku": "cas-1", "price_cents": 100},
            {"sku": "cas-2", "price_cents": 200},
        ],
    )
    session.delete(product)
    session.commit()
    remaining = session.execute(select(Variant)).scalars().all()
    assert remaining == []


def test_product_description_defaults_to_empty(session):
    product = Product(name="Default")
    session.add(product)
    session.commit()
    session.refresh(product)
    assert product.description == ""


def test_variant_stock_defaults_to_zero(session, make_product):
    product = make_product(name="Z", variants=[{"sku": "z-1", "price_cents": 50}])
    assert product.variants[0].stock == 0


def test_multiple_products_independent_variants(session, make_product):
    a = make_product(name="A", variants=[{"sku": "a-1", "price_cents": 100}])
    b = make_product(name="B", variants=[{"sku": "b-1", "price_cents": 200}])
    assert a.variants[0].product_id == a.id
    assert b.variants[0].product_id == b.id
    assert a.variants[0].product_id != b.variants[0].product_id
