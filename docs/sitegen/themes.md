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

If you want live reload to work in your theme, include the following
right before `</body>`:

```html
<script src="/__sitegen/reload.js" defer></script>
```

(The default theme does this automatically via `base.html`.)
