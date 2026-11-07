"""HTML renderer for the parser AST."""
from __future__ import annotations

from html import escape as _html_escape
from urllib.parse import quote as _url_quote

from .ast import (
    Autolink,
    BlockQuote,
    CodeBlock,
    Document,
    Emphasis,
    FootnoteDef,
    FootnoteRef,
    Heading,
    HTMLBlock,
    Image,
    InlineCode,
    LineBreak,
    Link,
    LinkRefDef,
    List,
    ListItem,
    Node,
    Paragraph,
    RawHTML,
    SoftBreak,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    ThematicBreak,
)


def _esc(s: str) -> str:
    return _html_escape(s, quote=False).replace('"', "&quot;")


def _esc_attr(s: str) -> str:
    return _html_escape(s, quote=True)


def _escape_url(url: str) -> str:
    safe = ";/?:@&=+$,-_.!~*'()#%"
    return _url_quote(url, safe=safe)


class HTMLRenderer:
    def __init__(self):
        self.footnote_refs = []  # list of label references in order of first use
        self.footnote_defs = {}

    def render(self, doc: Document) -> str:
        self.footnote_defs = getattr(doc, "footnotes", {}) or {}
        self.footnote_refs = []
        parts = [self._render_node(c) for c in doc.children]
        body = "".join(parts)
        # Append footnotes section if any references appeared
        if self.footnote_refs:
            body += self._render_footnotes_section()
        return body

    # Dispatch -----------------------------------------------------------
    def _render_node(self, node: Node) -> str:
        meth = getattr(self, f"_render_{type(node).__name__}", None)
        if meth is None:
            return self._render_children(node)
        return meth(node)

    def _render_children(self, node: Node) -> str:
        return "".join(self._render_node(c) for c in node.children)

    # Block renderers ----------------------------------------------------
    def _render_Paragraph(self, node: Paragraph) -> str:
        return f"<p>{self._render_children(node)}</p>\n"

    def _render_Heading(self, node: Heading) -> str:
        return f"<h{node.level}>{self._render_children(node)}</h{node.level}>\n"

    def _render_BlockQuote(self, node: BlockQuote) -> str:
        return f"<blockquote>\n{self._render_children(node)}</blockquote>\n"

    def _render_ThematicBreak(self, node: ThematicBreak) -> str:
        return "<hr />\n"

    def _render_CodeBlock(self, node: CodeBlock) -> str:
        if node.info:
            lang = node.info.split()[0]
            cls = f' class="language-{_esc_attr(lang)}"'
        else:
            cls = ""
        return f"<pre><code{cls}>{_esc(node.content)}</code></pre>\n"

    def _render_HTMLBlock(self, node: HTMLBlock) -> str:
        return node.content if node.content.endswith("\n") else node.content + "\n"

    def _render_List(self, node: List) -> str:
        tag = "ol" if node.ordered else "ul"
        attrs = ""
        if node.ordered and node.start != 1:
            attrs = f' start="{node.start}"'
        items = "".join(self._render_node(c) for c in node.children)
        return f"<{tag}{attrs}>\n{items}</{tag}>\n"

    def _render_ListItem(self, node: ListItem) -> str:
        # Tight items: inline their single paragraph child.
        inner = []
        for c in node.children:
            if isinstance(c, Paragraph) and len(node.children) == 1:
                inner.append(self._render_children(c))
            else:
                inner.append(self._render_node(c))
        joined = "".join(inner)
        if "\n" in joined.rstrip("\n"):
            return f"<li>\n{joined}</li>\n"
        return f"<li>{joined.rstrip()}</li>\n"

    def _render_Table(self, node: Table) -> str:
        parts = ["<table>\n"]
        if node.header is not None:
            parts.append("<thead>\n<tr>\n")
            for cell in node.header.children:
                parts.append(self._render_cell(cell))
            parts.append("</tr>\n</thead>\n")
        if node.children:
            parts.append("<tbody>\n")
            for row in node.children:
                parts.append("<tr>\n")
                for cell in row.children:
                    parts.append(self._render_cell(cell))
                parts.append("</tr>\n")
            parts.append("</tbody>\n")
        parts.append("</table>\n")
        return "".join(parts)

    def _render_cell(self, cell: TableCell) -> str:
        tag = "th" if cell.header else "td"
        align = f' style="text-align:{cell.align}"' if cell.align else ""
        inner = self._render_children(cell) if cell.children else _esc(cell.raw)
        return f"<{tag}{align}>{inner}</{tag}>\n"

    def _render_LinkRefDef(self, node: LinkRefDef) -> str:
        return ""

    def _render_FootnoteDef(self, node: FootnoteDef) -> str:
        return ""

    # Inline renderers ---------------------------------------------------
    def _render_Text(self, node: Text) -> str:
        return _esc(node.content)

    def _render_Emphasis(self, node: Emphasis) -> str:
        return f"<em>{self._render_children(node)}</em>"

    def _render_Strong(self, node: Strong) -> str:
        return f"<strong>{self._render_children(node)}</strong>"

    def _render_InlineCode(self, node: InlineCode) -> str:
        return f"<code>{_esc(node.content)}</code>"

    def _render_Link(self, node: Link) -> str:
        dest = _escape_url(node.destination)
        title_attr = f' title="{_esc_attr(node.title)}"' if node.title else ""
        return f'<a href="{dest}"{title_attr}>{self._render_children(node)}</a>'

    def _render_Image(self, node: Image) -> str:
        dest = _escape_url(node.destination)
        alt = _esc_attr(node.alt)
        title_attr = f' title="{_esc_attr(node.title)}"' if node.title else ""
        return f'<img src="{dest}" alt="{alt}"{title_attr} />'

    def _render_Autolink(self, node: Autolink) -> str:
        if node.is_email:
            return f'<a href="mailto:{_esc_attr(node.destination)}">{_esc(node.destination)}</a>'
        dest = _escape_url(node.destination)
        return f'<a href="{dest}">{_esc(node.destination)}</a>'

    def _render_RawHTML(self, node: RawHTML) -> str:
        return node.content

    def _render_LineBreak(self, node: LineBreak) -> str:
        return "<br />\n"

    def _render_SoftBreak(self, node: SoftBreak) -> str:
        return "\n"

    def _render_FootnoteRef(self, node: FootnoteRef) -> str:
        label = node.label
        if label not in self.footnote_refs:
            self.footnote_refs.append(label)
        n = self.footnote_refs.index(label) + 1
        return (
            f'<sup class="footnote-ref">'
            f'<a href="#fn-{_esc_attr(label)}" id="fnref-{_esc_attr(label)}">{n}</a>'
            f'</sup>'
        )

    def _render_footnotes_section(self) -> str:
        parts = ['<section class="footnotes">\n<ol>\n']
        for label in self.footnote_refs:
            fn = self.footnote_defs.get(label)
            if fn is None:
                continue
            # Re-render the footnote body as paragraphs
            from .blocks import parse_blocks
            from .inlines import parse_inlines
            doc, refs, fns = parse_blocks(fn.raw)
            parse_inlines(doc, refs, fns)
            inner = "".join(self._render_node(c) for c in doc.children)
            parts.append(f'<li id="fn-{_esc_attr(label)}">\n{inner}</li>\n')
        parts.append("</ol>\n</section>\n")
        return "".join(parts)
