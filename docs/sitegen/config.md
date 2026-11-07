# Configuration schema

`site.toml` lives at the root of a `sitegen` project. All keys live
under the `[site]` table.

```toml
[site]
title       = "My Site"
base_url    = "https://example.com"
description = "A site about things"
author      = "Someone"
theme       = "default"
language    = "en"
output_dir  = "public"
content_dir = "content"
static_dir  = "static"
themes_dir  = "themes"
plugins     = ["my_pkg.my_plugin"]
```

## Keys

| Key           | Type     | Default    | Meaning                                                   |
|---------------|----------|------------|-----------------------------------------------------------|
| `title`       | string   | `"Site"`   | Site title — used in templates and feeds.                 |
| `base_url`    | string   | `""`       | Absolute URL prefix used when emitting feeds and sitemap. |
| `description` | string   | `""`       | Site description — used by RSS.                           |
| `author`      | string   | `""`       | Optional author name.                                     |
| `theme`       | string   | `"default"`| Theme name — resolved under `themes/` then built-ins.     |
| `language`    | string   | `"en"`     | HTML `lang` attribute default.                            |
| `output_dir`  | string   | `"public"` | Where the CLI writes rendered files.                      |
| `content_dir` | string   | `"content"`| Where the builder looks for markdown sources.             |
| `static_dir`  | string   | `"static"` | Project-level static assets (future).                     |
| `themes_dir`  | string   | `"themes"` | Project-level theme search root.                          |
| `plugins`     | string[] | `[]`       | Dotted module paths to load (each needs `register`).      |

Any other top-level tables are preserved on `SiteConfig.extra` and are
available to templates that want to read them.

## Page front matter

Each markdown file may start with a TOML block delimited by `+++`:

```markdown
+++
title   = "A Page"
date    = "2026-01-01T12:00:00Z"
tags    = ["foo", "bar"]
summary = "One-line summary used by feeds."
+++
```

`title` defaults to the file's stem, `tags` defaults to the empty
list, `date` is parsed with `datetime.fromisoformat`.
