"""Block-level markdown tokenizer.

Produces an AST (Document root) from the raw text and also collects
link reference definitions and footnote definitions encountered along
the way, returning them alongside the document.

The parser is deliberately permissive: it recognises the block
constructs named in DSE-84 (ATX+Setext headings, ordered and unordered
lists with nesting, pipe tables, fenced and indented code blocks,
block quotes, thematic breaks, footnote definitions, link reference
definitions, and HTML blocks). It is not a complete CommonMark
implementation, but it matches the shape of one closely enough to
produce reasonable HTML for ordinary documents.
"""
from __future__ import annotations

import re
from typing import Dict, List as PyList, Tuple

from .ast import (
    BlockQuote,
    CodeBlock,
    Document,
    FootnoteDef,
    Heading,
    HTMLBlock,
    LinkRefDef,
    List,
    ListItem,
    Paragraph,
    Table,
    TableCell,
    TableRow,
    ThematicBreak,
)


_ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
_SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
_HR_RE = re.compile(r"^ {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})[ \t]*$")
_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})[ \t]*([^`\r\n]*)$")
_ULIST_RE = re.compile(r"^( {0,3})([-+*])([ \t]+)(.*)$")
_OLIST_RE = re.compile(r"^( {0,3})(\d{1,9})([.)])([ \t]+)(.*)$")
_BLOCKQUOTE_RE = re.compile(r"^ {0,3}>[ ]?(.*)$")
_LINK_REF_RE = re.compile(
    r'^[ ]{0,3}\[(?P<label>(?:\\[\[\]]|[^\[\]])+)\]:\s*'
    r'(?P<dest><[^>]*>|\S+)'
    r'(?:\s+(?P<title>"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|\((?:\\.|[^)])*\)))?'
    r'\s*$'
)
_FOOTNOTE_DEF_RE = re.compile(r"^ {0,3}\[\^(?P<label>[^\]]+)\]:[ \t]*(?P<body>.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)*\s*:?-+:?\s*\|?\s*$")
_HTML_BLOCK_START_RE = re.compile(
    r"^ {0,3}<(/?)(" + "|".join([
        "address", "article", "aside", "base", "basefont", "blockquote",
        "body", "caption", "center", "col", "colgroup", "dd", "details",
        "dialog", "dir", "div", "dl", "dt", "fieldset", "figcaption",
        "figure", "footer", "form", "frame", "frameset", "h1", "h2",
        "h3", "h4", "h5", "h6", "head", "header", "hr", "html",
        "iframe", "legend", "li", "link", "main", "menu", "menuitem",
        "nav", "noframes", "ol", "optgroup", "option", "p", "param",
        "section", "source", "summary", "table", "tbody", "td",
        "tfoot", "th", "thead", "title", "tr", "track", "ul", "script",
        "style", "pre",
    ]) + r")(\s|>|/>|$)",
    re.IGNORECASE,
)


def _expand_tabs(line: str) -> str:
    out = []
    col = 0
    for ch in line:
        if ch == "\t":
            fill = 4 - (col % 4)
            out.append(" " * fill)
            col += fill
        else:
            out.append(ch)
            col += 1
    return "".join(out)


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip()).lower()


def parse_blocks(text: str) -> Tuple[Document, Dict[str, Tuple[str, str]], Dict[str, FootnoteDef]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    doc = Document()
    link_refs: Dict[str, Tuple[str, str]] = {}
    footnotes: Dict[str, FootnoteDef] = {}
    _parse(lines, 0, len(lines), doc, link_refs, footnotes, indent=0)
    return doc, link_refs, footnotes


def _parse(lines, start, end, parent, link_refs, footnotes, indent):
    i = start
    paragraph_lines: PyList[str] = []
    paragraph_start = None

    def flush_paragraph():
        nonlocal paragraph_lines, paragraph_start
        if paragraph_lines:
            # Try to extract leading link reference definitions.
            text = "\n".join(paragraph_lines)
            text = _extract_link_refs(text, link_refs)
            if text.strip():
                parent.children.append(Paragraph(raw=text))
            paragraph_lines = []
            paragraph_start = None

    while i < end:
        raw = lines[i]
        line = _strip_indent(raw, indent)
        if line is None:
            # Does not belong to this container's indent.
            flush_paragraph()
            break
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        # Thematic break (must come before list check for "---")
        if _HR_RE.match(line) and not paragraph_lines:
            parent.children.append(ThematicBreak())
            i += 1
            continue

        # ATX heading
        m = _ATX_RE.match(line)
        if m:
            flush_paragraph()
            level = len(m.group(1))
            raw_text = (m.group(2) or "").strip()
            parent.children.append(Heading(level=level, raw=raw_text))
            i += 1
            continue

        # Setext heading: previous paragraph becomes heading
        m = _SETEXT_RE.match(line)
        if m and paragraph_lines:
            level = 1 if m.group(1).startswith("=") else 2
            raw_text = "\n".join(paragraph_lines).strip()
            raw_text = _extract_link_refs(raw_text, link_refs)
            paragraph_lines = []
            if raw_text:
                parent.children.append(Heading(level=level, raw=raw_text))
            i += 1
            continue

        # Fenced code block
        m = _FENCE_RE.match(line)
        if m:
            flush_paragraph()
            fence = m.group(2)
            info = m.group(3).strip()
            i += 1
            content_lines: PyList[str] = []
            while i < end:
                cur = _strip_indent(lines[i], indent) or ""
                close = re.match(r"^ {0,3}(" + re.escape(fence[0]) + r"{" + str(len(fence)) + r",})[ \t]*$", cur)
                if close:
                    i += 1
                    break
                content_lines.append(cur)
                i += 1
            parent.children.append(
                CodeBlock(content="\n".join(content_lines) + ("\n" if content_lines else ""), info=info, fenced=True)
            )
            continue

        # Indented code block (only when not continuing a paragraph)
        if not paragraph_lines and raw.startswith(" " * (indent + 4)):
            flush_paragraph()
            code_lines: PyList[str] = []
            while i < end:
                cur = lines[i]
                if cur.startswith(" " * (indent + 4)):
                    code_lines.append(cur[indent + 4 :])
                    i += 1
                elif cur.strip() == "":
                    # Trailing blank lines are part of the block only if more code follows.
                    j = i + 1
                    while j < end and lines[j].strip() == "":
                        j += 1
                    if j < end and lines[j].startswith(" " * (indent + 4)):
                        code_lines.append("")
                        i += 1
                    else:
                        break
                else:
                    break
            parent.children.append(
                CodeBlock(content="\n".join(code_lines) + "\n", info="", fenced=False)
            )
            continue

        # Blockquote
        m = _BLOCKQUOTE_RE.match(line)
        if m:
            flush_paragraph()
            bq_lines: PyList[str] = [m.group(1)]
            i += 1
            while i < end:
                cur = _strip_indent(lines[i], indent) or ""
                mm = _BLOCKQUOTE_RE.match(cur)
                if mm:
                    bq_lines.append(mm.group(1))
                    i += 1
                elif cur.strip() == "":
                    break
                else:
                    # lazy continuation
                    bq_lines.append(cur)
                    i += 1
            bq = BlockQuote()
            parent.children.append(bq)
            _parse(bq_lines, 0, len(bq_lines), bq, link_refs, footnotes, indent=0)
            continue

        # Footnote definition
        m = _FOOTNOTE_DEF_RE.match(line)
        if m:
            flush_paragraph()
            label = m.group("label").strip()
            body_lines = [m.group("body")]
            i += 1
            # Continuation lines indented at least 4 or blank then indented.
            while i < end:
                cur = lines[i]
                if cur.strip() == "":
                    body_lines.append("")
                    i += 1
                    continue
                if cur.startswith(" " * (indent + 4)):
                    body_lines.append(cur[indent + 4 :])
                    i += 1
                else:
                    break
            # Trim trailing blanks
            while body_lines and body_lines[-1] == "":
                body_lines.pop()
            fn = FootnoteDef(label=label, raw="\n".join(body_lines))
            footnotes[_normalize_label(label)] = fn
            continue

        # Link reference definition standalone
        joined_test = line
        m = _LINK_REF_RE.match(joined_test)
        if m and not paragraph_lines:
            label = _normalize_label(m.group("label"))
            dest = m.group("dest")
            if dest.startswith("<") and dest.endswith(">"):
                dest = dest[1:-1]
            title = m.group("title") or ""
            if title:
                title = title[1:-1]
            link_refs[label] = (dest, title)
            i += 1
            continue

        # List item
        m_u = _ULIST_RE.match(line)
        m_o = _OLIST_RE.match(line)
        if m_u or m_o:
            flush_paragraph()
            ordered = bool(m_o)
            if m_o:
                indent_str = m_o.group(1)
                num = int(m_o.group(2))
                delim = m_o.group(3)
                after = m_o.group(5)
                marker = m_o.group(2) + delim
                bullet = delim
            else:
                indent_str = m_u.group(1)
                after = m_u.group(4)
                marker = m_u.group(2)
                bullet = m_u.group(2)
                num = 1
            lst = List(ordered=ordered, start=num, bullet=bullet)
            parent.children.append(lst)
            # Determine item indent: spaces to leading indent + marker width + after space
            # We treat each item as a mini-document.
            i = _consume_list_items(lines, i, end, lst, link_refs, footnotes, ordered, indent)
            continue

        # Pipe table detection: line that looks like header followed by separator
        if "|" in line and i + 1 < end:
            next_raw = lines[i + 1]
            next_stripped = _strip_indent(next_raw, indent) or ""
            if _TABLE_SEP_RE.match(next_stripped) and "|" in next_stripped:
                table = _parse_table(lines, i, end, indent)
                if table is not None:
                    flush_paragraph()
                    parent.children.append(table[0])
                    i = table[1]
                    continue

        # HTML block (type 6: known block tag)
        if _HTML_BLOCK_START_RE.match(line):
            flush_paragraph()
            html_lines = [line]
            i += 1
            while i < end:
                cur = _strip_indent(lines[i], indent)
                if cur is None or cur.strip() == "":
                    break
                html_lines.append(cur)
                i += 1
            parent.children.append(HTMLBlock(content="\n".join(html_lines) + "\n"))
            continue

        # Default: paragraph continuation
        paragraph_lines.append(line)
        i += 1

    flush_paragraph()
    return i


def _strip_indent(line: str, indent: int):
    if indent == 0:
        return line
    if len(line) >= indent and line[:indent].strip() == "":
        return line[indent:]
    if line.strip() == "":
        return ""
    return None


def _extract_link_refs(text: str, link_refs) -> str:
    """Pull leading link reference definitions out of a paragraph text."""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = _LINK_REF_RE.match(lines[i])
        if not m:
            break
        label = _normalize_label(m.group("label"))
        dest = m.group("dest")
        if dest.startswith("<") and dest.endswith(">"):
            dest = dest[1:-1]
        title = m.group("title") or ""
        if title:
            title = title[1:-1]
        if label not in link_refs:
            link_refs[label] = (dest, title)
        i += 1
    return "\n".join(lines[i:])


def _consume_list_items(lines, i, end, lst: List, link_refs, footnotes, ordered: bool, indent: int) -> int:
    prev_blank = False
    while i < end:
        raw = lines[i]
        line = _strip_indent(raw, indent)
        if line is None:
            break
        if line.strip() == "":
            prev_blank = True
            i += 1
            continue
        m_u = _ULIST_RE.match(line)
        m_o = _OLIST_RE.match(line)
        if ordered:
            m = m_o
        else:
            m = m_u
        if not m:
            break
        if ordered:
            indent_str = m.group(1)
            marker_w = len(m.group(2)) + 1  # digits + delim
            after = m.group(5)
            after_spaces = len(m.group(4))
        else:
            indent_str = m.group(1)
            marker_w = 1
            after = m.group(4)
            after_spaces = len(m.group(3))
        item_indent = len(indent_str) + marker_w + after_spaces
        if prev_blank:
            lst.tight = False
            prev_blank = False
        item = ListItem(raw_lines=[])
        lst.children.append(item)
        # First line content
        first = " " * (len(indent_str)) + after if False else after
        item_lines = [after]
        i += 1
        while i < end:
            raw2 = lines[i]
            s2 = _strip_indent(raw2, indent)
            if s2 is None:
                break
            if s2.strip() == "":
                item_lines.append("")
                i += 1
                continue
            if s2.startswith(" " * item_indent):
                item_lines.append(s2[item_indent:])
                i += 1
                continue
            # Another list marker at the same indent — belongs to the outer list.
            if _ULIST_RE.match(s2) or _OLIST_RE.match(s2):
                break
            # Lazy continuation only when the previous line was not blank.
            if item_lines and item_lines[-1].strip() != "":
                item_lines.append(s2.lstrip())
                i += 1
                continue
            break
        # Trim trailing blanks from item.
        while item_lines and item_lines[-1] == "":
            lst.tight = False
            item_lines.pop()
        _parse(item_lines, 0, len(item_lines), item, link_refs, footnotes, indent=0)
    return i


def _parse_table(lines, start, end, indent):
    header_line = _strip_indent(lines[start], indent) or ""
    sep_line = _strip_indent(lines[start + 1], indent) or ""
    header_cells = _split_table_row(header_line)
    sep_cells = _split_table_row(sep_line)
    if len(header_cells) != len(sep_cells):
        return None
    alignments = []
    for cell in sep_cells:
        s = cell.strip()
        left = s.startswith(":")
        right = s.endswith(":")
        if left and right:
            alignments.append("center")
        elif right:
            alignments.append("right")
        elif left:
            alignments.append("left")
        else:
            alignments.append("")
    table = Table(alignments=alignments)
    header = TableRow()
    for raw_cell, align in zip(header_cells, alignments):
        header.children.append(TableCell(header=True, align=align, raw=raw_cell.strip()))
    table.header = header
    i = start + 2
    while i < end:
        line = _strip_indent(lines[i], indent)
        if line is None or line.strip() == "":
            break
        if "|" not in line:
            break
        cells = _split_table_row(line)
        row = TableRow()
        for idx, raw_cell in enumerate(cells):
            align = alignments[idx] if idx < len(alignments) else ""
            row.children.append(TableCell(align=align, raw=raw_cell.strip()))
        table.children.append(row)
        i += 1
    return table, i


def _split_table_row(line: str):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells = []
    buf = []
    k = 0
    while k < len(line):
        ch = line[k]
        if ch == "\\" and k + 1 < len(line) and line[k + 1] == "|":
            buf.append("|")
            k += 2
            continue
        if ch == "|":
            cells.append("".join(buf))
            buf = []
            k += 1
            continue
        buf.append(ch)
        k += 1
    cells.append("".join(buf))
    return cells
