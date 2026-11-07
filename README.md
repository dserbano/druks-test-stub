# Make sure

- The Druks GitHub App has access to it.
- Your local Druks backend is running your modified code.
- GitHub webhooks can reach that backend.
- Your agent harness is c

## Development setup

### Installing dependencies

The `app/tracker/` package depends on Jinja2 at runtime and `pytest` for
development. Install both with:

```
pip install -e '.[dev]'
```

### Running tests

```
pytest
```

The tracker test suite lives under `tests/tracker/`.

### Tracker

`app/tracker/` contains a complete project tracker: projects, tasks,
subtasks, dependencies, assignees, sprints, labels, comments,
full-text search, a burndown calculator, and a static HTML dashboard
rendered with Jinja. See [docs/tracker/overview.md](docs/tracker/overview.md)
for a tour, and the other pages under `docs/tracker/` for the data
model, CLI, migrations, dashboard, and search.

CLI:

```
python -m app.tracker migrate --db ./tracker.db
python -m app.tracker seed --db ./tracker.db
python -m app.tracker dashboard --db ./tracker.db --output dashboard.html
```

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
