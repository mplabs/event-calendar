"""Fetch layer: turn a source into raw content for extraction."""

from __future__ import annotations

from ..config import Source
from .base import FetchResult
from .feed import fetch_feed
from .http import fetch_html
from .sitemap import fetch_sitemap


def fetch(source: Source) -> FetchResult:
    kind = source.fetch.type
    if kind == "feed":
        return fetch_feed(source)
    if kind == "html":
        return fetch_html(source)
    if kind == "sitemap":
        return fetch_sitemap(source)
    raise NotImplementedError(f"fetch type not implemented yet: {kind}")


