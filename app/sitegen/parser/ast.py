"""AST node types for the markdown parser."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List as PyList, Optional


@dataclass
class Node:
    children: PyList["Node"] = field(default_factory=list)

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


@dataclass
class Document(Node):
    link_refs: dict = field(default_factory=dict)
    footnotes: dict = field(default_factory=dict)


@dataclass
class Heading(Node):
    level: int = 1
    raw: str = ""


@dataclass
class Paragraph(Node):
    raw: str = ""


@dataclass
class BlockQuote(Node):
    pass


@dataclass
class List(Node):
    ordered: bool = False
    start: int = 1
    tight: bool = True
    bullet: str = "-"


@dataclass
class ListItem(Node):
    raw_lines: PyList[str] = field(default_factory=list)


@dataclass
class CodeBlock(Node):
    content: str = ""
    info: str = ""
    fenced: bool = False


@dataclass
class HTMLBlock(Node):
    content: str = ""


@dataclass
class ThematicBreak(Node):
    pass


@dataclass
class Table(Node):
    header: Optional["TableRow"] = None
    alignments: PyList[str] = field(default_factory=list)


@dataclass
class TableRow(Node):
    pass


@dataclass
class TableCell(Node):
    header: bool = False
    align: str = ""
    raw: str = ""


@dataclass
class FootnoteDef(Node):
    label: str = ""
    raw: str = ""


@dataclass
class LinkRefDef(Node):
    label: str = ""
    destination: str = ""
    title: str = ""


# Inline nodes

@dataclass
class Text(Node):
    content: str = ""


@dataclass
class Emphasis(Node):
    pass


@dataclass
class Strong(Node):
    pass


@dataclass
class InlineCode(Node):
    content: str = ""


@dataclass
class Link(Node):
    destination: str = ""
    title: str = ""


@dataclass
class Image(Node):
    destination: str = ""
    title: str = ""
    alt: str = ""


@dataclass
class Autolink(Node):
    destination: str = ""
    is_email: bool = False


@dataclass
class RawHTML(Node):
    content: str = ""


@dataclass
class FootnoteRef(Node):
    label: str = ""


@dataclass
class LineBreak(Node):
    pass


@dataclass
class SoftBreak(Node):
    pass
