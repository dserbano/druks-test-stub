"""Development server with live reload (SSE transport).

The server is a stdlib ``http.server.ThreadingHTTPServer`` serving the
output directory, plus:

* a Server-Sent-Events endpoint at ``/__sitegen/reload`` that publishes a
  ``reload`` event whenever :func:`notify_reload` is called,
* a watcher that calls :func:`notify_reload` (via :func:`watcher_callback`)
  every time a watched source file changes.

Tests exercise :class:`ReloadDispatcher` and :func:`watcher_callback`
directly, without opening a real socket — the socket code paths are kept
small so the reload *logic* is unit-testable.
"""
from __future__ import annotations

import posixpath
import queue
import threading
import urllib.parse
from dataclasses import dataclass, field
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, List, Optional

try:  # pragma: no cover - import guard
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    _HAS_WATCHDOG = True
except Exception:  # pragma: no cover
    FileSystemEventHandler = object  # type: ignore[assignment,misc]
    Observer = None  # type: ignore[assignment]
    _HAS_WATCHDOG = False


RELOAD_PATH = "/__sitegen/reload"
RELOAD_SNIPPET = (
    "<script>(function(){"
    "var es=new EventSource('" + RELOAD_PATH + "');"
    "es.addEventListener('reload',function(){location.reload();});"
    "})();</script>"
)


def inject_reload_snippet(html: bytes, snippet: str = RELOAD_SNIPPET) -> bytes:
    """Return ``html`` with the SSE reload snippet inserted before ``</body>``.

    Falls back to appending if no closing body tag is present. If the
    snippet is already present (byte-equal) the html is returned
    unchanged — injection is idempotent, which keeps the test for
    "served HTML includes the reload script" stable across re-reads.
    """
    enc = snippet.encode("utf-8")
    if enc in html:
        return html
    lower = html.lower()
    idx = lower.rfind(b"</body>")
    if idx == -1:
        return html + enc
    return html[:idx] + enc + html[idx:]


class ReloadDispatcher:
    """Fan-out of reload events to all connected SSE clients."""

    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: List[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def dispatch(self, event: str = "reload", data: str = "") -> int:
        """Send ``event`` to every subscriber. Returns the number of recipients."""
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            q.put((event, data))
        return len(subs)


@dataclass
class WatcherState:
    dispatcher: ReloadDispatcher
    rebuild: Optional[Callable[[], None]] = None
    events: List[str] = field(default_factory=list)


def watcher_callback(state: WatcherState, path: str) -> int:
    """Called by the file-watcher on every change event.

    Records the change, optionally re-runs the build, and fires a reload
    dispatch. Returns the number of subscribers notified.
    """
    state.events.append(path)
    if state.rebuild is not None:
        state.rebuild()
    return state.dispatcher.dispatch(event="reload", data=path)


class _InjectingHandler(SimpleHTTPRequestHandler):
    dispatcher: Optional[ReloadDispatcher] = None
    directory: str = "."

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory or self.directory, **kwargs)

    def do_GET(self):  # noqa: N802
        if self.path == RELOAD_PATH:
            return self._do_sse()
        resolved = self._resolve_html_path()
        if resolved is not None:
            return self._serve_html_with_snippet(resolved)
        return super().do_GET()

    def _resolve_html_path(self) -> Optional[Path]:
        """Return a filesystem Path when this request maps to an HTML file.

        Mirrors ``SimpleHTTPRequestHandler.translate_path`` for the
        subset we care about: strip query/fragment, decode percent-
        escapes, resolve against the configured directory, and apply
        the "/dir/" → "/dir/index.html" rule. Any resolved path that
        escapes ``self.directory`` returns ``None`` — the base handler
        then takes over and applies its own protections.
        """
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        try:
            path = urllib.parse.unquote(path, errors="surrogatepass")
        except (UnicodeDecodeError, TypeError):
            return None
        trailing_slash = path.endswith("/")
        path = posixpath.normpath(path)
        while path.startswith("/"):
            path = path[1:]
        parts = [p for p in path.split("/") if p and p != "."]
        if any(p == ".." for p in parts):
            return None
        fs = Path(self.directory, *parts) if parts else Path(self.directory)
        if fs.is_dir() or trailing_slash:
            fs = fs / "index.html"
        try:
            resolved = fs.resolve(strict=False)
            root = Path(self.directory).resolve(strict=False)
            resolved.relative_to(root)
        except (ValueError, OSError):
            return None
        if fs.suffix.lower() in (".html", ".htm") and fs.is_file():
            return fs
        return None

    def _serve_html_with_snippet(self, fs: Path) -> None:
        try:
            raw = fs.read_bytes()
        except OSError:
            self.send_error(404)
            return
        body = inject_reload_snippet(raw)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):  # pragma: no cover
                pass

    def _do_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.dispatcher is None:
            return
        q = self.dispatcher.subscribe()
        try:
            while True:
                try:
                    event, data = q.get(timeout=30)
                except queue.Empty:
                    try:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        break
                    continue
                try:
                    self.wfile.write(f"event: {event}\n".encode("utf-8"))
                    self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
        finally:
            self.dispatcher.unsubscribe(q)


class _WatchdogHandler(FileSystemEventHandler):  # pragma: no cover - thin shim
    def __init__(self, state: WatcherState):
        self.state = state

    def on_modified(self, event):
        if getattr(event, "is_directory", False):
            return
        watcher_callback(self.state, getattr(event, "src_path", ""))

    def on_created(self, event):
        if getattr(event, "is_directory", False):
            return
        watcher_callback(self.state, getattr(event, "src_path", ""))


def make_handler(output_dir: Path, dispatcher: ReloadDispatcher):
    class _H(_InjectingHandler):
        pass

    _H.dispatcher = dispatcher
    _H.directory = str(output_dir)
    return _H


def serve(
    src: Path,
    out: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    config_path=None,
):  # pragma: no cover - driven by hand, not unit-tested
    from .build import build as build_site

    build_site(Path(src), Path(out), config_path=config_path)
    dispatcher = ReloadDispatcher()
    state = WatcherState(dispatcher=dispatcher, rebuild=lambda: build_site(Path(src), Path(out), config_path=config_path))
    httpd = ThreadingHTTPServer((host, port), make_handler(Path(out), dispatcher))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    observer = None
    if _HAS_WATCHDOG:
        observer = Observer()
        observer.schedule(_WatchdogHandler(state), str(src), recursive=True)
        observer.start()
    print(f"serving on http://{host}:{port}")
    try:
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        if observer is not None:
            observer.stop()
            observer.join()
        httpd.shutdown()
