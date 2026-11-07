# sitegen — overview

`sitegen` is a pure-Python static site generator that turns a tree of
markdown and a TOML config into a static HTML site. It has no runtime
dependencies outside Python ≥ 3.11, Jinja2, and watchdog.

## What it ships

- A **markdown parser** written from scratch that targets CommonMark
  0.30 — headings (ATX and Setext), ordered/unordered nested lists,
  pipe tables, fenced and indented code blocks, blockquotes, thematic
  breaks, footnote definitions, link reference definitions, raw HTML
  blocks; inline emphasis/strong, inline code, inline + reference
  links, images, autolinks, raw inline HTML, footnote references.
  See [CommonMark 0.30](https://spec.commonmark.org/0.30/).
- A **template layer** built on Jinja2 (with a tiny fallback engine
  for hermetic test runs).
- **Themes**, rooted at either the project's `themes/` directory or
  the built-in set under `app/sitegen/themes_builtin/`.
- **Tags** with per-tag index pages.
- **RSS 2.0** and **sitemap.xml** emission for every rendered page.
- **Incremental builds** driven by a content-hash manifest; template,
  theme, or plugin changes invalidate the entire site.
- A **dev server** with SSE-based live reload and a watchdog-backed
  file watcher.
- A **plugin registry** with `before_build`, `on_page`, and
  `after_build` hook points and a built-in reading-time plugin
  shipped as reference.

## Minimal usage

```bash
sitegen build ./site ./public
sitegen serve ./site ./public
```

See the other pages for details:

- [CLI reference](cli.md)
- [Configuration schema](config.md)
- [Theme authoring](themes.md)
- [Plugin authoring](plugins.md)
