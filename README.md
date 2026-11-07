# Make sure

- The Druks GitHub App has access to it.
- Your local Druks backend is running your modified code.
- GitHub webhooks can reach that backend.
- Your agent harness is c

## Development setup

### Installing dependencies

This repository is a minimal test project. No external dependencies are required for the current setup.

### Running tests

There is currently no automated test suite. If tests are added in the future, document the commands required to run them here.

## Inventory app

An inventory management FastAPI app lives under `app/inventory/`. It exposes REST endpoints for products, suppliers, warehouses, stock movements, purchase orders, and low-stock alerts, with CSV import and export for products and suppliers. Full design notes are in `app/inventory/ARCHITECTURE.md`.

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
```

The runtime dependencies (`fastapi`, `sqlalchemy`, `pydantic`, `python-multipart`) are declared in `pyproject.toml`; `pytest` and `httpx` are the test extras.

### Run the app

```bash
uvicorn --factory app.inventory.main:create_app
```

The app creates a SQLite database file (`inventory.db` by default) on startup. Point it elsewhere with `INVENTORY_DB_URL=sqlite:///./alt.db`.

### Run the inventory test suite

```bash
pytest tests/inventory/
```

Each test uses an isolated in-memory SQLite database created by the `tests/inventory/conftest.py` fixtures, so tests do not share state.

Reviewer access restored: operator changes receive an independent review.
test: merge-done
test: t-l10
test: jira-mcp-2
test: 937-approve
test: report-approve
test: s9
test: x3
test: x3-round2
test: x5
