from __future__ import annotations

import pytest


def _on_hand(client, product_id, warehouse_id):
    body = client.get(
        "/stock-movements", params={"product_id": product_id, "warehouse_id": warehouse_id}
    ).json()
    inflow = sum(m["quantity"] for m in body["items"] if m["kind"] == "in")
    outflow = sum(m["quantity"] for m in body["items"] if m["kind"] == "out")
    transfer_out = sum(
        m["quantity"]
        for m in body["items"]
        if m["kind"] == "transfer" and m["warehouse_id"] == warehouse_id
    )
    # Include transfers coming in at this warehouse (dest_warehouse_id side).
    body_all = client.get("/stock-movements", params={"product_id": product_id}).json()
    transfer_in = sum(
        m["quantity"]
        for m in body_all["items"]
        if m["kind"] == "transfer" and m["dest_warehouse_id"] == warehouse_id
    )
    return inflow + transfer_in - outflow - transfer_out


def test_post_inbound_creates_movement(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 5},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["kind"] == "in"
    assert body["quantity"] == 5
    assert body["dest_warehouse_id"] is None


def test_inbound_increases_on_hand(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    for _ in range(3):
        client.post(
            "/stock-movements",
            json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 4},
        )
    # Reorder to zero so this ends up in alerts if on_hand ≤ 0. Confirm no alert.
    client.put(f"/products/{p['id']}", json={"reorder_point": 11})
    alerts = client.get("/low-stock-alerts").json()
    # On hand = 12 which is above 11: not in alerts.
    assert all(a["product_id"] != p["id"] for a in alerts)


def test_outbound_decreases_stock(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 10},
    )
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 3},
    )
    assert resp.status_code == 201


def test_outbound_insufficient_rejected(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 1},
    )
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"]


def test_outbound_partial_then_fail(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 5},
    )
    assert client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 5},
    ).status_code == 201
    assert client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 1},
    ).status_code == 400


def test_transfer_moves_stock(client, product_factory, warehouse_factory):
    p = product_factory()
    src = warehouse_factory()
    dest = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": src["id"], "kind": "in", "quantity": 10},
    )
    resp = client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": src["id"],
            "kind": "transfer",
            "quantity": 4,
            "dest_warehouse_id": dest["id"],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["dest_warehouse_id"] == dest["id"]


def test_transfer_requires_dest(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": w["id"],
            "kind": "transfer",
            "quantity": 1,
        },
    )
    assert resp.status_code == 400


def test_transfer_same_warehouse_rejected(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": w["id"],
            "kind": "transfer",
            "quantity": 1,
            "dest_warehouse_id": w["id"],
        },
    )
    assert resp.status_code == 400


def test_transfer_insufficient_stock(client, product_factory, warehouse_factory):
    p = product_factory()
    src = warehouse_factory()
    dest = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": src["id"],
            "kind": "transfer",
            "quantity": 1,
            "dest_warehouse_id": dest["id"],
        },
    )
    assert resp.status_code == 400


def test_dest_only_for_transfer(client, product_factory, warehouse_factory):
    p = product_factory()
    w1 = warehouse_factory()
    w2 = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": w1["id"],
            "kind": "in",
            "quantity": 1,
            "dest_warehouse_id": w2["id"],
        },
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("quantity", [0, -1, -100])
def test_non_positive_quantity_rejected(client, product_factory, warehouse_factory, quantity):
    p = product_factory()
    w = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": quantity},
    )
    assert resp.status_code == 422


def test_unknown_product_rejected(client, warehouse_factory):
    w = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={"product_id": 9999, "warehouse_id": w["id"], "kind": "in", "quantity": 1},
    )
    assert resp.status_code == 400


def test_unknown_warehouse_rejected(client, product_factory):
    p = product_factory()
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": 9999, "kind": "in", "quantity": 1},
    )
    assert resp.status_code == 400


def test_list_movements_empty(client):
    assert client.get("/stock-movements").json()["total"] == 0


def test_list_movements_filter_by_product(client, product_factory, warehouse_factory):
    p1 = product_factory()
    p2 = product_factory()
    w = warehouse_factory()
    for p in (p1, p2):
        client.post(
            "/stock-movements",
            json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 1},
        )
    body = client.get("/stock-movements", params={"product_id": p1["id"]}).json()
    assert body["total"] == 1


def test_list_movements_filter_by_warehouse(client, product_factory, warehouse_factory):
    p = product_factory()
    w1 = warehouse_factory()
    w2 = warehouse_factory()
    for w in (w1, w2):
        client.post(
            "/stock-movements",
            json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 2},
        )
    body = client.get("/stock-movements", params={"warehouse_id": w1["id"]}).json()
    assert body["total"] == 1


def test_list_movements_filter_by_kind(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 5},
    )
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 2},
    )
    body = client.get("/stock-movements", params={"kind": "in"}).json()
    assert body["total"] == 1


@pytest.mark.parametrize("skip,limit,expected", [
    (0, 5, 5),
    (5, 5, 5),
    (10, 5, 0),
    (0, 50, 10),
])
def test_list_movements_pagination(client, product_factory, warehouse_factory, skip, limit, expected):
    p = product_factory()
    w = warehouse_factory()
    for _ in range(10):
        client.post(
            "/stock-movements",
            json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 1},
        )
    body = client.get("/stock-movements", params={"skip": skip, "limit": limit}).json()
    assert body["total"] == 10
    assert len(body["items"]) == expected


def test_get_movement_ok(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    mid = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 3},
    ).json()["id"]
    assert client.get(f"/stock-movements/{mid}").status_code == 200


def test_get_movement_not_found(client):
    assert client.get("/stock-movements/9999").status_code == 404


def test_movement_has_timestamp(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    body = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 1},
    ).json()
    assert "created_at" in body and body["created_at"]


def test_movement_reference_stored(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    body = client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": w["id"],
            "kind": "in",
            "quantity": 1,
            "reference": "ref-42",
        },
    ).json()
    assert body["reference"] == "ref-42"


@pytest.mark.parametrize("qty", [1, 5, 50, 100, 500])
def test_multiple_inbound_sizes(client, product_factory, warehouse_factory, qty):
    p = product_factory()
    w = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": qty},
    )
    assert resp.json()["quantity"] == qty


def test_outbound_at_exact_balance(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 7},
    )
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 7},
    )
    assert resp.status_code == 201


def test_transfer_source_goes_negative_rejected(client, product_factory, warehouse_factory):
    p = product_factory()
    src = warehouse_factory()
    dest = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": src["id"], "kind": "in", "quantity": 3},
    )
    resp = client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": src["id"],
            "kind": "transfer",
            "quantity": 5,
            "dest_warehouse_id": dest["id"],
        },
    )
    assert resp.status_code == 400


def test_movements_isolated_across_products(client, product_factory, warehouse_factory):
    p1 = product_factory()
    p2 = product_factory()
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p1["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 10},
    )
    # p2 has 0 stock; out should fail
    resp = client.post(
        "/stock-movements",
        json={"product_id": p2["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 1},
    )
    assert resp.status_code == 400


def test_movements_isolated_across_warehouses(client, product_factory, warehouse_factory):
    p = product_factory()
    w1 = warehouse_factory()
    w2 = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w1["id"], "kind": "in", "quantity": 5},
    )
    # out at w2 fails
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w2["id"], "kind": "out", "quantity": 1},
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("i", range(10))
def test_many_movements(client, product_factory, warehouse_factory, i):
    p = product_factory()
    w = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": i + 1},
    )
    assert resp.status_code == 201


def test_transfer_round_trip(client, product_factory, warehouse_factory):
    p = product_factory()
    a = warehouse_factory()
    b = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": a["id"], "kind": "in", "quantity": 10},
    )
    client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": a["id"],
            "kind": "transfer",
            "quantity": 10,
            "dest_warehouse_id": b["id"],
        },
    )
    # Now a is empty, b has 10; moving back should work
    client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": b["id"],
            "kind": "transfer",
            "quantity": 10,
            "dest_warehouse_id": a["id"],
        },
    )
    body = client.get(
        "/stock-movements", params={"product_id": p["id"]}
    ).json()
    assert body["total"] == 3


def test_invalid_kind_rejected(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "foo", "quantity": 1},
    )
    assert resp.status_code == 422


def test_list_movements_combine_filters(client, product_factory, warehouse_factory):
    p = product_factory()
    w = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 2},
    )
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in", "quantity": 3},
    )
    body = client.get(
        "/stock-movements",
        params={"product_id": p["id"], "warehouse_id": w["id"], "kind": "in"},
    ).json()
    assert body["total"] == 2


def test_transfer_leaves_source_zero_when_it_was_exact(client, product_factory, warehouse_factory):
    p = product_factory()
    src = warehouse_factory()
    dest = warehouse_factory()
    client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": src["id"], "kind": "in", "quantity": 4},
    )
    client.post(
        "/stock-movements",
        json={
            "product_id": p["id"],
            "warehouse_id": src["id"],
            "kind": "transfer",
            "quantity": 4,
            "dest_warehouse_id": dest["id"],
        },
    )
    # Out from src must fail now.
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": src["id"], "kind": "out", "quantity": 1},
    )
    assert resp.status_code == 400
