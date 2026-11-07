"""From-scratch markdown parser targeting CommonMark 0.30.

Entry points:
    parse(text)        -> AST (Document node)
    render(text)       -> HTML string
    render_ast(ast)    -> HTML string
"""
from .ast import (
    Node,
    Document,
    Heading,
    Paragraph,
    BlockQuote,
    List,
    ListItem,
    CodeBlock,
    HTMLBlock,
    ThematicBreak,
    Table,
    TableRow,
    TableCell,
    FootnoteDef,
    LinkRefDef,
    Text,
    Emphasis,
    Strong,
    InlineCode,
    Link,
    Image,
    Autolink,
    RawHTML,
    FootnoteRef,
    LineBreak,
    SoftBreak,
)
from .blocks import parse_blocks
from .inlines import parse_inlines
from .renderer import HTMLRenderer


def parse(text: str) -> Document:
    """Parse markdown text into an AST Document."""
    doc, link_refs, footnotes = parse_blocks(text)
    parse_inlines(doc, link_refs, footnotes)
    doc.link_refs = link_refs
    doc.footnotes = footnotes
    return doc


def render_ast(doc: Document) -> str:
    """Render an AST to HTML."""
    return HTMLRenderer().render(doc)


def render(text: str) -> str:
    """Parse and render markdown text to HTML."""
    return render_ast(parse(text))


__all__ = [
    "parse",
    "render",
    "render_ast",
    "HTMLRenderer",
    "Node",
    "Document",
    "Heading",
    "Paragraph",
    "BlockQuote",
    "List",
    "ListItem",
    "CodeBlock",
    "HTMLBlock",
    "ThematicBreak",
    "Table",
    "TableRow",
    "TableCell",
    "FootnoteDef",
    "LinkRefDef",
    "Text",
    "Emphasis",
    "Strong",
    "InlineCode",
    "Link",
    "Image",
    "Autolink",
    "RawHTML",
    "FootnoteRef",
    "LineBreak",
    "SoftBreak",
]
