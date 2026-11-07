"""Inline and reference images."""
from app.sitegen.parser import render


def test_image_inline():
    out = render("![alt](img.png)")
    assert '<img src="img.png" alt="alt" />' in out


def test_image_with_title():
    out = render('![alt](img.png "t")')
    assert 'src="img.png"' in out
    assert 'alt="alt"' in out
    assert 'title="t"' in out


def test_image_reference():
    md = "![foo][bar]\n\n[bar]: img.png\n"
    out = render(md)
    assert '<img src="img.png" alt="foo" />' in out


def test_image_in_paragraph():
    out = render("See ![logo](l.png) above.\n")
    assert '<img src="l.png" alt="logo" />' in out


def test_image_alt_is_text_only():
    out = render("![*emphatic* alt](x.png)")
    assert '<img src="x.png"' in out
