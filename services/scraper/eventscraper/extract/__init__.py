"""Extraction: turn raw fetch results into ExtractedEvent objects."""

from __future__ import annotations

from ..fetch.base import FetchResult
from ..models import ExtractedEvent
from .llm import get_default_client


def extract(result: FetchResult) -> list[ExtractedEvent]:
    """Extract events from a fetch result.

    kind="events"  -> pre-structured (feed); skip the LLM.
    kind="text"    -> single HTML/text blob; one LLM call.

    kind="pages" (sitemap crawl) is handled per-URL in pipeline.run_source, not here.
    """
    if result.kind == "events":
        return [
            ExtractedEvent(**{**e, "title": e.get("title") or "", "start": e.get("start") or ""})
            for e in result.structured if e.get("title")
        ]

    return get_default_client().extract_events(result.content)


