"""RSS 2.0 and sitemap.xml emission."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape as _escape
from typing import Iterable


def _url(base: str, path: str) -> str:
    if not base:
        return path
    return base.rstrip("/") + "/" + path.lstrip("/")


def _rfc822(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def _iso8601(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


def render_rss(site, pages: Iterable, now=None) -> str:
    now = now or datetime.now(timezone.utc)
    items = []
    for page in pages:
        items.append(
            "<item>\n"
            f"<title>{_escape(page.title)}</title>\n"
            f"<link>{_escape(_url(site.base_url, page.url))}</link>\n"
            f"<guid>{_escape(_url(site.base_url, page.url))}</guid>\n"
            f"<pubDate>{_rfc822(getattr(page, 'date', now) or now)}</pubDate>\n"
            f"<description>{_escape((page.summary or page.title or '').strip())}</description>\n"
            "</item>"
        )
    body = "\n".join(items)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0">\n'
        '<channel>\n'
        f'<title>{_escape(site.title)}</title>\n'
        f'<link>{_escape(site.base_url)}</link>\n'
        f'<description>{_escape(site.description)}</description>\n'
        f'<lastBuildDate>{_rfc822(now)}</lastBuildDate>\n'
        f'{body}\n'
        '</channel>\n'
        '</rss>\n'
    )


def render_sitemap(site, pages: Iterable, now=None) -> str:
    now = now or datetime.now(timezone.utc)
    urls = []
    for page in pages:
        urls.append(
            "<url>\n"
            f"<loc>{_escape(_url(site.base_url, page.url))}</loc>\n"
            f"<lastmod>{_iso8601(getattr(page, 'date', now) or now)}</lastmod>\n"
            "</url>"
        )
    body = "\n".join(urls)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'{body}\n'
        '</urlset>\n'
    )
