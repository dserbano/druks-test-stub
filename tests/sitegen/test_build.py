"""End-to-end build pipeline tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.sitegen.build import build, _url_for


@pytest.fixture
def site_tree(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    content.mkdir()
    (content / "index.md").write_text(
        '+++\ntitle = "Home"\ntags = ["intro"]\n+++\n'
        "# Home\n\nHello *world*.\n",
        encoding="utf-8",
    )
    (content / "post.md").write_text(
        '+++\ntitle = "Post"\ntags = ["intro", "demo"]\n+++\n'
        "## Post\n\nText.\n",
        encoding="utf-8",
    )
    (tmp_path / "site.toml").write_text(
        '[site]\ntitle = "T"\nbase_url = "https://ex.com"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_build_renders_all_pages(site_tree, tmp_path):
    out = tmp_path / "public"
    result = build(site_tree, out)
    assert len(result.rendered) == 2


def test_build_emits_html_files(site_tree, tmp_path):
    out = tmp_path / "public"
    build(site_tree, out)
    assert (out / "index.html").exists()
    assert (out / "post" / "index.html").exists()


def test_build_emits_rss(site_tree, tmp_path):
    out = tmp_path / "public"
    build(site_tree, out)
    assert (out / "rss.xml").exists()


def test_build_emits_sitemap(site_tree, tmp_path):
    out = tmp_path / "public"
    build(site_tree, out)
    assert (out / "sitemap.xml").exists()


def test_build_emits_tag_pages(site_tree, tmp_path):
    out = tmp_path / "public"
    build(site_tree, out)
    assert (out / "tags" / "intro" / "index.html").exists()
    assert (out / "tags" / "demo" / "index.html").exists()


def test_build_output_has_rendered_content(site_tree, tmp_path):
    out = tmp_path / "public"
    build(site_tree, out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "<em>world</em>" in html


def test_build_without_config_falls_back_to_defaults(tmp_path):
    (tmp_path / "x.md").write_text("# hi\n", encoding="utf-8")
    out = tmp_path / "public"
    result = build(tmp_path, out)
    assert len(result.rendered) == 1


@pytest.mark.parametrize("rel,url", [
    ("index.md", "/"),
    ("post.md", "/post/"),
    ("sub/index.md", "/sub/"),
    ("sub/page.md", "/sub/page/"),
])
def test_url_for(rel, url):
    assert _url_for(rel) == url


def test_cli_module_importable():
    import app.sitegen.cli as cli
    assert cli.main is not None


def test_cli_build_parser_accepts_command():
    from app.sitegen.cli import build_parser
    p = build_parser()
    ns = p.parse_args(["build", "src", "out"])
    assert ns.command == "build"


def test_cli_serve_parser_accepts_command():
    from app.sitegen.cli import build_parser
    p = build_parser()
    ns = p.parse_args(["serve", "src", "out"])
    assert ns.command == "serve"
