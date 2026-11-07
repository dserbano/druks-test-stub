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


def test_inject_reload_snippet_before_body_close():
    from app.sitegen.server import inject_reload_snippet
    html = b"<html><body><h1>hi</h1></body></html>"
    out = inject_reload_snippet(html)
    assert b"EventSource" in out
    assert out.index(b"EventSource") < out.index(b"</body>")


def test_inject_reload_snippet_is_idempotent():
    from app.sitegen.server import inject_reload_snippet
    html = b"<html><body></body></html>"
    once = inject_reload_snippet(html)
    twice = inject_reload_snippet(once)
    assert once == twice


def test_inject_reload_snippet_appends_when_no_body_close():
    from app.sitegen.server import inject_reload_snippet
    html = b"<html><p>no body tag</p>"
    out = inject_reload_snippet(html)
    assert out.endswith(RELOAD_SNIPPET.encode("utf-8"))


def test_inject_reload_snippet_handles_uppercase_body():
    from app.sitegen.server import inject_reload_snippet
    html = b"<HTML><BODY>x</BODY></HTML>"
    out = inject_reload_snippet(html)
    assert b"EventSource" in out
    assert out.index(b"EventSource") < out.lower().index(b"</body>")


def test_built_pages_served_with_reload_script_injected(tmp_path):
    """Integration-ish: a built HTML page served by the handler carries the
    reload script even when the file on disk does not.
    """
    import io
    from app.sitegen.server import make_handler
    (tmp_path / "index.html").write_text(
        "<html><body>hello</body></html>", encoding="utf-8"
    )
    d = ReloadDispatcher()
    cls = make_handler(tmp_path, d)

    captured = io.BytesIO()

    class FakeReq:
        def makefile(self, *a, **kw):
            return io.BytesIO(b"")

    class FakeHandler(cls):  # type: ignore[misc,valid-type]
        def __init__(self):
            # Don't go through BaseHTTPRequestHandler.__init__ — we just
            # want to drive the HTML-serving path.
            self.path = "/"
            self.command = "GET"
            self.directory = str(tmp_path)
            self.wfile = captured
            self.rfile = io.BytesIO(b"")
            self.headers = {}
            self.request_version = "HTTP/1.0"

        def send_response(self, code, message=None):
            captured.write(f"HTTP/1.0 {code}\r\n".encode("ascii"))

        def send_header(self, k, v):
            captured.write(f"{k}: {v}\r\n".encode("ascii"))

        def end_headers(self):
            captured.write(b"\r\n")

        def log_message(self, *a, **kw):
            pass

    h = FakeHandler()
    h.do_GET()
    out = captured.getvalue()
    assert b"EventSource" in out
    assert b"hello" in out


def test_resolve_html_path_rejects_traversal(tmp_path):
    from app.sitegen.server import make_handler
    cls = make_handler(tmp_path, ReloadDispatcher())

    class _H(cls):  # type: ignore[misc,valid-type]
        def __init__(self, path):
            self.path = path
            self.directory = str(tmp_path)

    assert _H("/../etc/passwd")._resolve_html_path() is None
