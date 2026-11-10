from __future__ import annotations


def test_get_product_detail_200(client, make_product):
    product = make_product(name="Detail")
    response = client.get(f"/products/{product.id}")
    assert response.status_code == 200
    assert response.json()["id"] == product.id
    assert response.json()["name"] == "Detail"


def test_get_product_detail_nested_variants(client, make_product):
    product = make_product(
        name="Nested",
        variants=[
            {"sku": "n-s", "price_cents": 100, "stock": 1},
            {"sku": "n-m", "price_cents": 110, "stock": 2},
        ],
    )
    body = client.get(f"/products/{product.id}").json()
    assert "variants" in body
    assert isinstance(body["variants"], list)
    assert len(body["variants"]) == 2
    skus = {v["sku"] for v in body["variants"]}
    assert skus == {"n-s", "n-m"}


def test_get_product_detail_variant_fields(client, make_product):
    product = make_product(
        name="Fielded",
        variants=[{"sku": "f-1", "price_cents": 999, "stock": 7}],
    )
    body = client.get(f"/products/{product.id}").json()
    variant = body["variants"][0]
    assert variant["sku"] == "f-1"
    assert variant["price_cents"] == 999
    assert variant["stock"] == 7


def test_get_product_detail_404_when_missing(client):
    response = client.get("/products/9999")
    assert response.status_code == 404


def test_get_product_detail_404_body_has_detail(client):
    response = client.get("/products/42")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_get_product_detail_404_after_delete(client, make_product, session):
    product = make_product(name="Doomed")
    product_id = product.id
    session.delete(product)
    session.commit()
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 404


def test_get_product_detail_id_type_validation(client):
    response = client.get("/products/not-an-int")
    assert response.status_code == 422


def test_get_product_detail_does_not_leak_siblings(client, make_product):
    a = make_product(name="A", variants=[{"sku": "ax", "price_cents": 1}])
    make_product(name="B", variants=[{"sku": "bx", "price_cents": 1}])
    body = client.get(f"/products/{a.id}").json()
    assert len(body["variants"]) == 1
    assert body["variants"][0]["sku"] == "ax"
