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
from time import sleep

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import Source
from .base import USER_AGENT, FetchResult
from .http import clean_html

log = logging.getLogger(__name__)

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def _get(url: str) -> str:
    resp = httpx.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True
    )
    resp.raise_for_status()
    return resp.text


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
    """Fetch all event pages discovered via the sitemap and return as structured list."""
    # Step 1: get sitemap index
    index_xml = _get(source.fetch.sitemap_url)
    event_sitemap_url = _find_event_sitemap(index_xml, source.fetch.sitemap_filter)
    if not event_sitemap_url:
        raise RuntimeError(
            f"No sub-sitemap matching '{source.fetch.sitemap_filter}' found in "
            f"{source.fetch.sitemap_url}"
        )

    # Step 2: get event URL list
    event_sitemap_xml = _get(event_sitemap_url)
    entries = _parse_event_urls(event_sitemap_xml)
    log.info("sitemap: %d event URLs discovered", len(entries))

    # Step 3: fetch each event detail page
    rate_limit = float(source.legal.get("rate_limit_s", 3))
    structured: list[dict] = []
    for i, entry in enumerate(entries[:max_pages]):
        try:
            html = _get(entry["url"])
            text = clean_html(html, source.fetch.content_selector)
            structured.append({
                "url": entry["url"],
                "lastmod": entry["lastmod"],
                "content": text,
            })
        except Exception as exc:
            log.warning("failed to fetch %s: %s", entry["url"], exc)
        if i < len(entries) - 1:
            sleep(rate_limit)

    log.info("sitemap: fetched %d/%d event pages", len(structured), len(entries))
    return FetchResult(
        source_id=source.id,
        url=source.fetch.sitemap_url,
        content="",
        kind="pages",
        structured=structured,
    )
