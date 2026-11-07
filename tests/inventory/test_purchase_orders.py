from __future__ import annotations

import pytest


@pytest.fixture
def po_bundle(client, supplier_factory, warehouse_factory, product_factory):
    s = supplier_factory()
    w = warehouse_factory()
    p1 = product_factory()
    p2 = product_factory()
    return {"supplier": s, "warehouse": w, "products": [p1, p2]}


def _make_po(client, supplier_id, warehouse_id, lines):
    resp = client.post(
        "/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_id,
            "lines": lines,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_po(client, po_bundle):
    s = po_bundle["supplier"]
    w = po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": 3, "unit_price": 1.5}])
    assert po["status"] == "draft"
    assert po["received_at"] is None
    assert len(po["lines"]) == 1


def test_create_po_without_lines(client, po_bundle):
    s = po_bundle["supplier"]
    w = po_bundle["warehouse"]
    po = _make_po(client, s["id"], w["id"], [])
    assert po["lines"] == []


def test_create_po_multiple_lines(client, po_bundle):
    s = po_bundle["supplier"]
    w = po_bundle["warehouse"]
    lines = [{"product_id": p["id"], "quantity": i + 1, "unit_price": 1.0}
             for i, p in enumerate(po_bundle["products"])]
    po = _make_po(client, s["id"], w["id"], lines)
    assert len(po["lines"]) == 2


def test_get_po_ok(client, po_bundle):
    s = po_bundle["supplier"]
    w = po_bundle["warehouse"]
    po = _make_po(client, s["id"], w["id"], [])
    assert client.get(f"/purchase-orders/{po['id']}").status_code == 200


def test_get_po_not_found(client):
    assert client.get("/purchase-orders/9999").status_code == 404


def test_update_draft_po(client, po_bundle):
    s = po_bundle["supplier"]
    w = po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [])
    resp = client.put(
        f"/purchase-orders/{po['id']}",
        json={"lines": [{"product_id": p["id"], "quantity": 2, "unit_price": 3.0}]},
    )
    assert resp.status_code == 200
    assert len(resp.json()["lines"]) == 1


def test_update_po_not_found(client):
    assert client.put("/purchase-orders/9999", json={"supplier_id": 1}).status_code == 404


def test_delete_draft_po(client, po_bundle):
    s = po_bundle["supplier"]
    w = po_bundle["warehouse"]
    po = _make_po(client, s["id"], w["id"], [])
    assert client.delete(f"/purchase-orders/{po['id']}").status_code == 204


def test_delete_po_not_found(client):
    assert client.delete("/purchase-orders/9999").status_code == 404


def test_delete_non_draft_rejected(client, po_bundle):
    s = po_bundle["supplier"]
    w = po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": 2}])
    # transition to placed
    client.put(f"/purchase-orders/{po['id']}", json={"status": "placed"})
    assert client.delete(f"/purchase-orders/{po['id']}").status_code == 400


def test_transition_draft_to_placed(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    po = _make_po(client, s["id"], w["id"], [])
    resp = client.put(f"/purchase-orders/{po['id']}", json={"status": "placed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "placed"


def test_receive_empty_po_rejected(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    po = _make_po(client, s["id"], w["id"], [])
    client.put(f"/purchase-orders/{po['id']}", json={"status": "placed"})
    resp = client.post(f"/purchase-orders/{po['id']}/receive")
    assert resp.status_code == 400


def test_receive_posts_movements(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p1, p2 = po_bundle["products"]
    po = _make_po(
        client,
        s["id"],
        w["id"],
        [
            {"product_id": p1["id"], "quantity": 3, "unit_price": 1.0},
            {"product_id": p2["id"], "quantity": 7, "unit_price": 2.0},
        ],
    )
    resp = client.post(f"/purchase-orders/{po['id']}/receive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"
    assert resp.json()["received_at"] is not None
    movements = client.get(
        "/stock-movements", params={"warehouse_id": w["id"]}
    ).json()["items"]
    quantities = {m["product_id"]: m["quantity"] for m in movements if m["kind"] == "in"}
    assert quantities[p1["id"]] == 3
    assert quantities[p2["id"]] == 7


def test_receive_increases_stock_levels(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p1 = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p1["id"], "quantity": 11}])
    client.post(f"/purchase-orders/{po['id']}/receive")
    # Drain via out movement to prove level is 11
    resp = client.post(
        "/stock-movements",
        json={"product_id": p1["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 11},
    )
    assert resp.status_code == 201
    # 12th should fail
    resp2 = client.post(
        "/stock-movements",
        json={"product_id": p1["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 1},
    )
    assert resp2.status_code == 400


def test_cannot_receive_twice(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": 1}])
    assert client.post(f"/purchase-orders/{po['id']}/receive").status_code == 200
    assert client.post(f"/purchase-orders/{po['id']}/receive").status_code == 400


def test_cancel_from_draft(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    po = _make_po(client, s["id"], w["id"], [])
    resp = client.put(f"/purchase-orders/{po['id']}", json={"status": "cancelled"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_cannot_transition_cancelled(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    po = _make_po(client, s["id"], w["id"], [])
    client.put(f"/purchase-orders/{po['id']}", json={"status": "cancelled"})
    resp = client.put(f"/purchase-orders/{po['id']}", json={"status": "placed"})
    assert resp.status_code == 400


def test_cannot_edit_placed_po_fields(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": 1}])
    client.put(f"/purchase-orders/{po['id']}", json={"status": "placed"})
    resp = client.put(f"/purchase-orders/{po['id']}", json={"supplier_id": s["id"]})
    assert resp.status_code == 400


def test_list_pos_empty(client):
    assert client.get("/purchase-orders").json()["total"] == 0


@pytest.mark.parametrize("skip,limit,expected", [
    (0, 5, 5),
    (5, 5, 5),
    (0, 100, 10),
    (10, 5, 0),
])
def test_list_pos_pagination(client, po_bundle, skip, limit, expected):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    for _ in range(10):
        _make_po(client, s["id"], w["id"], [])
    body = client.get("/purchase-orders", params={"skip": skip, "limit": limit}).json()
    assert body["total"] == 10
    assert len(body["items"]) == expected


def test_list_pos_filter_by_status(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p = po_bundle["products"][0]
    _make_po(client, s["id"], w["id"], [])  # draft
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": 1}])
    client.post(f"/purchase-orders/{po['id']}/receive")
    body_r = client.get("/purchase-orders", params={"status": "received"}).json()
    body_d = client.get("/purchase-orders", params={"status": "draft"}).json()
    assert body_r["total"] == 1
    assert body_d["total"] == 1


def test_list_pos_filter_by_supplier(client, supplier_factory, warehouse_factory):
    w = warehouse_factory()
    s1 = supplier_factory()
    s2 = supplier_factory()
    _make_po(client, s1["id"], w["id"], [])
    _make_po(client, s2["id"], w["id"], [])
    body = client.get("/purchase-orders", params={"supplier_id": s1["id"]}).json()
    assert body["total"] == 1


def test_list_pos_filter_by_warehouse(client, supplier_factory, warehouse_factory):
    s = supplier_factory()
    w1 = warehouse_factory()
    w2 = warehouse_factory()
    _make_po(client, s["id"], w1["id"], [])
    _make_po(client, s["id"], w2["id"], [])
    body = client.get("/purchase-orders", params={"warehouse_id": w1["id"]}).json()
    assert body["total"] == 1


def test_po_line_validation(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    resp = client.post(
        "/purchase-orders",
        json={
            "supplier_id": s["id"],
            "warehouse_id": w["id"],
            "lines": [{"product_id": 1, "quantity": 0}],
        },
    )
    assert resp.status_code == 422


def test_po_receive_endpoint_bridges_draft(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": 2}])
    resp = client.post(f"/purchase-orders/{po['id']}/receive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


def test_po_receive_not_found(client):
    assert client.post("/purchase-orders/9999/receive").status_code == 404


def test_update_po_supplier(client, po_bundle, supplier_factory):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    new_s = supplier_factory()
    po = _make_po(client, s["id"], w["id"], [])
    resp = client.put(f"/purchase-orders/{po['id']}", json={"supplier_id": new_s["id"]})
    assert resp.json()["supplier_id"] == new_s["id"]


def test_update_po_warehouse(client, po_bundle, warehouse_factory):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    new_w = warehouse_factory()
    po = _make_po(client, s["id"], w["id"], [])
    resp = client.put(f"/purchase-orders/{po['id']}", json={"warehouse_id": new_w["id"]})
    assert resp.json()["warehouse_id"] == new_w["id"]


def test_po_lines_replace_on_update(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p1, p2 = po_bundle["products"]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p1["id"], "quantity": 1}])
    resp = client.put(
        f"/purchase-orders/{po['id']}",
        json={"lines": [{"product_id": p2["id"], "quantity": 4}]},
    )
    assert len(resp.json()["lines"]) == 1
    assert resp.json()["lines"][0]["product_id"] == p2["id"]


def test_receive_multiple_lines_for_same_product_sums(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(
        client,
        s["id"],
        w["id"],
        [{"product_id": p["id"], "quantity": 2}, {"product_id": p["id"], "quantity": 3}],
    )
    client.post(f"/purchase-orders/{po['id']}/receive")
    # Should have 5 on hand total
    resp = client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "out", "quantity": 5},
    )
    assert resp.status_code == 201


@pytest.mark.parametrize("qty", [1, 10, 100, 1000])
def test_receive_scales_quantity(client, po_bundle, qty):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": qty}])
    assert client.post(f"/purchase-orders/{po['id']}/receive").status_code == 200
    assert client.post(
        "/stock-movements",
        json={"product_id": p["id"], "warehouse_id": w["id"], "kind": "out", "quantity": qty},
    ).status_code == 201


@pytest.mark.parametrize("i", range(5))
def test_po_bulk_create(client, po_bundle, i):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    po = _make_po(client, s["id"], w["id"], [])
    assert po["id"] is not None


def test_po_received_at_set_on_receive(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": 1}])
    resp = client.post(f"/purchase-orders/{po['id']}/receive")
    assert resp.json()["received_at"] is not None


def test_po_reference_in_movement(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": 1}])
    client.post(f"/purchase-orders/{po['id']}/receive")
    movements = client.get("/stock-movements").json()["items"]
    assert movements[0]["reference"] == f"PO:{po['id']}"


def test_po_cancel_on_placed(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    p = po_bundle["products"][0]
    po = _make_po(client, s["id"], w["id"], [{"product_id": p["id"], "quantity": 1}])
    client.put(f"/purchase-orders/{po['id']}", json={"status": "placed"})
    resp = client.put(f"/purchase-orders/{po['id']}", json={"status": "cancelled"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_cancelled_po_cannot_receive(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    po = _make_po(client, s["id"], w["id"], [])
    client.put(f"/purchase-orders/{po['id']}", json={"status": "cancelled"})
    assert client.post(f"/purchase-orders/{po['id']}/receive").status_code == 400


def test_po_create_negative_price_rejected(client, po_bundle):
    s, w = po_bundle["supplier"], po_bundle["warehouse"]
    resp = client.post(
        "/purchase-orders",
        json={
            "supplier_id": s["id"],
            "warehouse_id": w["id"],
            "lines": [{"product_id": 1, "quantity": 1, "unit_price": -0.01}],
        },
    )
    assert resp.status_code == 422
