# CLI

Invoke the tracker through Python's `-m` runner.

```
python -m app.tracker <command> [options]
```

The CLI exits with status `2` on an unknown command or invalid
arguments (standard `argparse` behavior).

## `migrate`

Apply any pending migrations against the given SQLite file.

```
python -m app.tracker migrate --db ./tracker.db
```

Idempotent — running twice is a no-op on the second call.

## `seed`

Apply migrations and populate the representative dataset.

```
python -m app.tracker seed --db ./tracker.db
```

## `dashboard`

Render the static HTML dashboard.

```
python -m app.tracker dashboard \
  --db ./tracker.db \
  --output ./dashboard.html \
  --search "cache" \
  --sprint 1
```

`--search` is optional and controls which term is used in the search
section. `--sprint` picks a specific sprint id for the burndown
section (defaults to the earliest-starting sprint).
