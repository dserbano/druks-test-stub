"""Template rendering.

Uses Jinja2 when it's installed; otherwise a tiny, well-defined
fallback engine covering ``{{ var }}``, ``{% if %}``, ``{% for %}``,
and ``{% include %}``. The fallback exists so tests collect in
environments without Jinja2 — real deployments install the dependency.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional

try:  # pragma: no cover - import guard
    import jinja2

    _HAS_JINJA = True
except Exception:  # pragma: no cover
    jinja2 = None
    _HAS_JINJA = False


class TemplateError(RuntimeError):
    pass


class TemplateEngine:
    def __init__(self, search_dirs: Iterable[Path]):
        self.search_dirs = [Path(p) for p in search_dirs]
        if _HAS_JINJA:
            self.env = jinja2.Environment(
                loader=jinja2.FileSystemLoader([str(p) for p in self.search_dirs]),
                autoescape=False,
                keep_trailing_newline=True,
            )
        else:
            self.env = None

    def render(self, template_name: str, context: Mapping[str, Any]) -> str:
        if self.env is not None:
            return self.env.get_template(template_name).render(**context)
        for d in self.search_dirs:
            p = d / template_name
            if p.exists():
                return _render_fallback(p.read_text(encoding="utf-8"), context, d)
        raise TemplateError(f"template not found: {template_name}")

    def render_string(self, source: str, context: Mapping[str, Any], base_dir: Optional[Path] = None) -> str:
        if self.env is not None:
            return self.env.from_string(source).render(**context)
        return _render_fallback(source, context, base_dir or Path("."))


# ---------------------------------------------------------------------------
# Fallback engine: parse → tree of nodes → walk.
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.DOTALL)


@dataclass
class _Txt:
    text: str


@dataclass
class _Var:
    expr: str


@dataclass
class _If:
    cond: str
    body: List


@dataclass
class _For:
    var: str
    iter_expr: str
    body: List


@dataclass
class _Include:
    name: str


def _tokenize(source: str) -> List[str]:
    return [t for t in _TOKEN_RE.split(source) if t != ""]


def _parse_tokens(tokens: List[str], pos: int, terminator: Optional[str] = None):
    nodes = []
    while pos < len(tokens):
        tok = tokens[pos]
        if tok.startswith("{{") and tok.endswith("}}"):
            nodes.append(_Var(tok[2:-2].strip()))
            pos += 1
            continue
        if tok.startswith("{%") and tok.endswith("%}"):
            inner = tok[2:-2].strip()
            if terminator and inner == terminator:
                return nodes, pos + 1
            if inner.startswith("if "):
                body, pos = _parse_tokens(tokens, pos + 1, "endif")
                nodes.append(_If(inner[3:].strip(), body))
                continue
            if inner.startswith("for "):
                m = re.match(r"for\s+(\w+)\s+in\s+(.+)", inner)
                if not m:
                    pos += 1
                    continue
                body, pos = _parse_tokens(tokens, pos + 1, "endfor")
                nodes.append(_For(m.group(1), m.group(2).strip(), body))
                continue
            if inner.startswith("include "):
                nm = inner[len("include "):].strip().strip('"').strip("'")
                nodes.append(_Include(nm))
                pos += 1
                continue
            # Unknown tag — ignore.
            pos += 1
            continue
        nodes.append(_Txt(tok))
        pos += 1
    return nodes, pos


def _resolve(expr: str, ctx: Mapping[str, Any]) -> Any:
    expr = expr.strip()
    parts = expr.split(".")
    cur: Any
    if isinstance(ctx, Mapping):
        cur = ctx.get(parts[0])
    else:
        cur = getattr(ctx, parts[0], None)
    for part in parts[1:]:
        if cur is None:
            return ""
        if isinstance(cur, Mapping):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
    return "" if cur is None else cur


def _render_nodes(nodes, ctx, base_dir) -> str:
    out = []
    for node in nodes:
        if isinstance(node, _Txt):
            out.append(node.text)
        elif isinstance(node, _Var):
            out.append(str(_resolve(node.expr, ctx)))
        elif isinstance(node, _If):
            if bool(_resolve(node.cond, ctx)):
                out.append(_render_nodes(node.body, ctx, base_dir))
        elif isinstance(node, _For):
            iterable = _resolve(node.iter_expr, ctx) or []
            for item in iterable:
                scope = dict(ctx) if isinstance(ctx, Mapping) else {}
                scope[node.var] = item
                out.append(_render_nodes(node.body, scope, base_dir))
        elif isinstance(node, _Include):
            p = base_dir / node.name
            if p.exists():
                out.append(_render_fallback(p.read_text(encoding="utf-8"), ctx, base_dir))
    return "".join(out)


def _render_fallback(source: str, ctx: Mapping[str, Any], base_dir: Path) -> str:
    tokens = _tokenize(source)
    tree, _ = _parse_tokens(tokens, 0, None)
    return _render_nodes(tree, ctx, base_dir)


def render_template(template: str, context: Mapping[str, Any], search_dirs: Iterable[Path]):
    return TemplateEngine(search_dirs).render(template, context)
