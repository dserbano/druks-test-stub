from __future__ import annotations


def test_list_products_empty(client):
    response = client.get("/products")
    assert response.status_code == 200
    assert response.json() == []


def test_list_products_returns_seeded(client, make_product):
    make_product(name="Alpha")
    make_product(name="Bravo")
    response = client.get("/products")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {p["name"] for p in body} == {"Alpha", "Bravo"}


def test_list_products_returns_list_type(client, make_product):
    make_product(name="Solo")
    body = client.get("/products").json()
    assert isinstance(body, list)
    assert isinstance(body[0], dict)


def test_list_products_includes_variants(client, make_product):
    make_product(
        name="With-Variants",
        variants=[
            {"sku": "wv-1", "price_cents": 100},
            {"sku": "wv-2", "price_cents": 200},
        ],
    )
    body = client.get("/products").json()
    assert len(body) == 1
    variants = body[0]["variants"]
    assert len(variants) == 2
    assert {v["sku"] for v in variants} == {"wv-1", "wv-2"}


def test_list_products_empty_variants_field(client, make_product):
    make_product(name="NoVar")
    body = client.get("/products").json()
    assert body[0]["variants"] == []


def test_list_products_limit(client, make_product):
    for i in range(5):
        make_product(name=f"p{i}")
    body = client.get("/products", params={"limit": 2}).json()
    assert len(body) == 2


def test_list_products_offset(client, make_product):
    for i in range(3):
        make_product(name=f"n{i}")
    body = client.get("/products", params={"offset": 1}).json()
    assert len(body) == 2
    assert body[0]["name"] == "n1"


def test_list_products_limit_zero_invalid(client):
    response = client.get("/products", params={"limit": 0})
    assert response.status_code == 422
