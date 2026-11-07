# Tracker overview

`app/tracker/` is a self-contained project tracker built on the Python
standard library plus Jinja2. Everything lives in-process against a
SQLite database file (or `:memory:` for tests).

## Layout

```
app/tracker/
  __init__.py           # re-exports submodules
  __main__.py           # python -m app.tracker CLI
  db.py                 # connection helpers
  migrations/           # ordered .sql files + runner
  models/               # one module per entity
    project.py
    task.py
    subtask.py
    dependency.py
    assignee.py
    sprint.py
    comment.py
    label.py
  search.py             # SQLite FTS5 over projects / tasks / comments
  burndown.py           # sprint remaining-work series
  dashboard.py          # Jinja-driven static HTML renderer
  seed.py               # representative dataset
  templates/
    dashboard.html.j2
```

Related documents:

- [data-model.md](data-model.md) — tables and relationships
- [cli.md](cli.md) — CLI reference
- [migrations.md](migrations.md) — migration workflow
- [dashboard.md](dashboard.md) — dashboard rendering
- [search.md](search.md) — full-text search
