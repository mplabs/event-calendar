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
    """Fetch → extract → normalize → store one URL at a time so events land in the DB
    within seconds and partial progress survives a restart mid-crawl."""
    from time import sleep

    from .extract.llm import get_default_client
    from .fetch.http import _get, clean_html
    from .store import store

    client = get_default_client()
    rate_limit = float(source.legal.get("rate_limit_s", 3))
    total_extracted = total_normalized = total_stored = 0

    for i, url in enumerate(fetched.structured):
        if i:
            sleep(rate_limit)  # polite crawl delay between page fetches
        try:
            content = clean_html(_get(url), source.fetch.content_selector)
        except Exception as exc:  # skip a bad page, keep crawling
            log.warning("failed to fetch %s: %s", url, exc)
            continue

        page_events = client.extract_events(content)
        for ev in page_events:
            if not ev.url:
                ev.url = url

        normed = [n for raw in page_events if (n := normalize(raw, source)) is not None]
        deduped = dedupe(normed)

        if not dry_run and deduped:
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
