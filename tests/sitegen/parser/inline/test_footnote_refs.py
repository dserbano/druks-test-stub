"""Footnote reference inline parsing."""
from app.sitegen.parser import render


def test_footnote_reference_single():
    out = render("foo[^1]\n\n[^1]: note\n")
    assert 'href="#fn-1"' in out
    assert 'id="fnref-1"' in out


def test_footnote_reference_renders_sup():
    out = render("foo[^1]\n\n[^1]: note\n")
    assert "<sup" in out


def test_footnote_section_appended():
    out = render("foo[^a]\n\n[^a]: note body\n")
    assert '<section class="footnotes">' in out
    assert "note body" in out


def test_footnote_labels_are_normalized():
    out = render("hi[^A]\n\n[^a]: body\n")
    assert '<section class="footnotes">' in out


def test_footnote_reference_without_definition_is_rendered():
    out = render("hi[^missing]\n")
    # We still render the sup but no section is emitted.
    assert "<sup" in out
