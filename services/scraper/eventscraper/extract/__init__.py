"""Extraction: turn raw fetch results into ExtractedEvent objects."""

from __future__ import annotations

from ..fetch.base import FetchResult
from ..models import ExtractedEvent
from .llm import LLMClient, get_default_client


def extract(result: FetchResult, client: LLMClient | None = None) -> list[ExtractedEvent]:
    """Extract events from a fetch result.

    kind="events"  -> pre-structured (feed); skip the LLM.
    kind="text"    -> single HTML/text blob; one LLM call.

    kind="pages" (sitemap crawl) is handled in pipeline._run_pages, not here.
    """
    if result.kind == "events":
        return [
            ExtractedEvent(**{**e, "title": e.get("title") or "", "start": e.get("start") or ""})
            for e in result.structured if e.get("title")
        ]

    client = client or get_default_client()
    return client.extract_events(result.content)


