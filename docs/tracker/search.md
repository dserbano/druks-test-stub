# Full-text search

`app.tracker.search` exposes a thin wrapper around three SQLite FTS5
virtual tables:

- `projects_fts(name, description)`
- `tasks_fts(title, description)`
- `comments_fts(body)`

Triggers on the base tables mirror inserts, updates and deletes into
the FTS tables, so there is no explicit reindex step for normal
writes.

## API

```python
from app.tracker import search
search.search_projects(conn, "widget")
search.search_tasks(conn, "widget")
search.search_comments(conn, "widget")
search.search_all(conn, "widget", limit=20)
```

Each call returns a list of `SearchHit(kind, rowid, snippet, rank)`
with `rank` from SQLite's `bm25()` (lower is better). `search_all`
interleaves hits from the three indexes and sorts by rank.

Empty or whitespace-only queries return an empty list.

## Reindex

`search.rebuild_indexes(conn)` forces a full rebuild of every FTS
index from the base content tables. Use after bulk imports if you
bypassed the trigger path.
