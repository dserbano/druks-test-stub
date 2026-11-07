from __future__ import annotations

import io

import pytest


def _upload(client, path, text, field="file"):
    return client.post(
        path,
        files={field: ("data.csv", io.BytesIO(text.encode("utf-8")), "text/csv")},
    )


# ------ Products ------

def test_export_products_empty(client):
    body = client.get("/csv/products/export").text
    assert body.splitlines()[0] == "sku,name,description,price,reorder_point,supplier_id"


def test_export_products_has_rows(client, product_factory):
    product_factory(sku="E1", name="Exp", price=1.0, reorder_point=2)
    body = client.get("/csv/products/export").text.splitlines()
    assert any("E1" in line for line in body[1:])


def test_import_products_basic(client):
    csv_text = "sku,name,price,reorder_point\nX1,hello,1.5,3\n"
    resp = _upload(client, "/csv/products/import", csv_text)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 1
    assert body["errors"] == []


def test_import_products_missing_name(client):
    csv_text = "sku,name\nM1,\n"
    resp = _upload(client, "/csv/products/import", csv_text)
    body = resp.json()
    assert body["imported"] == 0
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 1


def test_import_products_missing_sku(client):
    csv_text = "sku,name\n,hello\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 0
    assert len(body["errors"]) == 1


def test_import_products_mixed_rows(client):
    csv_text = "sku,name,price\nGOOD,ok,1.0\n,bad,2.0\nGOOD2,ok2,3.0\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 2
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 2


def test_import_products_upserts(client):
    client.post("/products", json={"sku": "UP1", "name": "old", "price": 1.0})
    csv_text = "sku,name,price\nUP1,new,9.0\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 1
    # Confirm name/price updated
    p = client.get("/products", params={"sku": "UP1"}).json()["items"][0]
    assert p["name"] == "new"
    assert p["price"] == 9.0


def test_import_products_negative_price_errors(client):
    csv_text = "sku,name,price\nN1,x,-1\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 0
    assert body["errors"][0]["error"]


def test_import_products_negative_reorder_errors(client):
    csv_text = "sku,name,reorder_point\nN2,x,-1\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 0


def test_import_products_unknown_supplier_errors(client):
    csv_text = "sku,name,supplier_id\nN3,x,9999\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 0
    assert "supplier" in body["errors"][0]["error"]


def test_import_products_valid_supplier(client, supplier_factory):
    s = supplier_factory()
    csv_text = f"sku,name,supplier_id\nOK,x,{s['id']}\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 1


def test_export_then_import_round_trip(client, product_factory):
    product_factory(sku="R1", name="r1", price=5.0, reorder_point=2)
    product_factory(sku="R2", name="r2", price=2.5)
    exported = client.get("/csv/products/export").text
    # Delete and re-import
    before = client.get("/products", params={"sku": "R1"}).json()["items"][0]["id"]
    assert client.delete(f"/products/{before}").status_code == 204
    body = _upload(client, "/csv/products/import", exported).json()
    assert body["imported"] == 2


def test_import_products_non_utf8_rejected(client):
    bad = b"\xff\xfe\x00bad"
    resp = client.post(
        "/csv/products/import",
        files={"file": ("x.csv", io.BytesIO(bad), "text/csv")},
    )
    assert resp.status_code == 400


# ------ Suppliers ------

def test_export_suppliers_empty_header(client):
    assert client.get("/csv/suppliers/export").text.splitlines()[0] == "name,email,phone,address"


def test_export_suppliers_has_rows(client, supplier_factory):
    supplier_factory(name="S1", email="a@b.com")
    body = client.get("/csv/suppliers/export").text.splitlines()
    assert any("S1" in line for line in body[1:])


def test_import_suppliers_basic(client):
    csv_text = "name,email\nS1,a@b.com\n"
    body = _upload(client, "/csv/suppliers/import", csv_text).json()
    assert body["imported"] == 1
    assert body["errors"] == []


def test_import_suppliers_missing_name(client):
    csv_text = "name,email\n,x@y.com\n"
    body = _upload(client, "/csv/suppliers/import", csv_text).json()
    assert body["imported"] == 0
    assert len(body["errors"]) == 1


def test_import_suppliers_bad_email(client):
    csv_text = "name,email\nNoAt,invalid\n"
    body = _upload(client, "/csv/suppliers/import", csv_text).json()
    assert body["imported"] == 0


def test_import_suppliers_mixed_rows(client):
    csv_text = "name,email\nOk1,a@b.com\n,bad\nOk2,c@d.com\n"
    body = _upload(client, "/csv/suppliers/import", csv_text).json()
    assert body["imported"] == 2
    assert len(body["errors"]) == 1


def test_import_suppliers_upserts(client, supplier_factory):
    supplier_factory(name="ExistSup", email="old@x.com")
    csv_text = "name,email\nExistSup,new@x.com\n"
    body = _upload(client, "/csv/suppliers/import", csv_text).json()
    assert body["imported"] == 1
    page = client.get("/suppliers", params={"name": "ExistSup"}).json()
    assert page["items"][0]["email"] == "new@x.com"


def test_suppliers_round_trip(client, supplier_factory):
    supplier_factory(name="R1", email="r1@x.com")
    supplier_factory(name="R2")
    exported = client.get("/csv/suppliers/export").text
    body = _upload(client, "/csv/suppliers/import", exported).json()
    assert body["imported"] == 2


@pytest.mark.parametrize("extra", [
    "",
    "address only,a@a.com,,Main St\n",
    "phone only,,555-0100,\n",
])
def test_import_suppliers_variants(client, extra):
    csv_text = "name,email,phone,address\n" + extra if extra else "name,email,phone,address\n"
    body = _upload(client, "/csv/suppliers/import", csv_text).json()
    # Header-only is 0 imports; otherwise 1.
    assert body["imported"] == (0 if not extra else 1)


def test_import_products_empty_body(client):
    resp = _upload(client, "/csv/products/import", "sku,name\n")
    assert resp.json()["imported"] == 0


def test_import_products_whitespace_treated_as_missing(client):
    csv_text = "sku,name\n   ,hello\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 0


def test_import_products_price_string(client):
    csv_text = "sku,name,price\nSTR,x,notanumber\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 0


@pytest.mark.parametrize("i", range(5))
def test_import_products_many_rows(client, i):
    csv_text = f"sku,name\nMANY-{i},p-{i}\n"
    body = _upload(client, "/csv/products/import", csv_text).json()
    assert body["imported"] == 1


def test_csv_imports_do_not_abort_batch_on_partial_failure(client):
    rows = ["sku,name,price"]
    for i in range(5):
        rows.append(f"OK-{i},p,{i + 1}")
    rows.append(",bad,1")
    for i in range(5):
        rows.append(f"OK2-{i},p,{i + 1}")
    body = _upload(client, "/csv/products/import", "\n".join(rows) + "\n").json()
    assert body["imported"] == 10
    assert len(body["errors"]) == 1
