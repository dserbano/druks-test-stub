# Theme authoring

A theme is a directory with a `templates/` and (optionally) `static/`
subdirectory:

```
themes/my-theme/
  templates/
    page.html
    tag.html
    base.html         # optional, can be included from others
  static/
    style.css
    favicon.ico
```

`sitegen` looks for themes under the project's `themes_dir` first,
then falls back to `app/sitegen/themes_builtin/`. The built-in
`default` theme is a working minimum you can copy from.

## Required templates

- `page.html` — renders a single page. Receives `site` (the site
  config as a dict) and `page` with keys `title`, `content`
  (HTML string), `url`, `meta`.
- `tag.html` — renders a per-tag index. Receives `site`, `tag`
  (string), and `pages` (list of `{title, url}`).

## Static assets

Every file under `static/` is copied verbatim into the output root
during build. Paths are preserved (so `static/img/logo.png` becomes
`/img/logo.png`).

## Live reload

Live reload is handled by the dev server, which injects a small
`<script>` tag into every HTML response just before `</body>`. The
script opens an `EventSource` connection to `/__sitegen/reload` and
calls `location.reload()` when a `reload` event arrives.

Your theme does not need to add anything — the injection is the
transport, and it kicks in whenever your page has a `</body>` tag (or
is appended if it does not). To opt a specific page out of reload,
omit the `</body>` tag *and* ensure the snippet is not present in the
page source.

If you prefer to control the snippet's position yourself, include it
verbatim in your template:

```html
<script>(function(){var es=new EventSource('/__sitegen/reload');
es.addEventListener('reload',function(){location.reload();});})();</script>
```

The injector is idempotent: pages that already contain the snippet
byte-for-byte are served unchanged.
