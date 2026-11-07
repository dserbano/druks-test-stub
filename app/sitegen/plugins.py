"""Plugin system.

Plugins are regular Python callables or classes that register themselves
against named hook points. The pipeline fires ``before_build``,
``on_page`` (once per rendered page, with the Page object), and
``after_build``. Registration order is preserved.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List

HOOKS = ("before_build", "on_page", "after_build")


@dataclass
class PluginRegistry:
    hooks: Dict[str, List[Callable]] = field(
        default_factory=lambda: {h: [] for h in HOOKS}
    )

    def register(self, hook: str, fn: Callable) -> None:
        if hook not in self.hooks:
            raise ValueError(f"unknown hook: {hook!r}")
        self.hooks[hook].append(fn)

    def before_build(self, fn: Callable) -> Callable:
        self.register("before_build", fn)
        return fn

    def on_page(self, fn: Callable) -> Callable:
        self.register("on_page", fn)
        return fn

    def after_build(self, fn: Callable) -> Callable:
        self.register("after_build", fn)
        return fn

    def invoke(self, hook: str, *args, **kwargs) -> List:
        if hook not in self.hooks:
            raise ValueError(f"unknown hook: {hook!r}")
        results = []
        for fn in self.hooks[hook]:
            results.append(fn(*args, **kwargs))
        return results


def load_plugin(path: str, registry: PluginRegistry) -> None:
    """Import a plugin by dotted module path and let it register itself.

    The plugin module must expose a top-level ``register(registry)`` callable.
    """
    mod = importlib.import_module(path)
    reg = getattr(mod, "register", None)
    if reg is None:
        raise AttributeError(f"plugin {path!r} has no register() function")
    reg(registry)


# ---------------------------------------------------------------------------
# Built-in demonstration plugin
# ---------------------------------------------------------------------------


def register(registry: PluginRegistry) -> None:
    """The built-in demo plugin.

    Adds a ``reading_time`` attribute to every page based on the word
    count in its rendered HTML. Intentionally small — serves as a
    reference for authoring custom plugins.
    """
    def _reading_time(page):
        words = len((page.content or "").split())
        minutes = max(1, round(words / 200))
        page.meta["reading_time"] = minutes

    registry.on_page(_reading_time)
