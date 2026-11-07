from __future__ import annotations

import pytest


def _alert_ids(client, params=None):
    resp = client.get("/low-stock-alerts", params=params or {})
    assert resp.status_code == 200
    return {a["product_id"] for a in resp.json()}


def test_no_alerts_when_no_products(client):
    assert client.get("/low-stock-alerts").json() == []


def test_product_with_zero_stock_and_zero_reorder_is_alerted(client, product_factory):
    # Default reorder_point=0 means on_hand=0 <= 0 -> alerted.
    p = product_factory()
    assert p["id"] in _alert_ids(client)


def test_product_above_reorder_not_alerted(client, product_factory, warehouse_factory):
    p = product_factory(reorder_point=5)
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 10},
    )
    assert p["id"] not in _alert_ids(client)


def test_product_at_reorder_is_alerted(client, product_factory, warehouse_factory):
    p = product_factory(reorder_point=5)
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 5},
    )
    assert p["id"] in _alert_ids(client)


def test_product_below_reorder_is_alerted(client, product_factory, warehouse_factory):
    p = product_factory(reorder_point=5)
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 3},
    )
    assert p["id"] in _alert_ids(client)


def test_dropping_below_threshold_flips_in(client, product_factory, warehouse_factory):
    p = product_factory(reorder_point=5)
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 10},
    )
    assert p["id"] not in _alert_ids(client)
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 6},
    )
    assert p["id"] in _alert_ids(client)


def test_crossing_back_above_threshold_removes_alert(client, product_factory, warehouse_factory):
    p = product_factory(reorder_point=5)
    w = warehouse_factory()
    assert p["id"] in _alert_ids(client)
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 20},
    )
    assert p["id"] not in _alert_ids(client)


def test_alerts_sum_across_warehouses(client, product_factory, warehouse_factory):
    p = product_factory(reorder_point=10)
    w1 = warehouse_factory()
    w2 = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w1["id"], "kind": "in", "quantity": 6},
    )
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w2["id"], "kind": "in", "quantity": 6},
    )
    # Total 12 > 10 -> not alerted
    assert p["id"] not in _alert_ids(client)


def test_alerts_filter_by_warehouse(client, product_factory, warehouse_factory):
    p = product_factory(reorder_point=5)
    w1 = warehouse_factory()
    w2 = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w1["id"], "kind": "in", "quantity": 10},
    )
    # Globally not alerted; per w2 (0 stock) alerted.
    assert p["id"] not in _alert_ids(client)
    assert p["id"] in _alert_ids(client, params={"warehouse_id": w2["id"]})


def test_alerts_include_schema_fields(client, product_factory):
    p = product_factory(reorder_point=2)
    body = client.get("/low-stock-alerts").json()
    match = [a for a in body if a["product_id"] == p["id"]][0]
    assert {"product_id", "sku", "name", "on_hand", "reorder_point"} <= set(match)
    assert match["reorder_point"] == 2
    assert match["on_hand"] == 0


@pytest.mark.parametrize("reorder,quantity,expected", [
    (0, 0, True),
    (0, 1, False),
    (5, 4, True),
    (5, 5, True),
    (5, 6, False),
    (100, 99, True),
    (100, 100, True),
    (100, 101, False),
])
def test_alert_threshold_matrix(client, product_factory, warehouse_factory, reorder, quantity, expected):
    p = product_factory(reorder_point=reorder)
    w = warehouse_factory()
    if quantity:
        client.post(
            "/stock-movements",
            json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": quantity},
        )
    is_alerted = p["id"] in _alert_ids(client)
    assert is_alerted == expected


def test_alerts_multiple_products(client, product_factory, warehouse_factory):
    w = warehouse_factory()
    short = product_factory(reorder_point=5)
    ok = product_factory(reorder_point=5)
    client.post(
        "/stock-movements",
        json={"product_id": ok["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 10},
    )
    ids = _alert_ids(client)
    assert short["id"] in ids
    assert ok["id"] not in ids


def test_alerts_product_updated_reorder_point(client, product_factory, warehouse_factory):
    p = product_factory(reorder_point=100)
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 50},
    )
    assert p["id"] in _alert_ids(client)
    client.put(f"/products/{p['id']}", json={"reorder_point": 10})
    assert p["id"] not in _alert_ids(client)


@pytest.mark.parametrize("i", range(5))
def test_alerts_many_products(client, product_factory, i):
    p = product_factory(reorder_point=1)
    assert p["id"] in _alert_ids(client)
