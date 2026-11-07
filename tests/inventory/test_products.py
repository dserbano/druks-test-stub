from __future__ import annotations

import pytest


def _body(resp):
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def test_create_product_minimum(client):
    resp = client.post("/products", json={"sku": "P1", "name": "Widget"})
    body = _body(resp)
    assert body["sku"] == "P1"
    assert body["name"] == "Widget"
    assert body["price"] == 0.0
    assert body["reorder_point"] == 0
    assert body["supplier_id"] is None


def test_create_product_with_all_fields(client, supplier_factory):
    sup = supplier_factory()
    resp = client.post(
        "/products",
        json={
            "sku": "P2",
            "name": "Full",
            "description": "a full product",
            "price": 12.5,
            "reorder_point": 5,
            "supplier_id": sup["id"],
        },
    )
    body = _body(resp)
    assert body["description"] == "a full product"
    assert body["price"] == 12.5
    assert body["reorder_point"] == 5
    assert body["supplier_id"] == sup["id"]


def test_create_product_duplicate_sku_conflict(client, product_factory):
    product_factory(sku="DUP-1")
    resp = client.post("/products", json={"sku": "DUP-1", "name": "Other"})
    assert resp.status_code == 409


@pytest.mark.parametrize("missing", ["sku", "name"])
def test_create_product_missing_required(client, missing):
    payload = {"sku": "X", "name": "Y"}
    payload.pop(missing)
    resp = client.post("/products", json=payload)
    assert resp.status_code == 422


@pytest.mark.parametrize("field,value", [
    ("sku", ""),
    ("name", ""),
    ("price", -1),
    ("reorder_point", -1),
    ("price", -0.01),
    ("reorder_point", -10),
])
def test_create_product_validation(client, field, value):
    payload = {"sku": "S", "name": "N", field: value}
    resp = client.post("/products", json=payload)
    assert resp.status_code == 422


def test_get_product_ok(client, product_factory):
    p = product_factory()
    resp = client.get(f"/products/{p['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == p["id"]


def test_get_product_not_found(client):
    resp = client.get("/products/9999")
    assert resp.status_code == 404


def test_update_product_partial(client, product_factory):
    p = product_factory(price=1.0, reorder_point=0)
    resp = client.put(f"/products/{p['id']}", json={"price": 7.5})
    body = _body(resp)
    assert body["price"] == 7.5
    assert body["reorder_point"] == 0


def test_update_product_change_sku(client, product_factory):
    p = product_factory(sku="OLD")
    resp = client.put(f"/products/{p['id']}", json={"sku": "NEW"})
    assert resp.status_code == 200
    assert resp.json()["sku"] == "NEW"


def test_update_product_sku_conflict(client, product_factory):
    product_factory(sku="TAKEN")
    p = product_factory(sku="OTHER")
    resp = client.put(f"/products/{p['id']}", json={"sku": "TAKEN"})
    assert resp.status_code == 409


def test_update_product_not_found(client):
    resp = client.put("/products/9999", json={"name": "z"})
    assert resp.status_code == 404


def test_delete_product_ok(client, product_factory):
    p = product_factory()
    resp = client.delete(f"/products/{p['id']}")
    assert resp.status_code == 204
    assert client.get(f"/products/{p['id']}").status_code == 404


def test_delete_product_not_found(client):
    assert client.delete("/products/9999").status_code == 404


def test_list_products_empty(client):
    body = _body(client.get("/products"))
    assert body == {"items": [], "total": 0, "skip": 0, "limit": 50}


def test_list_products_default_pagination(client, product_factory):
    for _ in range(3):
        product_factory()
    body = _body(client.get("/products"))
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert body["skip"] == 0
    assert body["limit"] == 50


@pytest.mark.parametrize("skip,limit,expected_count", [
    (0, 5, 5),
    (0, 10, 10),
    (5, 10, 10),
    (10, 10, 5),
    (15, 10, 0),
    (0, 1, 1),
])
def test_list_products_pagination(client, product_factory, skip, limit, expected_count):
    for _ in range(15):
        product_factory()
    body = _body(client.get("/products", params={"skip": skip, "limit": limit}))
    assert body["total"] == 15
    assert len(body["items"]) == expected_count
    assert body["skip"] == skip
    assert body["limit"] == limit


@pytest.mark.parametrize("skip,limit", [(-1, 10), (0, 0), (0, -5), (0, 10000)])
def test_list_products_bad_pagination(client, skip, limit):
    resp = client.get("/products", params={"skip": skip, "limit": limit})
    assert resp.status_code == 422


def test_list_products_filter_by_name(client, product_factory):
    product_factory(name="Red Widget")
    product_factory(name="Blue Widget")
    product_factory(name="Gadget")
    body = _body(client.get("/products", params={"name": "Widget"}))
    assert body["total"] == 2
    names = {p["name"] for p in body["items"]}
    assert names == {"Red Widget", "Blue Widget"}


def test_list_products_filter_by_sku(client, product_factory):
    product_factory(sku="AAA")
    product_factory(sku="BBB")
    body = _body(client.get("/products", params={"sku": "AAA"}))
    assert body["total"] == 1
    assert body["items"][0]["sku"] == "AAA"


def test_list_products_filter_by_supplier(client, product_factory, supplier_factory):
    s1 = supplier_factory()
    s2 = supplier_factory()
    product_factory(supplier_id=s1["id"])
    product_factory(supplier_id=s1["id"])
    product_factory(supplier_id=s2["id"])
    body = _body(client.get("/products", params={"supplier_id": s1["id"]}))
    assert body["total"] == 2


def test_list_products_filter_combines(client, product_factory, supplier_factory):
    s = supplier_factory()
    product_factory(name="One", supplier_id=s["id"])
    product_factory(name="Two", supplier_id=s["id"])
    product_factory(name="One")
    body = _body(
        client.get("/products", params={"name": "One", "supplier_id": s["id"]})
    )
    assert body["total"] == 1


def test_list_products_filter_case_insensitive(client, product_factory):
    product_factory(name="Alpha")
    body = _body(client.get("/products", params={"name": "alpha"}))
    assert body["total"] == 1


@pytest.mark.parametrize("n", [1, 5, 20, 100])
def test_list_products_total_scales(client, product_factory, n):
    for _ in range(n):
        product_factory()
    body = _body(client.get("/products", params={"limit": 500}))
    assert body["total"] == n
    assert len(body["items"]) == n


def test_list_products_ordering_by_id(client, product_factory):
    created = [product_factory() for _ in range(5)]
    body = _body(client.get("/products"))
    ids_in_order = [p["id"] for p in body["items"]]
    assert ids_in_order == sorted([p["id"] for p in created])


@pytest.mark.parametrize("price", [0.0, 1.0, 10.5, 99.99, 1000.0])
def test_price_round_trips(client, price):
    resp = client.post("/products", json={"sku": f"P-{price}", "name": "x", "price": price})
    assert resp.status_code == 201
    assert resp.json()["price"] == price


@pytest.mark.parametrize("reorder", [0, 1, 10, 100, 1000])
def test_reorder_point_round_trips(client, reorder):
    resp = client.post(
        "/products",
        json={"sku": f"R-{reorder}", "name": "x", "reorder_point": reorder},
    )
    assert resp.status_code == 201
    assert resp.json()["reorder_point"] == reorder


def test_update_product_clear_supplier_requires_null(client, product_factory, supplier_factory):
    s = supplier_factory()
    p = product_factory(supplier_id=s["id"])
    resp = client.put(f"/products/{p['id']}", json={"supplier_id": None})
    assert resp.status_code == 200
    assert resp.json()["supplier_id"] is None


def test_update_product_no_fields_is_noop(client, product_factory):
    p = product_factory(price=5.0)
    resp = client.put(f"/products/{p['id']}", json={})
    assert resp.status_code == 200
    assert resp.json()["price"] == 5.0


def test_cannot_delete_product_removes_stock_levels(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 5},
    )
    assert client.delete(f"/products/{p['id']}").status_code == 204


@pytest.mark.parametrize("i", range(10))
def test_bulk_create_products(client, i):
    resp = client.post("/products", json={"sku": f"BULK-{i}", "name": f"P{i}"})
    assert resp.status_code == 201


def test_product_description_optional(client):
    resp = client.post("/products", json={"sku": "ND", "name": "nod"})
    assert resp.json()["description"] is None


def test_product_long_description(client):
    resp = client.post(
        "/products",
        json={"sku": "LD", "name": "ld", "description": "x" * 500},
    )
    assert resp.status_code == 201
    assert len(resp.json()["description"]) == 500


def test_product_description_too_long(client):
    resp = client.post(
        "/products",
        json={"sku": "LDE", "name": "ld", "description": "x" * 2000},
    )
    assert resp.status_code == 422


def test_product_sku_max_length(client):
    resp = client.post("/products", json={"sku": "x" * 100, "name": "ok"})
    assert resp.status_code == 201


def test_product_sku_over_max(client):
    resp = client.post("/products", json={"sku": "x" * 101, "name": "ok"})
    assert resp.status_code == 422


def test_product_name_max_length(client):
    resp = client.post("/products", json={"sku": "nm", "name": "y" * 300})
    assert resp.status_code == 201


def test_product_name_over_max(client):
    resp = client.post("/products", json={"sku": "nm2", "name": "y" * 301})
    assert resp.status_code == 422


@pytest.mark.parametrize("n", range(1, 6))
def test_update_many_fields(client, product_factory, n):
    p = product_factory()
    resp = client.put(
        f"/products/{p['id']}",
        json={"name": f"renamed-{n}", "price": float(n), "reorder_point": n},
    )
    body = _body(resp)
    assert body["name"] == f"renamed-{n}"
    assert body["price"] == float(n)
    assert body["reorder_point"] == n
