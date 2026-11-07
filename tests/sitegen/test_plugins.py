"""Plugin registry tests + the built-in demo plugin."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import pytest

from app.sitegen import plugins
from app.sitegen.plugins import HOOKS, PluginRegistry


@dataclass
class FakePage:
    title: str = "p"
    content: str = ""
    meta: Dict = field(default_factory=dict)


def test_registry_has_all_hooks():
    r = PluginRegistry()
    for h in HOOKS:
        assert h in r.hooks
        assert r.hooks[h] == []


def test_register_appends_in_order():
    r = PluginRegistry()
    r.register("on_page", lambda p: None)
    r.register("on_page", lambda p: None)
    assert len(r.hooks["on_page"]) == 2


def test_register_unknown_hook_raises():
    r = PluginRegistry()
    with pytest.raises(ValueError):
        r.register("after_apocalypse", lambda: None)


def test_invoke_calls_handlers_in_order():
    r = PluginRegistry()
    calls = []
    r.on_page(lambda p: calls.append(("a", p)))
    r.on_page(lambda p: calls.append(("b", p)))
    page = FakePage()
    r.invoke("on_page", page)
    assert [c[0] for c in calls] == ["a", "b"]


def test_invoke_returns_results():
    r = PluginRegistry()
    r.register("before_build", lambda: 1)
    r.register("before_build", lambda: 2)
    assert r.invoke("before_build") == [1, 2]


def test_decorator_registration():
    r = PluginRegistry()

    @r.on_page
    def h(p):
        p.meta["ran"] = True
        return p

    page = FakePage()
    r.invoke("on_page", page)
    assert page.meta.get("ran") is True


def test_before_build_hook_fires_with_args():
    r = PluginRegistry()
    seen = {}
    r.before_build(lambda **kw: seen.update(kw))
    r.invoke("before_build", site="s", src="src", out="out")
    assert seen == {"site": "s", "src": "src", "out": "out"}


def test_after_build_hook():
    r = PluginRegistry()
    calls = []
    r.after_build(lambda **kw: calls.append(kw))
    r.invoke("after_build", site="s", src="src", out="out", pages=[])
    assert len(calls) == 1


def test_on_page_mutation_persists():
    r = PluginRegistry()
    r.on_page(lambda p: p.meta.__setitem__("x", 1))
    page = FakePage()
    r.invoke("on_page", page)
    assert page.meta["x"] == 1


def test_builtin_plugin_registers_on_page():
    r = PluginRegistry()
    plugins.register(r)
    assert len(r.hooks["on_page"]) == 1


def test_builtin_plugin_sets_reading_time():
    r = PluginRegistry()
    plugins.register(r)
    page = FakePage(content="word " * 400)
    r.invoke("on_page", page)
    assert page.meta.get("reading_time") == 2


def test_builtin_plugin_at_least_one_minute():
    r = PluginRegistry()
    plugins.register(r)
    page = FakePage(content="")
    r.invoke("on_page", page)
    assert page.meta.get("reading_time") == 1
