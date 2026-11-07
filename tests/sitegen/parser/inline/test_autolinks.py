"""Autolinks (``<http://x.com>``, ``<me@x.com>``)."""
from app.sitegen.parser import render


def test_autolink_http():
    out = render("<http://x.com>")
    assert '<a href="http://x.com">http://x.com</a>' in out


def test_autolink_https():
    out = render("<https://x.com>")
    assert '<a href="https://x.com">https://x.com</a>' in out


def test_autolink_email():
    out = render("<me@x.com>")
    assert '<a href="mailto:me@x.com">me@x.com</a>' in out


def test_autolink_other_scheme():
    out = render("<ftp://x.com/a>")
    assert '<a href="ftp://x.com/a">ftp://x.com/a</a>' in out


def test_non_autolink_text():
    out = render("http://x.com")
    assert "<a " not in out
