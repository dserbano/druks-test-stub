# Inventory app architecture

## Layering

The app follows a three-layer shape: **routers → services → models**.

- **`routers/`** — FastAPI `APIRouter` modules, one per resource. Routers bind HTTP endpoints to Pydantic schemas, depend on `get_db` for a per-request `Session`, and raise `HTTPException` on validation or lookup failures. No business logic lives here.
- **`services/`** — plain functions that take a `Session` plus typed arguments. Services own the transactional rules: a stock movement and the matching stock-level change commit together; a purchase order's status transition and the stock movements it emits commit together. Services raise typed `StockError` / `POError`; routers translate those into 4xx responses.
- **`models/`** — SQLAlchemy 2.0 declarative models. Tables carry the invariants the database can enforce (unique SKU, unique `(product_id, warehouse_id)` for stock levels, foreign keys). Models hold no logic.

Pydantic schemas in `schemas/` sit alongside models. They are deliberately a separate type graph — mutating API bodies (`ProductUpdate` with every field optional) don't round-trip the ORM shape.

## Stock movement flow

A `StockMovement` row is the audit trail for a stock change; a `StockLevel` row is the current on-hand quantity for one `(product, warehouse)` pair.

`services/stock.py::post_movement` is the single way stock-level deltas are written:

1. Validate the product and warehouse exist and, for a transfer, that the destination differs from the source.
2. Look up or create the source `StockLevel` row (lazy — a product doesn't need a row at every warehouse).
3. Apply the delta:
   - `in`: `+quantity` at source warehouse.
   - `out`: `-quantity` at source; refuse if the current on-hand is below the request.
   - `transfer`: `-quantity` at source, `+quantity` at destination (lazily created).
4. Insert the `StockMovement` row recording the request.
5. Commit the session. All four writes land in one transaction; on any failure, `db.rollback()` discards every change so the movement log cannot drift from stock levels.

The movement table is append-only. The router exposes `GET` endpoints for list and detail, and a `POST` to create, but no update or delete — mutating history would break the audit trail.

## Purchase-order receipt

Purchase orders move `draft → placed → received`, with `cancelled` reachable from `draft` or `placed`. `services/purchase_order.py::transition` enforces the state machine. The only transition that writes stock is `placed → received`:

For each `PurchaseOrderLine` on the PO, the service applies `+quantity` to the stock level at the PO's receiving warehouse **and** inserts an `IN` `StockMovement` with `reference = "PO:<id>"`. All of that, plus the PO's `status` and `received_at` writes, commit in one transaction. The `POST /purchase-orders/{id}/receive` endpoint is a thin wrapper that bridges a `draft` straight to `received` by first transitioning to `placed`.

An attempt to receive a PO with no lines raises `POError` so stock cannot drift silently.

## Low-stock alerts

`services/stock.py::low_stock_products` computes alerts on demand — there is no denormalized flag on `Product`. For each product it sums `on_hand` across every `StockLevel` row (optionally filtered to a single warehouse) and emits an alert when `sum(on_hand) <= reorder_point`. Computing on read keeps the write path simple: nothing in `post_movement` or the PO receipt needs to maintain an alert cache.

`GET /low-stock-alerts?warehouse_id=<id>` surfaces the list; without the filter, it checks each product's total across the whole business.

## CSV import / export

`csv_io.py` is a thin set of helpers that wrap the stdlib `csv` module:

- `parse_csv(text)` returns `(fieldnames, rows)` with each row as a plain `dict`.
- `serialize_csv(fieldnames, rows)` produces header-plus-rows text; `None` values are written as empty strings.
- `import_rows(rows, required, handler)` iterates rows, enforces the list of required fields, delegates persistence to the caller's `handler(row)`, and collects `{"row": idx, "error": msg, "data": row}` for any row the handler rejects. A validation error on one row never aborts the batch — the endpoint returns `{"imported": n, "errors": [...]}` so the caller can fix bad rows and re-upload.

The CSV router lives at `routers/csv_router.py` and ships import+export for products and suppliers. Export reads straight from the models; import upserts by natural key (`sku` for products, `name` for suppliers) so round-tripping an export is idempotent.
