from __future__ import annotations

import pytest


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_exposed(client):
    assert client.get("/openapi.json").status_code == 200


@pytest.mark.parametrize("path", [
    "/products",
    "/suppliers",
    "/warehouses",
    "/stock-movements",
    "/purchase-orders",
    "/low-stock-alerts",
])
def test_resource_list_endpoints_exist(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", [
    "/products",
    "/suppliers",
    "/warehouses",
])
def test_resource_create_rejects_empty_body(client, path):
    assert client.post(path, json={}).status_code == 422


@pytest.mark.parametrize("path", [
    "/products/9999",
    "/suppliers/9999",
    "/warehouses/9999",
    "/stock-movements/9999",
    "/purchase-orders/9999",
])
def test_get_missing_returns_404(client, path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", [
    "/products/9999",
    "/suppliers/9999",
    "/warehouses/9999",
])
def test_update_missing_returns_404(client, path):
    assert client.put(path, json={"name": "x"}).status_code == 404


@pytest.mark.parametrize("path", [
    "/products/9999",
    "/suppliers/9999",
    "/warehouses/9999",
    "/purchase-orders/9999",
])
def test_delete_missing_returns_404(client, path):
    assert client.delete(path).status_code == 404


def test_pagination_shape_consistent_across_resources(
    client, product_factory, supplier_factory, warehouse_factory
):
    product_factory()
    supplier_factory()
    warehouse_factory()
    for path in ("/products", "/suppliers", "/warehouses"):
        body = client.get(path).json()
        assert {"items", "total", "skip", "limit"} <= set(body)


@pytest.mark.parametrize("path", [
    "/products",
    "/suppliers",
    "/warehouses",
    "/stock-movements",
    "/purchase-orders",
])
def test_list_default_limit_is_50(client, path):
    body = client.get(path).json()
    assert body["limit"] == 50


@pytest.mark.parametrize("path", [
    "/products",
    "/suppliers",
    "/warehouses",
])
def test_list_default_skip_is_0(client, path):
    body = client.get(path).json()
    assert body["skip"] == 0


@pytest.mark.parametrize("limit", [1, 10, 50, 100, 500])
def test_valid_limit_values(client, limit):
    body = client.get("/products", params={"limit": limit}).json()
    assert body["limit"] == limit


def test_isolation_between_tests_products(client, product_factory):
    product_factory()
    assert client.get("/products").json()["total"] == 1


def test_isolation_between_tests_suppliers(client, supplier_factory):
    supplier_factory()
    assert client.get("/suppliers").json()["total"] == 1


def test_isolation_between_tests_warehouses(client, warehouse_factory):
    warehouse_factory()
    assert client.get("/warehouses").json()["total"] == 1


def test_isolation_between_tests_stock(client):
    assert client.get("/stock-movements").json()["total"] == 0


def test_isolation_between_tests_pos(client):
    assert client.get("/purchase-orders").json()["total"] == 0


def test_create_app_factory():
    from app.inventory import create_app
    import sqlalchemy

    eng = sqlalchemy.create_engine("sqlite://", future=True)
    app = create_app(db_engine=eng, init=True)
    # routes should include each resource prefix
    paths = {route.path for route in app.routes}
    for prefix in ("/products", "/suppliers", "/warehouses",
                   "/stock-movements", "/purchase-orders", "/low-stock-alerts"):
        assert any(p.startswith(prefix) for p in paths)
    eng.dispose()


@pytest.mark.parametrize("i", range(5))
def test_simple_health_repeat(client, i):
    assert client.get("/health").status_code == 200


def test_openapi_lists_expected_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    for key in ("/products", "/suppliers", "/warehouses",
                "/stock-movements", "/purchase-orders",
                "/low-stock-alerts", "/csv/products/export",
                "/csv/suppliers/export"):
        assert key in paths, key


def test_app_title(app):
    assert app.title == "Inventory Management"
