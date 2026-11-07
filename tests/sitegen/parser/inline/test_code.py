"""Inline code (``` `text` ```)."""
import pytest
from app.sitegen.parser import render


@pytest.mark.parametrize("md,expected", [
    ("`code`", "<p><code>code</code></p>\n"),
    ("a `code` b", "<p>a <code>code</code> b</p>\n"),
    ("`a b c`", "<p><code>a b c</code></p>\n"),
])
def test_inline_code_basic(md, expected):
    assert render(md) == expected


def test_inline_code_with_backticks_inside():
    out = render("`` a ` b ``")
    assert "<code>a ` b</code>" in out


def test_inline_code_html_escapes_content():
    out = render("`<div>`")
    assert "<code>&lt;div&gt;</code>" in out


def test_inline_code_unmatched():
    out = render("`unmatched")
    assert "<code>" not in out
