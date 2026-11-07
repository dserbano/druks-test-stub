"""Inline and reference links."""
import pytest
from app.sitegen.parser import render, parse


def test_inline_link_basic():
    assert '<a href="http://x.com">link</a>' in render("[link](http://x.com)")


def test_inline_link_with_title():
    out = render('[link](http://x.com "t")')
    assert 'href="http://x.com"' in out
    assert 'title="t"' in out


def test_reference_link_full():
    md = "[foo][bar]\n\n[bar]: http://x.com\n"
    out = render(md)
    assert '<a href="http://x.com">foo</a>' in out


def test_reference_link_collapsed():
    md = "[bar][]\n\n[bar]: http://x.com\n"
    out = render(md)
    assert '<a href="http://x.com">bar</a>' in out


def test_reference_link_shortcut():
    md = "[bar]\n\n[bar]: http://x.com\n"
    out = render(md)
    assert '<a href="http://x.com">bar</a>' in out


def test_reference_link_definition_persists_on_doc():
    doc = parse("[foo]: http://x.com\n")
    assert doc.link_refs["foo"][0] == "http://x.com"


def test_link_with_relative_dest():
    out = render("[rel](/foo)")
    assert '<a href="/foo">rel</a>' in out


def test_link_in_paragraph_text():
    out = render("See [docs](docs.md) please.\n")
    assert '<a href="docs.md">docs</a>' in out
