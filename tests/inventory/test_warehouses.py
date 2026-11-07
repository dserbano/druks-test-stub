from __future__ import annotations

import pytest


def test_create_warehouse_minimum(client):
    resp = client.post("/warehouses", json={"name": "Main"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Main"
    assert resp.json()["location"] is None


def test_create_warehouse_with_location(client):
    resp = client.post("/warehouses", json={"name": "W1", "location": "Bay Area"})
    assert resp.json()["location"] == "Bay Area"


def test_create_warehouse_duplicate_name_conflict(client, warehouse_factory):
    warehouse_factory(name="Dup")
    assert client.post("/warehouses", json={"name": "Dup"}).status_code == 409


def test_create_warehouse_missing_name(client):
    assert client.post("/warehouses", json={}).status_code == 422


@pytest.mark.parametrize("name", ["", "x" * 201])
def test_create_warehouse_bad_name(client, name):
    assert client.post("/warehouses", json={"name": name}).status_code == 422


def test_get_warehouse_ok(client, warehouse_factory):
    w = warehouse_factory()
    assert client.get(f"/warehouses/{w['id']}").status_code == 200


def test_get_warehouse_not_found(client):
    assert client.get("/warehouses/9999").status_code == 404


def test_update_warehouse_ok(client, warehouse_factory):
    w = warehouse_factory()
    resp = client.put(f"/warehouses/{w['id']}", json={"location": "NY"})
    assert resp.json()["location"] == "NY"


def test_update_warehouse_rename(client, warehouse_factory):
    w = warehouse_factory(name="One")
    resp = client.put(f"/warehouses/{w['id']}", json={"name": "Two"})
    assert resp.json()["name"] == "Two"


def test_update_warehouse_rename_conflict(client, warehouse_factory):
    warehouse_factory(name="Taken")
    other = warehouse_factory(name="Free")
    resp = client.put(f"/warehouses/{other['id']}", json={"name": "Taken"})
    assert resp.status_code == 409


def test_update_warehouse_not_found(client):
    assert client.put("/warehouses/9999", json={"name": "x"}).status_code == 404


def test_delete_warehouse_ok(client, warehouse_factory):
    w = warehouse_factory()
    assert client.delete(f"/warehouses/{w['id']}").status_code == 204
    assert client.get(f"/warehouses/{w['id']}").status_code == 404


def test_delete_warehouse_not_found(client):
    assert client.delete("/warehouses/9999").status_code == 404


def test_list_warehouses_empty(client):
    body = client.get("/warehouses").json()
    assert body["total"] == 0 and body["items"] == []


@pytest.mark.parametrize("n", [1, 5, 25, 100])
def test_list_warehouses_scales(client, warehouse_factory, n):
    for _ in range(n):
        warehouse_factory()
    body = client.get("/warehouses", params={"limit": 500}).json()
    assert body["total"] == n


@pytest.mark.parametrize("skip,limit,expected", [
    (0, 5, 5),
    (5, 5, 5),
    (10, 5, 0),
    (2, 3, 3),
])
def test_list_warehouses_pagination(client, warehouse_factory, skip, limit, expected):
    for _ in range(10):
        warehouse_factory()
    body = client.get("/warehouses", params={"skip": skip, "limit": limit}).json()
    assert len(body["items"]) == expected
    assert body["total"] == 10


def test_list_warehouses_filter_by_name(client, warehouse_factory):
    warehouse_factory(name="North A")
    warehouse_factory(name="North B")
    warehouse_factory(name="South")
    body = client.get("/warehouses", params={"name": "North"}).json()
    assert body["total"] == 2


def test_list_warehouses_filter_case_insensitive(client, warehouse_factory):
    warehouse_factory(name="UpperCase")
    assert client.get("/warehouses", params={"name": "uppercase"}).json()["total"] == 1


def test_warehouse_name_max_length(client):
    assert client.post("/warehouses", json={"name": "y" * 200}).status_code == 201


def test_warehouse_name_over_max(client):
    assert client.post("/warehouses", json={"name": "y" * 201}).status_code == 422


@pytest.mark.parametrize("i", range(10))
def test_bulk_create_warehouses(client, i):
    resp = client.post("/warehouses", json={"name": f"BW-{i}"})
    assert resp.status_code == 201


def test_warehouse_update_noop(client, warehouse_factory):
    w = warehouse_factory(location="SF")
    resp = client.put(f"/warehouses/{w['id']}", json={})
    assert resp.json()["location"] == "SF"


def test_warehouse_location_clears(client, warehouse_factory):
    w = warehouse_factory(location="x")
    resp = client.put(f"/warehouses/{w['id']}", json={"location": None})
    assert resp.json()["location"] is None


def test_warehouse_list_returns_fields(client, warehouse_factory):
    warehouse_factory(location="LA")
    item = client.get("/warehouses").json()["items"][0]
    assert {"id", "name", "location"} <= set(item)


@pytest.mark.parametrize("payload", [
    {"name": "A"},
    {"name": "B", "location": "L1"},
    {"name": "C", "location": "L2"},
    {"name": "D"},
])
def test_warehouse_variants(client, payload):
    assert client.post("/warehouses", json=payload).status_code == 201
