"""Orchestrates the stages: fetch -> extract -> normalize -> dedupe -> store."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import Source
from .dedupe import dedupe
from .extract import extract
from .fetch import fetch
from .fetch.base import FetchResult
from .models import Event
from .normalize import normalize

log = logging.getLogger(__name__)


@dataclass
class RunResult:
    source_id: str
    fetched: int
    normalized: int
    deduped: int
    stored: int
    content_hash: str


def run_source(source: Source, *, dry_run: bool = False) -> RunResult:
    log.info("fetching %s (%s)", source.id, source.fetch.type)
    fetched = fetch(source)

    # Multi-page sources: extract+store per page so events land in DB progressively.
    if fetched.kind == "pages":
        return _run_pages(fetched, source, dry_run)

    extracted = extract(fetched)
    log.info("extracted %d raw events", len(extracted))

    normalized: list[Event] = [n for raw in extracted if (n := normalize(raw, source)) is not None]
    deduped = dedupe(normalized)
    log.info("normalized=%d deduped=%d", len(normalized), len(deduped))

    stored = 0
    if not dry_run:
        from .store import store
        stored = store(deduped, source)

    return RunResult(
        source_id=source.id,
        fetched=len(extracted),
        normalized=len(normalized),
        deduped=len(deduped),
        stored=stored,
        content_hash=fetched.content_hash,
    )


def _run_pages(fetched: FetchResult, source: Source, dry_run: bool) -> RunResult:
    """Process each page through extract→normalize→store immediately so the DB fills up
    as LLM calls complete rather than waiting for all pages to finish."""
    from .extract.llm import get_default_client

    client = get_default_client()
    total_extracted = total_normalized = total_stored = 0

    for page in fetched.structured:
        page_events = client.extract_events(page["content"])
        for ev in page_events:
            if not ev.url:
                ev.url = page["url"]

        normed = [n for raw in page_events if (n := normalize(raw, source)) is not None]
        deduped = dedupe(normed)

        if not dry_run and deduped:
            from .store import store
            store(deduped, source)
            total_stored += len(deduped)

        total_extracted += len(page_events)
        total_normalized += len(normed)

    log.info("pages complete: extracted=%d normalized=%d stored=%d", total_extracted, total_normalized, total_stored)
    return RunResult(
        source_id=source.id,
        fetched=total_extracted,
        normalized=total_normalized,
        deduped=total_normalized,
        stored=total_stored,
        content_hash=fetched.content_hash,
    )
