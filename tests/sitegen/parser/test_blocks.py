"""Block-level parser coverage tests.

One test per named block construct in DSE-84: ATX+Setext headings,
ordered and nested lists, pipe tables, fenced and indented code blocks,
block quotes, thematic breaks, footnote definitions, link reference
definitions, and raw HTML blocks.
"""
from __future__ import annotations

import pytest

from app.sitegen.parser import render, parse
from app.sitegen.parser.ast import (
    BlockQuote,
    CodeBlock,
    Heading,
    HTMLBlock,
    List,
    Paragraph,
    Table,
    ThematicBreak,
)


# --- ATX headings ---------------------------------------------------------

@pytest.mark.parametrize("hashes,level", [("#", 1), ("##", 2), ("###", 3), ("####", 4), ("#####", 5), ("######", 6)])
def test_atx_heading_levels(hashes, level):
    md = f"{hashes} Title\n"
    out = render(md)
    assert f"<h{level}>" in out and f"</h{level}>" in out


def test_atx_heading_text():
    out = render("# Hello world\n")
    assert out.strip() == "<h1>Hello world</h1>"


def test_atx_heading_with_trailing_hashes():
    out = render("## Hello ##\n")
    assert "<h2>Hello</h2>" in out


def test_atx_heading_in_ast():
    doc = parse("# Hi\n")
    assert isinstance(doc.children[0], Heading)
    assert doc.children[0].level == 1


# --- Setext headings ------------------------------------------------------

def test_setext_h1():
    out = render("Title\n=====\n")
    assert "<h1>Title</h1>" in out


def test_setext_h2():
    out = render("Title\n-----\n")
    assert "<h2>Title</h2>" in out


def test_setext_heading_in_ast():
    doc = parse("Title\n=====\n")
    assert isinstance(doc.children[0], Heading)
    assert doc.children[0].level == 1


# --- Lists ----------------------------------------------------------------

def test_unordered_list_dash():
    out = render("- a\n- b\n- c\n")
    assert "<ul>" in out and out.count("<li>") == 3


def test_unordered_list_asterisk():
    out = render("* a\n* b\n")
    assert "<ul>" in out and out.count("<li>") == 2


def test_unordered_list_plus():
    out = render("+ a\n+ b\n")
    assert "<ul>" in out


def test_ordered_list():
    out = render("1. a\n2. b\n3. c\n")
    assert "<ol>" in out and out.count("<li>") == 3


def test_ordered_list_start():
    out = render("5. a\n6. b\n")
    assert '<ol start="5">' in out


def test_nested_unordered_list():
    out = render("- a\n  - a1\n  - a2\n- b\n")
    assert out.count("<ul>") == 2


def test_list_in_ast():
    doc = parse("- a\n- b\n")
    assert isinstance(doc.children[0], List)
    assert len(doc.children[0].children) == 2


# --- Tables ---------------------------------------------------------------

def test_pipe_table_basic():
    md = "| a | b |\n| - | - |\n| 1 | 2 |\n"
    out = render(md)
    assert "<table>" in out
    assert "<th>a</th>" in out
    assert "<td>1</td>" in out


def test_pipe_table_alignment_left():
    md = "| a |\n| :- |\n| 1 |\n"
    out = render(md)
    assert 'style="text-align:left"' in out


def test_pipe_table_alignment_right():
    md = "| a |\n| -: |\n| 1 |\n"
    out = render(md)
    assert 'style="text-align:right"' in out


def test_pipe_table_alignment_center():
    md = "| a |\n| :-: |\n| 1 |\n"
    out = render(md)
    assert 'style="text-align:center"' in out


def test_table_ast_node():
    doc = parse("| a | b |\n| - | - |\n| 1 | 2 |\n")
    assert isinstance(doc.children[0], Table)


def test_table_rows_count():
    md = "| a | b |\n| - | - |\n| 1 | 2 |\n| 3 | 4 |\n"
    out = render(md)
    assert out.count("<tr>") == 3  # header + 2 body rows


# --- Fenced code blocks ---------------------------------------------------

def test_fenced_code_backticks():
    out = render("```\nhello\n```\n")
    assert "<pre><code>hello\n</code></pre>" in out


def test_fenced_code_tildes():
    out = render("~~~\nhello\n~~~\n")
    assert "<pre><code>hello\n</code></pre>" in out


def test_fenced_code_language_class():
    out = render("```python\nprint(1)\n```\n")
    assert 'class="language-python"' in out


def test_fenced_code_longer_fence():
    out = render("````\n```\ninside\n```\n````\n")
    assert "inside" in out


def test_fenced_code_in_ast():
    doc = parse("```\nhi\n```\n")
    assert isinstance(doc.children[0], CodeBlock)
    assert doc.children[0].fenced is True


# --- Indented code blocks -------------------------------------------------

def test_indented_code_block():
    out = render("    hello\n    world\n")
    assert "<pre><code>hello\nworld\n</code></pre>" in out


def test_indented_code_block_ast():
    doc = parse("    hello\n")
    assert isinstance(doc.children[0], CodeBlock)
    assert doc.children[0].fenced is False


# --- Blockquotes ----------------------------------------------------------

def test_blockquote_single():
    out = render("> hi\n")
    assert "<blockquote>" in out and "<p>hi</p>" in out


def test_blockquote_multi_paragraph():
    out = render("> a\n>\n> b\n")
    assert out.count("<p>") == 2


def test_blockquote_in_ast():
    doc = parse("> hi\n")
    assert isinstance(doc.children[0], BlockQuote)


def test_nested_blockquote():
    out = render("> > inner\n")
    assert out.count("<blockquote>") == 2


# --- Thematic breaks ------------------------------------------------------

@pytest.mark.parametrize("src", ["---\n", "***\n", "___\n", "- - -\n", "* * *\n"])
def test_thematic_break(src):
    assert "<hr />" in render(src)


def test_hr_in_ast():
    doc = parse("---\n")
    assert isinstance(doc.children[0], ThematicBreak)


# --- Footnote definitions -------------------------------------------------

def test_footnote_definition_collected():
    doc = parse("[^1]: a footnote\n")
    assert "1" in doc.footnotes


def test_footnote_reference_renders():
    out = render("See[^1]\n\n[^1]: here\n")
    assert 'id="fnref-1"' in out
    assert 'id="fn-1"' in out


# --- Link reference definitions -------------------------------------------

def test_link_reference_definition_collected():
    doc = parse("[foo]: http://x.com \"title\"\n")
    assert "foo" in doc.link_refs
    assert doc.link_refs["foo"] == ("http://x.com", "title")


def test_link_via_reference_definition():
    out = render("[foo]\n\n[foo]: http://x.com\n")
    assert '<a href="http://x.com">foo</a>' in out


# --- Raw HTML blocks ------------------------------------------------------

def test_html_block_is_passed_through():
    out = render("<div>hello</div>\n")
    assert "<div>hello</div>" in out


def test_html_block_ast_node():
    doc = parse("<div>hi</div>\n")
    assert isinstance(doc.children[0], HTMLBlock)


# --- Paragraph default ----------------------------------------------------

def test_paragraph_default():
    out = render("hello world\n")
    assert "<p>hello world</p>" in out


def test_paragraph_ast_node():
    doc = parse("hello\n")
    assert isinstance(doc.children[0], Paragraph)


def test_paragraph_joins_adjacent_lines():
    out = render("a\nb\nc\n")
    assert out.count("<p>") == 1


def test_blank_line_separates_paragraphs():
    out = render("a\n\nb\n")
    assert out.count("<p>") == 2


# --- Multiple blocks together --------------------------------------------

def test_mixed_blocks():
    md = "# A\n\n- l1\n- l2\n\n```\ncode\n```\n\n> q\n\n---\n"
    out = render(md)
    assert "<h1>A</h1>" in out
    assert "<ul>" in out
    assert "<pre><code>" in out
    assert "<blockquote>" in out
    assert "<hr />" in out


def test_parser_has_no_external_markdown_dep():
    """ac-parser-blocks forbids importing a third-party markdown library."""
    import inspect
    import app.sitegen.parser as parser_mod
    src = inspect.getsource(parser_mod)
    for forbidden in ("import markdown", "import mistune", "import markdown_it", "import commonmark"):
        assert forbidden not in src
