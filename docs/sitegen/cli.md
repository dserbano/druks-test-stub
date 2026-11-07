# CLI reference

`sitegen` exposes two subcommands.

## `sitegen build <src> <out>`

Builds the site at `<src>` into `<out>`. The source tree must contain
the content directory named by `site.content_dir` (defaults to
`content/`) and a `site.toml` at the root, unless overridden with
`--config`.

Options:

- `--config PATH` — explicit path to a site config file (TOML).

`python -m app.sitegen build <src> <out>` is equivalent and works
without the installed console entry.

Exit code 0 on success. Writes a `.sitegen-manifest.json` into the
output directory for incremental runs.

## `sitegen serve <src> <out>`

Builds once, then serves `<out>` over HTTP and watches `<src>` for
changes. Any file change triggers a rebuild and sends a `reload`
event to all connected Server-Sent-Events clients at
`/__sitegen/reload`. Every HTML response passes through an injector
that inserts a tiny `<script>` subscribing to that endpoint, so no
theme change is required for reload to work.

Options:

- `--host` (default `127.0.0.1`)
- `--port` (default `8000`)
- `--config PATH`
