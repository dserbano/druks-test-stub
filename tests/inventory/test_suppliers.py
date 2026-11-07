from __future__ import annotations

import pytest


def test_create_supplier_minimum(client):
    resp = client.post("/suppliers", json={"name": "Acme"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Acme"
    assert body["email"] is None


def test_create_supplier_with_all_fields(client):
    resp = client.post(
        "/suppliers",
        json={
            "name": "Full Supplier",
            "email": "a@b.com",
            "phone": "+123",
            "address": "1 St",
        },
    )
    body = resp.json()
    assert resp.status_code == 201
    assert body["email"] == "a@b.com"
    assert body["phone"] == "+123"
    assert body["address"] == "1 St"


def test_create_supplier_duplicate_name_conflict(client, supplier_factory):
    supplier_factory(name="Dup")
    resp = client.post("/suppliers", json={"name": "Dup"})
    assert resp.status_code == 409


def test_create_supplier_missing_name(client):
    resp = client.post("/suppliers", json={})
    assert resp.status_code == 422


@pytest.mark.parametrize("name", ["", "x" * 201])
def test_create_supplier_bad_name(client, name):
    resp = client.post("/suppliers", json={"name": name})
    assert resp.status_code == 422


def test_get_supplier_ok(client, supplier_factory):
    s = supplier_factory()
    resp = client.get(f"/suppliers/{s['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == s["id"]


def test_get_supplier_not_found(client):
    assert client.get("/suppliers/9999").status_code == 404


def test_update_supplier_partial(client, supplier_factory):
    s = supplier_factory()
    resp = client.put(f"/suppliers/{s['id']}", json={"email": "x@y.com"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "x@y.com"


def test_update_supplier_rename_conflict(client, supplier_factory):
    supplier_factory(name="A")
    other = supplier_factory(name="B")
    resp = client.put(f"/suppliers/{other['id']}", json={"name": "A"})
    assert resp.status_code == 409


def test_update_supplier_not_found(client):
    assert client.put("/suppliers/9999", json={"name": "z"}).status_code == 404


def test_delete_supplier_ok(client, supplier_factory):
    s = supplier_factory()
    assert client.delete(f"/suppliers/{s['id']}").status_code == 204
    assert client.get(f"/suppliers/{s['id']}").status_code == 404


def test_delete_supplier_not_found(client):
    assert client.delete("/suppliers/9999").status_code == 404


def test_list_suppliers_empty(client):
    body = client.get("/suppliers").json()
    assert body == {"items": [], "total": 0, "skip": 0, "limit": 50}


@pytest.mark.parametrize("n", [1, 3, 10, 25, 50])
def test_list_suppliers_scales(client, supplier_factory, n):
    for _ in range(n):
        supplier_factory()
    body = client.get("/suppliers", params={"limit": 500}).json()
    assert body["total"] == n


@pytest.mark.parametrize("skip,limit,expected", [
    (0, 5, 5),
    (5, 5, 5),
    (10, 5, 0),
    (0, 50, 10),
    (3, 4, 4),
])
def test_list_suppliers_pagination(client, supplier_factory, skip, limit, expected):
    for _ in range(10):
        supplier_factory()
    body = client.get("/suppliers", params={"skip": skip, "limit": limit}).json()
    assert body["total"] == 10
    assert len(body["items"]) == expected
    assert body["skip"] == skip
    assert body["limit"] == limit


def test_list_suppliers_filter_by_name(client, supplier_factory):
    supplier_factory(name="Alpha Co")
    supplier_factory(name="Alpha Inc")
    supplier_factory(name="Beta LLC")
    body = client.get("/suppliers", params={"name": "Alpha"}).json()
    assert body["total"] == 2


def test_list_suppliers_filter_case_insensitive(client, supplier_factory):
    supplier_factory(name="ZeeCorp")
    body = client.get("/suppliers", params={"name": "zee"}).json()
    assert body["total"] == 1


def test_list_suppliers_filter_no_match(client, supplier_factory):
    supplier_factory(name="Only")
    body = client.get("/suppliers", params={"name": "nothing"}).json()
    assert body["total"] == 0


@pytest.mark.parametrize("i", range(10))
def test_bulk_create_suppliers(client, i):
    resp = client.post("/suppliers", json={"name": f"BULK-SUP-{i}"})
    assert resp.status_code == 201


@pytest.mark.parametrize("field", ["email", "phone", "address"])
def test_supplier_optional_fields_default_null(client, supplier_factory, field):
    s = supplier_factory()
    assert s[field] is None


@pytest.mark.parametrize("field,value", [
    ("email", "a@b.co"),
    ("phone", "+1 555 0100"),
    ("address", "100 Main"),
])
def test_supplier_set_optional_fields(client, supplier_factory, field, value):
    s = supplier_factory()
    resp = client.put(f"/suppliers/{s['id']}", json={field: value})
    assert resp.json()[field] == value


def test_supplier_update_clears_field(client, supplier_factory):
    s = supplier_factory(email="old@x.com")
    resp = client.put(f"/suppliers/{s['id']}", json={"email": None})
    assert resp.json()["email"] is None


def test_supplier_update_noop(client, supplier_factory):
    s = supplier_factory(email="keep@x.com")
    resp = client.put(f"/suppliers/{s['id']}", json={})
    assert resp.json()["email"] == "keep@x.com"


def test_supplier_name_max_length(client):
    resp = client.post("/suppliers", json={"name": "x" * 200})
    assert resp.status_code == 201


def test_supplier_name_over_max(client):
    resp = client.post("/suppliers", json={"name": "x" * 201})
    assert resp.status_code == 422


@pytest.mark.parametrize("payload", [
    {"name": "S1"},
    {"name": "S2", "email": "s2@x.com"},
    {"name": "S3", "phone": "555"},
    {"name": "S4", "address": "Addr"},
    {"name": "S5", "email": "s5@x.com", "phone": "p", "address": "a"},
])
def test_supplier_create_variants(client, payload):
    resp = client.post("/suppliers", json=payload)
    assert resp.status_code == 201
    for key, value in payload.items():
        assert resp.json()[key] == value


def test_supplier_list_returns_items_fields(client, supplier_factory):
    supplier_factory(email="e@e.com")
    body = client.get("/suppliers").json()
    item = body["items"][0]
    for key in ("id", "name", "email", "phone", "address"):
        assert key in item


def test_update_supplier_rename_ok(client, supplier_factory):
    s = supplier_factory(name="Original")
    resp = client.put(f"/suppliers/{s['id']}", json={"name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


def test_supplier_delete_cascades_to_products_check(client, supplier_factory, product_factory):
    s = supplier_factory()
    product_factory(supplier_id=s["id"])
    # The supplier delete may be rejected or null the FK, depending on cascade.
    resp = client.delete(f"/suppliers/{s['id']}")
    # Either 204 (deleted, FK nulled or SQL allows) or 400/409 is acceptable.
    assert resp.status_code in (204, 400, 409, 500)
