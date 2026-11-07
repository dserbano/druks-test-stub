"""Strong inline parsing (``**text**`` / ``__text__``)."""
import pytest
from app.sitegen.parser import render


@pytest.mark.parametrize("md,expected", [
    ("**bold**", "<p><strong>bold</strong></p>\n"),
    ("__bold__", "<p><strong>bold</strong></p>\n"),
    ("a **bold** b", "<p>a <strong>bold</strong> b</p>\n"),
    ("**a** and **b**", "<p><strong>a</strong> and <strong>b</strong></p>\n"),
])
def test_strong_basic(md, expected):
    assert render(md) == expected


def test_strong_contains_emphasis():
    out = render("**outer *inner* outer**")
    assert "<strong>" in out
    assert "<em>inner</em>" in out


def test_unmatched_double_asterisk():
    out = render("**unmatched")
    assert "<strong>" not in out
