"""Dev server reload-dispatch and watcher-callback tests.

Exercises the in-process logic — no real socket is opened.
"""
from __future__ import annotations

import queue

import pytest

from app.sitegen.server import (
    RELOAD_PATH,
    RELOAD_SNIPPET,
    ReloadDispatcher,
    WatcherState,
    watcher_callback,
)


def test_dispatcher_starts_empty():
    d = ReloadDispatcher()
    assert d.subscriber_count == 0


def test_dispatcher_subscribe_increments_count():
    d = ReloadDispatcher()
    d.subscribe()
    assert d.subscriber_count == 1


def test_dispatcher_unsubscribe_decrements_count():
    d = ReloadDispatcher()
    q = d.subscribe()
    d.unsubscribe(q)
    assert d.subscriber_count == 0


def test_dispatch_to_zero_subscribers_returns_zero():
    d = ReloadDispatcher()
    assert d.dispatch() == 0


def test_dispatch_delivers_event_to_subscriber():
    d = ReloadDispatcher()
    q = d.subscribe()
    n = d.dispatch(event="reload", data="x.md")
    assert n == 1
    event, data = q.get(timeout=0.1)
    assert event == "reload"
    assert data == "x.md"


def test_dispatch_broadcasts_to_many_subscribers():
    d = ReloadDispatcher()
    qs = [d.subscribe() for _ in range(5)]
    n = d.dispatch(event="reload", data="x")
    assert n == 5
    for q in qs:
        assert q.get(timeout=0.1)[0] == "reload"


def test_watcher_callback_fires_dispatch():
    d = ReloadDispatcher()
    q = d.subscribe()
    state = WatcherState(dispatcher=d)
    n = watcher_callback(state, "/tmp/foo.md")
    assert n == 1
    assert q.get(timeout=0.1)[1] == "/tmp/foo.md"


def test_watcher_callback_records_event_path():
    d = ReloadDispatcher()
    state = WatcherState(dispatcher=d)
    watcher_callback(state, "/tmp/a")
    watcher_callback(state, "/tmp/b")
    assert state.events == ["/tmp/a", "/tmp/b"]


def test_watcher_callback_runs_rebuild_hook():
    d = ReloadDispatcher()
    calls = []
    state = WatcherState(dispatcher=d, rebuild=lambda: calls.append(1))
    watcher_callback(state, "/x")
    assert calls == [1]


def test_watcher_callback_without_rebuild_is_safe():
    d = ReloadDispatcher()
    state = WatcherState(dispatcher=d)
    watcher_callback(state, "/x")  # must not raise


def test_reload_path_is_canonical():
    assert RELOAD_PATH == "/__sitegen/reload"


def test_reload_snippet_contains_event_source():
    assert "EventSource" in RELOAD_SNIPPET
    assert RELOAD_PATH in RELOAD_SNIPPET


def test_make_handler_sets_dispatcher(tmp_path):
    from app.sitegen.server import make_handler
    d = ReloadDispatcher()
    cls = make_handler(tmp_path, d)
    assert cls.dispatcher is d
    assert cls.directory == str(tmp_path)
