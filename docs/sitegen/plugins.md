# Plugin authoring

A plugin is any Python module exposing a `register(registry)` callable
that attaches handlers to one or more of the available hook points.

## Hook points

- `before_build(site, src, out)` — fires once before any page is
  rendered. Useful for preparing caches or validating config.
- `on_page(page)` — fires once per page, *after* the markdown body
  has been rendered to HTML and before the page template runs. The
  plugin can mutate `page.content`, `page.meta`, or any other field.
- `after_build(site, src, out, pages)` — fires once after all pages
  have been written.

Handlers fire in **registration order**: the first plugin registered
sees each page first.

## Example

```python
# my_pkg/word_count.py

def register(registry):
    @registry.on_page
    def add_word_count(page):
        page.meta["word_count"] = len(page.content.split())
```

Wire it up by adding the dotted path to `site.toml`:

```toml
[site]
plugins = ["my_pkg.word_count"]
```

## Built-in demo plugin

`app.sitegen.plugins` ships a `register` that attaches a
`reading_time` attribute (`int` minutes) to every page as a reference
implementation. The build pipeline loads it by default; disable it by
passing `use_builtin_plugin=False` to `build()` when calling the
builder as a library.
