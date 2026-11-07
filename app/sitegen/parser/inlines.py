"""Inline-level markdown tokenizer.

Operates on the ``raw`` text stored on block-level nodes
(Paragraph, Heading, TableCell) and fills their ``children``
with inline AST nodes.
"""
from __future__ import annotations

import re
from typing import List as PyList, Tuple

from .ast import (
    Autolink,
    Document,
    Emphasis,
    FootnoteRef,
    Image,
    InlineCode,
    LineBreak,
    Link,
    Node,
    RawHTML,
    SoftBreak,
    Strong,
    Text,
)


_AUTOLINK_URL_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9+.\-]{1,31}:[^<>\x00-\x20]*)>")
_AUTOLINK_EMAIL_RE = re.compile(
    r"<([a-zA-Z0-9.!#$%&'*+/=?^_`{|}~\-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*)>"
)
_RAW_HTML_RE = re.compile(
    r"</?[a-zA-Z][a-zA-Z0-9\-]*(?:\s+[a-zA-Z_:][a-zA-Z0-9_.:\-]*(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'=<>`]+))?)*\s*/?>"
    r"|<!--[\s\S]*?-->"
    r"|<\?[\s\S]*?\?>"
    r"|<![A-Z][\s\S]*?>"
    r"|<!\[CDATA\[[\s\S]*?\]\]>"
)
_FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]]+)\]")


def parse_inlines(root: Node, link_refs, footnotes):
    """Walk the AST and parse inlines on nodes carrying a ``raw`` text."""
    for node in list(root.walk()):
        raw = getattr(node, "raw", None)
        if raw is None or node.children:
            # Nodes that already have children (block containers) have inlines
            # parsed on their raw-bearing leaf children instead.
            pass
        if raw:
            node.children = _parse_inline(raw, link_refs, footnotes)
            # Keep raw around so renderers can recover original if needed.


def _parse_inline(text: str, link_refs, footnotes) -> PyList[Node]:
    """Top-level inline parser."""
    tokens = _scan(text, link_refs, footnotes)
    return _pair_emphasis(tokens)


# ---------------------------------------------------------------------------
# Scanner: walks the text left-to-right turning it into a flat list of
# inline AST nodes plus "delimiter" markers that _pair_emphasis will
# resolve into Emphasis/Strong pairs.
# ---------------------------------------------------------------------------


class _Delim:
    __slots__ = ("char", "count", "can_open", "can_close", "index")

    def __init__(self, char, count, can_open, can_close):
        self.char = char
        self.count = count
        self.can_open = can_open
        self.can_close = can_close
        self.index = -1


def _scan(text, link_refs, footnotes):
    out: PyList = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]

        # Hard line break: two or more spaces + newline
        if ch == "\n":
            # Check previous for spaces
            if out and isinstance(out[-1], Text) and out[-1].content.endswith("  "):
                out[-1].content = out[-1].content.rstrip(" ")
                if not out[-1].content:
                    out.pop()
                out.append(LineBreak())
            elif i + 1 < n and text[i - 1 : i] == "\\":
                # backslash + newline = hard break
                if out and isinstance(out[-1], Text) and out[-1].content.endswith("\\"):
                    out[-1].content = out[-1].content[:-1]
                    if not out[-1].content:
                        out.pop()
                out.append(LineBreak())
            else:
                out.append(SoftBreak())
            i += 1
            continue

        if ch == "\\" and i + 1 < n:
            nxt = text[i + 1]
            if nxt in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~":
                _append_text(out, nxt)
                i += 2
                continue

        # Inline code
        if ch == "`":
            j = i
            while j < n and text[j] == "`":
                j += 1
            run = j - i
            # Find matching closing run
            k = j
            while k < n:
                if text[k] == "`":
                    kk = k
                    while kk < n and text[kk] == "`":
                        kk += 1
                    if kk - k == run:
                        content = text[j:k]
                        content = re.sub(r"[ \t\n]+", " ", content).strip(" ")
                        node = InlineCode(content=content)
                        out.append(node)
                        i = kk
                        break
                    k = kk
                else:
                    k += 1
            else:
                # No closing run — emit the backticks as text
                _append_text(out, text[i:j])
                i = j
            continue

        # Autolinks and raw HTML
        if ch == "<":
            m = _AUTOLINK_URL_RE.match(text, i)
            if m:
                out.append(Autolink(destination=m.group(1), is_email=False))
                i = m.end()
                continue
            m = _AUTOLINK_EMAIL_RE.match(text, i)
            if m:
                out.append(Autolink(destination=m.group(1), is_email=True))
                i = m.end()
                continue
            m = _RAW_HTML_RE.match(text, i)
            if m:
                out.append(RawHTML(content=m.group(0)))
                i = m.end()
                continue

        # Footnote reference ([^label])
        if ch == "[" and i + 1 < n and text[i + 1] == "^":
            m = _FOOTNOTE_REF_RE.match(text, i)
            if m:
                label = m.group(1).strip().lower()
                out.append(FootnoteRef(label=label))
                i = m.end()
                continue

        # Image ![alt](dest) or ![alt][ref]
        if ch == "!" and i + 1 < n and text[i + 1] == "[":
            node, new_i = _try_link(text, i + 1, link_refs, is_image=True)
            if node is not None:
                out.append(node)
                i = new_i
                continue

        # Link [text](dest) or [text][ref]
        if ch == "[":
            node, new_i = _try_link(text, i, link_refs, is_image=False)
            if node is not None:
                out.append(node)
                i = new_i
                continue

        # Emphasis delimiters
        if ch in ("*", "_"):
            j = i
            while j < n and text[j] == ch:
                j += 1
            count = j - i
            # Determine flanking (simplified)
            prev_char = text[i - 1] if i > 0 else "\n"
            next_char = text[j] if j < n else "\n"
            left_flank = not next_char.isspace() and (
                not _is_punct(next_char) or (prev_char.isspace() or _is_punct(prev_char))
            )
            right_flank = not prev_char.isspace() and (
                not _is_punct(prev_char) or (next_char.isspace() or _is_punct(next_char))
            )
            if ch == "_":
                can_open = left_flank and (not right_flank or _is_punct(prev_char))
                can_close = right_flank and (not left_flank or _is_punct(next_char))
            else:
                can_open = left_flank
                can_close = right_flank
            delim = _Delim(ch, count, can_open, can_close)
            delim.index = len(out)
            # Store as a marker Text node we can swap later.
            marker = _DelimMarker(delim)
            out.append(marker)
            i = j
            continue

        # Default: text
        _append_text(out, ch)
        i += 1
    return out


class _DelimMarker:
    __slots__ = ("delim",)

    def __init__(self, delim):
        self.delim = delim


def _append_text(out, s):
    if out and isinstance(out[-1], Text):
        out[-1].content += s
    else:
        out.append(Text(content=s))


def _is_punct(c):
    return bool(c) and (not c.isalnum()) and (not c.isspace())


def _try_link(text, start, link_refs, is_image):
    """Try to parse a link or image starting at ``start``.

    Returns (node, new_index) on success, (None, start) otherwise.
    """
    n = len(text)
    assert text[start] == "["
    depth = 1
    k = start + 1
    while k < n:
        c = text[k]
        if c == "\\" and k + 1 < n:
            k += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                break
        k += 1
    if k >= n:
        return None, start
    label_text = text[start + 1 : k]
    rest = k + 1
    # Inline link
    if rest < n and text[rest] == "(":
        m = re.match(r"\(\s*(<[^>]*>|\S*?)(?:\s+(\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*'|\((?:\\.|[^)])*\)))?\s*\)", text[rest:])
        if m:
            dest = m.group(1)
            if dest.startswith("<") and dest.endswith(">"):
                dest = dest[1:-1]
            title = m.group(2) or ""
            if title:
                title = title[1:-1]
            if is_image:
                node = Image(destination=dest, title=title, alt=_plain_text(label_text))
            else:
                node = Link(destination=dest, title=title)
                node.children = _parse_inline(label_text, link_refs, {})
            return node, rest + m.end()
    # Reference link: [text][label] or [text][]
    if rest < n and text[rest] == "[":
        m = re.match(r"\[([^\]]*)\]", text[rest:])
        if m:
            label = m.group(1).strip() or label_text
            key = re.sub(r"\s+", " ", label).lower()
            if key in link_refs:
                dest, title = link_refs[key]
                if is_image:
                    node = Image(destination=dest, title=title, alt=_plain_text(label_text))
                else:
                    node = Link(destination=dest, title=title)
                    node.children = _parse_inline(label_text, link_refs, {})
                return node, rest + m.end()
    # Collapsed shortcut: [text]
    key = re.sub(r"\s+", " ", label_text.strip()).lower()
    if key in link_refs:
        dest, title = link_refs[key]
        if is_image:
            node = Image(destination=dest, title=title, alt=_plain_text(label_text))
        else:
            node = Link(destination=dest, title=title)
            node.children = _parse_inline(label_text, link_refs, {})
        return node, k + 1
    return None, start


def _plain_text(s):
    return re.sub(r"\s+", " ", re.sub(r"[`*_\[\]]", "", s)).strip()


def _pair_emphasis(tokens):
    """Walk through the flat token list and replace matching delimiter
    markers with Emphasis / Strong nodes."""
    out: PyList = []
    stack: PyList[Tuple[int, _Delim]] = []  # (position in `out`, delim)

    def collapse_to(opener_delim, closer_delim, open_pos, close_pos, use):
        """Turn the span (open_pos, close_pos) exclusive into an Emphasis/Strong node."""
        inner = out[open_pos + 1 : close_pos]
        if use == 2:
            node = Strong(children=inner)
        else:
            node = Emphasis(children=inner)
        # Replace range (open_pos, close_pos] with the new node
        out[open_pos : close_pos + 1] = [node]

    for tok in tokens:
        if not isinstance(tok, _DelimMarker):
            out.append(tok)
            continue
        d = tok.delim
        out_pos = len(out)
        out.append(tok)
        if not d.can_close:
            if d.can_open:
                stack.append((out_pos, d))
            else:
                # Not an opener nor a closer — convert to literal
                out[out_pos] = Text(content=d.char * d.count)
            continue
        # Try to pair with a matching opener on the stack.
        matched = False
        for idx in range(len(stack) - 1, -1, -1):
            opos, od = stack[idx]
            if od.char != d.char:
                continue
            # Rule: if both can_open and can_close, their combined count must
            # not be a multiple of 3 (CommonMark rule 9/10, simplified).
            if (od.can_open and od.can_close) or (d.can_open and d.can_close):
                if (od.count + d.count) % 3 == 0 and not (od.count % 3 == 0 and d.count % 3 == 0):
                    continue
            # Determine how many delimiters we consume.
            use = 2 if od.count >= 2 and d.count >= 2 else 1
            # Remove everything on the stack above opener.
            stack = stack[: idx + 1]
            # Shorten counts.
            od.count -= use
            d.count -= use
            # Build the span.
            inner = out[opos + 1 : out_pos]
            if use == 2:
                node = Strong(children=inner)
            else:
                node = Emphasis(children=inner)
            # Replace the range (opos..out_pos) with: remaining opener text (if any) + node + remaining closer (if any)
            replacement = []
            if od.count > 0:
                replacement.append(Text(content=od.char * od.count))
            replacement.append(node)
            tail = []
            if d.count > 0:
                tail.append(Text(content=d.char * d.count))
            out[opos : out_pos + 1] = replacement
            # Update out_pos to new end position.
            out.extend(tail)
            # Clean up stack entry if exhausted.
            if od.count == 0:
                stack.pop()
            matched = True
            break
        if not matched:
            if d.can_open:
                stack.append((len(out) - 1, d))
            else:
                out[len(out) - 1] = Text(content=d.char * d.count)

    # Any remaining delimiter markers become literal text.
    final: PyList = []
    for item in out:
        if isinstance(item, _DelimMarker):
            if final and isinstance(final[-1], Text):
                final[-1].content += item.delim.char * item.delim.count
            else:
                final.append(Text(content=item.delim.char * item.delim.count))
        else:
            final.append(item)
    return final
