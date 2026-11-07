"""Emphasis inline parsing (``*text*`` / ``_text_``)."""
import pytest
from app.sitegen.parser import render


@pytest.mark.parametrize("md,expected", [
    ("*em*", "<p><em>em</em></p>\n"),
    ("_em_", "<p><em>em</em></p>\n"),
    ("a *em* b", "<p>a <em>em</em> b</p>\n"),
    ("*a* and *b*", "<p><em>a</em> and <em>b</em></p>\n"),
    ("*a b c*", "<p><em>a b c</em></p>\n"),
])
def test_emphasis_basic(md, expected):
    assert render(md) == expected


def test_emphasis_and_strong_combined_tokens():
    out = render("***both***")
    assert "<strong>" in out
    assert "both" in out


def test_emphasis_underscore_within_word_does_not_fire():
    out = render("a_b_c")
    assert "<em>" not in out


def test_emphasis_requires_matching_delimiter():
    out = render("*unmatched")
    assert "<em>" not in out


def test_emphasis_in_heading():
    out = render("# *em* in heading\n")
    assert "<em>em</em>" in out
