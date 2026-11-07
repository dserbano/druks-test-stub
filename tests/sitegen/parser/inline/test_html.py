"""Raw inline HTML passthrough."""
from app.sitegen.parser import render


def test_inline_open_tag():
    out = render("hello <span>world</span>")
    assert "<span>world</span>" in out


def test_inline_self_closing():
    out = render("a <br/> b")
    assert "<br/>" in out


def test_inline_comment():
    out = render("x <!-- hidden --> y")
    assert "<!-- hidden -->" in out


def test_inline_attributes():
    out = render('<a href="/x">link</a>')
    assert '<a href="/x">link</a>' in out


def test_inline_processing_instruction():
    out = render("<?php echo 1 ?>")
    assert "<?php echo 1 ?>" in out
