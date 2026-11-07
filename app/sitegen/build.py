"""Site build pipeline.

Reads a source tree (markdown + TOML config) and emits an HTML site.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .config import SiteConfig, load_config
from .feeds import render_rss, render_sitemap
from .incremental import MANIFEST_NAME, Manifest, hash_bytes, hash_tree, plan_rebuild
from .parser import render as md_render
from .plugins import PluginRegistry, load_plugin
from .plugins import register as builtin_register
from .tags import TagIndex, slugify
from .templates import TemplateEngine
from .themes import discover_theme


FRONT_MATTER_RE = re.compile(r"^\+\+\+\n(.*?)\n\+\+\+\n", re.DOTALL)


@dataclass
class Page:
    source: Path
    rel: str
    title: str = ""
    date: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    summary: str = ""
    body_md: str = ""
    content: str = ""  # rendered HTML body
    url: str = ""
    meta: Dict = field(default_factory=dict)


def _parse_front_matter(text: str):
    import tomllib
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    meta = tomllib.loads(m.group(1))
    return meta, text[m.end():]


def discover_sources(root: Path) -> List[Path]:
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def load_page(src: Path, content_root: Path) -> Page:
    rel = src.relative_to(content_root).as_posix()
    text = src.read_text(encoding="utf-8")
    meta, body = _parse_front_matter(text)
    page = Page(
        source=src,
        rel=rel,
        title=meta.get("title", src.stem),
        tags=list(meta.get("tags", [])),
        summary=meta.get("summary", ""),
        body_md=body,
        meta=dict(meta),
    )
    if "date" in meta:
        d = meta["date"]
        if isinstance(d, datetime):
            page.date = d
        elif isinstance(d, str):
            try:
                page.date = datetime.fromisoformat(d)
            except ValueError:
                page.date = None
    return page


def _url_for(rel: str) -> str:
    stem = rel[:-3] if rel.endswith(".md") else rel
    if stem == "index":
        return "/"
    if stem.endswith("/index"):
        stem = stem[: -len("/index")] + "/"
    else:
        stem = stem + "/"
    return "/" + stem.lstrip("/")


def _output_path(out: Path, url: str) -> Path:
    if url.endswith("/"):
        return out / url.lstrip("/") / "index.html"
    return out / (url.lstrip("/") + "/index.html")


@dataclass
class BuildResult:
    rendered: List[Page] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    written: List[Path] = field(default_factory=list)


def build(
    src: Path,
    out: Path,
    *,
    config_path: Optional[Path] = None,
    registry: Optional[PluginRegistry] = None,
    use_builtin_plugin: bool = True,
) -> BuildResult:
    src = Path(src)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cfg_path = Path(config_path) if config_path else src / "site.toml"
    if cfg_path.exists():
        site = load_config(cfg_path)
    else:
        site = SiteConfig()
    content_root = src / site.content_dir
    if not content_root.exists():
        content_root = src
    theme = discover_theme(site.theme, src / site.themes_dir if (src / site.themes_dir).exists() else None)

    registry = registry or PluginRegistry()
    if use_builtin_plugin:
        builtin_register(registry)
    for plugin_path in site.plugins:
        load_plugin(plugin_path, registry)

    registry.invoke("before_build", site=site, src=src, out=out)

    # Load all pages.
    pages: List[Page] = []
    content_files: Dict[str, bytes] = {}
    for p in discover_sources(content_root):
        page = load_page(p, content_root)
        page.url = _url_for(page.rel)
        pages.append(page)
        content_files[page.rel] = p.read_bytes()

    # Incremental: compute global hash of templates/theme/plugins + config.
    aux = []
    aux.extend(theme.templates_dir.rglob("*")) if theme.templates_dir.exists() else None
    aux.extend(theme.static_dir.rglob("*")) if theme.static_dir.exists() else None
    if cfg_path.exists():
        aux.append(cfg_path)
    # Include plugin modules by path if they exist on disk.
    global_hash = hash_tree(aux)

    manifest_path = out / MANIFEST_NAME
    manifest = Manifest.load(manifest_path)
    to_render = plan_rebuild(content_files, manifest, global_hash)

    engine = TemplateEngine(search_dirs=[theme.templates_dir])
    result = BuildResult()

    for page in pages:
        # Render body first so plugins see the HTML.
        page.content = md_render(page.body_md)
        registry.invoke("on_page", page)
        if page.rel not in to_render:
            result.skipped.append(page.rel)
            continue
        html = engine.render(
            "page.html",
            {"site": site.__dict__, "page": {"title": page.title, "content": page.content, "url": page.url, "meta": page.meta}},
        )
        dst = _output_path(out, page.url)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(html, encoding="utf-8")
        manifest.update(page.rel, hash_bytes(content_files[page.rel]))
        result.rendered.append(page)
        result.written.append(dst)

    # Tag pages (always written — small and depend on the full page list).
    tag_index = TagIndex()
    tag_index.collect(pages)
    tag_root = out / "tags"
    for tag, tpages in tag_index.tags.items():
        slug = slugify(tag)
        dst = tag_root / slug / "index.html"
        dst.parent.mkdir(parents=True, exist_ok=True)
        html = engine.render(
            "tag.html",
            {
                "site": site.__dict__,
                "tag": tag,
                "pages": [{"title": p.title, "url": p.url} for p in tpages],
            },
        )
        dst.write_text(html, encoding="utf-8")
        result.written.append(dst)

    # RSS + sitemap
    (out / "rss.xml").write_text(render_rss(site, pages), encoding="utf-8")
    (out / "sitemap.xml").write_text(render_sitemap(site, pages), encoding="utf-8")
    result.written.extend([out / "rss.xml", out / "sitemap.xml"])

    # Static assets from theme
    theme.copy_static(out)

    # Manifest
    manifest.global_hash = global_hash
    # Prune stale entries.
    manifest.sources = {k: v for k, v in manifest.sources.items() if k in content_files}
    manifest.save(manifest_path)

    registry.invoke("after_build", site=site, src=src, out=out, pages=pages)
    return result
