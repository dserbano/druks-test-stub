"""Site configuration.

A site's top-level ``site.toml`` is parsed into a :class:`SiteConfig`.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class SiteConfig:
    title: str = "Site"
    base_url: str = ""
    description: str = ""
    author: str = ""
    theme: str = "default"
    language: str = "en"
    output_dir: str = "public"
    content_dir: str = "content"
    static_dir: str = "static"
    themes_dir: str = "themes"
    plugins: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


def load_config(path: Path) -> SiteConfig:
    """Load a site config from a TOML file."""
    path = Path(path)
    with path.open("rb") as f:
        data = tomllib.load(f)
    site = data.get("site", {}) or {}
    cfg = SiteConfig(
        title=site.get("title", "Site"),
        base_url=site.get("base_url", ""),
        description=site.get("description", ""),
        author=site.get("author", ""),
        theme=site.get("theme", "default"),
        language=site.get("language", "en"),
        output_dir=site.get("output_dir", "public"),
        content_dir=site.get("content_dir", "content"),
        static_dir=site.get("static_dir", "static"),
        themes_dir=site.get("themes_dir", "themes"),
        plugins=list(site.get("plugins", [])),
        extra={k: v for k, v in data.items() if k != "site"},
    )
    return cfg
