# Dashboard

The dashboard is rendered as a single static HTML file by
`app.tracker.dashboard`. There is no HTTP server — the renderer takes a
connection, writes to the given path, and returns.

## Sections

- **Projects** (`id="projects"`) — project id, name, description.
- **Sprint burndown** (`id="sprint-burndown"`) — remaining and
  completed estimate per day for the selected sprint. Defaults to the
  earliest-starting sprint; pass `sprint_id` to pick another.
- **Open tasks per assignee** (`id="tasks-per-assignee"`) — per
  assignee, count of tasks not in `done`.
- **Search results** (`id="search-results"`) — ranked matches for the
  provided `search_term` across projects, tasks and comments.

## Programmatic use

```python
from app.tracker import db, migrations, dashboard
conn = db.connect("tracker.db")
migrations.apply(conn)
dashboard.render(conn, "dashboard.html", search_term="cache")
```

`dashboard.render_string(conn, ...)` returns the HTML as a string
instead of writing to disk, which is useful in tests.
