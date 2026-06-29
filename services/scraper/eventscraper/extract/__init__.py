"""Extraction: turn raw fetch results into ExtractedEvent objects."""

from __future__ import annotations

from ..fetch.base import FetchResult
from ..models import ExtractedEvent
from .llm import LLMClient, get_default_client


def extract(result: FetchResult, client: LLMClient | None = None) -> list[ExtractedEvent]:
    """Extract events from a fetch result.

    kind="events"  -> pre-structured (feed); skip the LLM.
    kind="pages"   -> list of {url, content} dicts (sitemap crawl); one LLM
                      call per page, url propagated onto ExtractedEvent.
    kind="text"    -> single HTML/text blob; one LLM call.
    """
    if result.kind == "events":
        return [ExtractedEvent(**_coerce(e)) for e in result.structured if e.get("title")]

    client = client or get_default_client()

    if result.kind == "pages":
        events: list[ExtractedEvent] = []
        for page in result.structured:
            page_events = client.extract_events(page["content"])
            for ev in page_events:
                if not ev.url:
                    ev.url = page["url"]
            events.extend(page_events)
        return events

    return client.extract_events(result.content)


def _coerce(raw: dict) -> dict:
    """Map a pre-structured feed dict onto ExtractedEvent fields."""
    return {
        "title": raw.get("title") or "",
        "description": raw.get("description"),
        "start": raw.get("start") or "",
        "end": raw.get("end"),
        "venue_name": raw.get("venue_name"),
        "url": raw.get("url"),
    }


__all__ = ["extract", "LLMClient", "get_default_client"]
