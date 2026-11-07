"""RSS and sitemap emission tests."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.sitegen.build import build
from app.sitegen.config import SiteConfig
from app.sitegen.feeds import render_rss, render_sitemap


@dataclass
class FakePage:
    title: str = "p"
    url: str = "/p/"
    date: datetime = field(default_factory=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    summary: str = "a summary"


def test_rss_is_well_formed_xml():
    site = SiteConfig(title="t", base_url="https://x.com", description="d")
    xml = render_rss(site, [FakePage(title="A", url="/a/"), FakePage(title="B", url="/b/")])
    root = ET.fromstring(xml)
    assert root.tag == "rss"
    assert root.attrib["version"] == "2.0"


def test_rss_has_channel():
    site = SiteConfig(title="t", base_url="https://x.com")
    xml = render_rss(site, [FakePage()])
    root = ET.fromstring(xml)
    assert root.find("channel") is not None


def test_rss_has_item_per_page():
    site = SiteConfig(base_url="https://x.com")
    pages = [FakePage(title="A", url="/a/"), FakePage(title="B", url="/b/")]
    xml = render_rss(site, pages)
    root = ET.fromstring(xml)
    items = root.find("channel").findall("item")
    assert len(items) == 2


def test_rss_item_has_required_subelements():
    site = SiteConfig(base_url="https://x.com")
    xml = render_rss(site, [FakePage(title="A", url="/a/")])
    root = ET.fromstring(xml)
    item = root.find("channel").find("item")
    assert item.find("title").text == "A"
    assert item.find("link").text == "https://x.com/a/"
    assert item.find("guid").text == "https://x.com/a/"


def test_rss_handles_special_characters_in_title():
    site = SiteConfig(base_url="https://x.com")
    xml = render_rss(site, [FakePage(title="Lust & Found <v>")])
    root = ET.fromstring(xml)
    assert root.find("channel").find("item").find("title").text == "Lust & Found <v>"


def test_sitemap_is_well_formed_xml():
    site = SiteConfig(base_url="https://x.com")
    xml = render_sitemap(site, [FakePage(url="/a/"), FakePage(url="/b/")])
    root = ET.fromstring(xml)
    assert root.tag.endswith("urlset")


def test_sitemap_has_url_per_page():
    site = SiteConfig(base_url="https://x.com")
    xml = render_sitemap(site, [FakePage(url="/a/"), FakePage(url="/b/"), FakePage(url="/c/")])
    root = ET.fromstring(xml)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = root.findall("s:url", ns)
    assert len(urls) == 3


def test_sitemap_url_loc_absolute():
    site = SiteConfig(base_url="https://x.com")
    xml = render_sitemap(site, [FakePage(url="/a/")])
    root = ET.fromstring(xml)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    loc = root.find("s:url", ns).find("s:loc", ns).text
    assert loc == "https://x.com/a/"


def test_rss_and_sitemap_written_in_build(tmp_path: Path):
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "a.md").write_text("+++\ntitle = \"A\"\n+++\n# A\n", encoding="utf-8")
    (tmp_path / "site.toml").write_text('[site]\ntitle = "t"\nbase_url = "https://x.com"\n', encoding="utf-8")
    out = tmp_path / "public"
    build(tmp_path, out)
    rss = ET.fromstring((out / "rss.xml").read_text(encoding="utf-8"))
    assert rss.tag == "rss"
    sitemap = ET.fromstring((out / "sitemap.xml").read_text(encoding="utf-8"))
    assert sitemap.tag.endswith("urlset")


def test_rss_empty_feed_is_valid():
    site = SiteConfig()
    xml = render_rss(site, [])
    root = ET.fromstring(xml)
    assert root.find("channel") is not None


def test_sitemap_empty_feed_is_valid():
    site = SiteConfig()
    xml = render_sitemap(site, [])
    root = ET.fromstring(xml)
    assert root.tag.endswith("urlset")
