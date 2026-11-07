# Migration workflow

Migrations live under `app/tracker/migrations/` and are plain SQL files
named `NNNN_<slug>.sql`. The runner (`app.tracker.migrations`)
discovers them, applies anything not yet recorded, and stamps the
version into a `schema_migrations` table.

## Writing a new migration

1. Pick the next `NNNN` prefix (zero-padded, four digits).
2. Save SQL to `app/tracker/migrations/NNNN_<slug>.sql`.
3. Use `CREATE TABLE IF NOT EXISTS` or similar idempotent statements
   where possible — the runner expects an apply to fail if the
   statements aren't safe for an already-migrated database.
4. If the migration introduces new searchable content, add FTS5
   triggers that mirror inserts/updates/deletes (see `0001_initial.sql`
   for the pattern).

## Running

```python
from app.tracker import db, migrations
conn = db.connect("tracker.db")
migrations.apply(conn)
```

`migrations.apply` returns the list of versions newly applied.
`migrations.pending(conn)` lets you inspect what would run.

## Rollbacks

There is no automatic rollback. For destructive changes, write a
forward-only migration that preserves the data you need, then follow
up with a cleanup migration once callers have migrated.
