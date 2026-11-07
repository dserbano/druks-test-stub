"""Theme discovery and resolution."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Theme:
    name: str
    root: Path

    @property
    def templates_dir(self) -> Path:
        return self.root / "templates"

    @property
    def static_dir(self) -> Path:
        return self.root / "static"

    def copy_static(self, dst: Path) -> List[Path]:
        """Copy the theme's static assets into ``dst``. Returns copied files."""
        copied: List[Path] = []
        if not self.static_dir.exists():
            return copied
        for src in self.static_dir.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(self.static_dir)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            copied.append(target)
        return copied


_BUILTIN_DIR = Path(__file__).parent / "themes_builtin"


def builtin_theme_dir() -> Path:
    return _BUILTIN_DIR


def discover_theme(name: str, themes_dir: Optional[Path] = None) -> Theme:
    """Locate a theme by name.

    Search order:
      1. ``themes_dir/<name>``
      2. ``app/sitegen/themes_builtin/<name>``
    """
    if themes_dir is not None:
        candidate = Path(themes_dir) / name
        if candidate.is_dir():
            return Theme(name=name, root=candidate)
    builtin = _BUILTIN_DIR / name
    if builtin.is_dir():
        return Theme(name=name, root=builtin)
    raise FileNotFoundError(f"theme not found: {name}")
