"""Sitemap-crawl fetcher: discover event page URLs via XML sitemap, then fetch
each static detail page and return cleaned text for LLM extraction.

Used for sites like jena-veranstaltungen.de (TYPO3 + ndsdestinationdataevent)
where the listing page is JS-rendered but individual event pages are static HTML.

Flow:
  1. Fetch the sitemap index to find the event-specific sub-sitemap.
  2. Parse the sub-sitemap to get all event page URLs + lastmod dates.
  3. Fetch each event detail page, clean to text, and return as structured items.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from ..config import Source
from .base import FetchResult
from .http import _get, clean_html

log = logging.getLogger(__name__)

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _find_event_sitemap(index_xml: str, filter_fragment: str) -> str | None:
    """Return the URL of the sub-sitemap whose loc contains filter_fragment."""
    root = ET.fromstring(index_xml)
    for sitemap in root.findall("sm:sitemap", _NS):
        loc = sitemap.findtext("sm:loc", namespaces=_NS) or ""
        if filter_fragment in loc:
            return loc
    return None


def _parse_event_urls(sitemap_xml: str) -> list[dict]:
    """Return [{url, lastmod}] from an event sub-sitemap."""
    root = ET.fromstring(sitemap_xml)
    entries = []
    for url_el in root.findall("sm:url", _NS):
        loc = url_el.findtext("sm:loc", namespaces=_NS)
        lastmod = url_el.findtext("sm:lastmod", namespaces=_NS)
        if loc:
            entries.append({"url": loc, "lastmod": lastmod or ""})
    return entries


def fetch_sitemap(source: Source, max_pages: int = 200) -> FetchResult:
    """Discover event page URLs via the sitemap. Content is NOT fetched here — the
    pipeline fetches each page with fetch_page() so extract+store can run per URL
    and progress survives a restart mid-crawl."""
    index_xml = _get(source.fetch.sitemap_url)
    event_sitemap_url = _find_event_sitemap(index_xml, source.fetch.sitemap_filter)
    if not event_sitemap_url:
        raise RuntimeError(
            f"No sub-sitemap matching '{source.fetch.sitemap_filter}' found in "
            f"{source.fetch.sitemap_url}"
        )

    event_sitemap_xml = _get(event_sitemap_url)
    entries = _parse_event_urls(event_sitemap_xml)[:max_pages]
    log.info("sitemap: %d event URLs discovered", len(entries))

    return FetchResult(
        source_id=source.id,
        url=source.fetch.sitemap_url,
        content="",
        kind="pages",
        structured=entries,  # [{url, lastmod}] — no content yet
    )


def fetch_page(url: str, content_selector: str | None = None) -> str:
    """Fetch and clean one event detail page."""
    return clean_html(_get(url), content_selector)
