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


def _process(fetched: FetchResult, source: Source, dry_run: bool, url: str | None = None) -> tuple[int, int, int, int]:
    """extract -> normalize -> dedupe -> store one already-fetched blob.

    Returns (extracted, normalized, deduped, stored). `url` backfills events missing one."""
    extracted = extract(fetched)
    if url:
        for ev in extracted:
            if not ev.url:
                ev.url = url

    normalized: list[Event] = [n for raw in extracted if (n := normalize(raw, source)) is not None]
    deduped = dedupe(normalized)

    stored = 0
    if not dry_run and deduped:
        from .store import store
        stored = store(deduped, source)

    return len(extracted), len(normalized), len(deduped), stored


def run_source(source: Source, *, dry_run: bool = False) -> RunResult:
    log.info("fetching %s (%s)", source.id, source.fetch.type)
    fetched = fetch(source)

    # Multi-page sources: fetch+process one URL at a time so events land in the DB
    # within seconds and partial progress survives a restart mid-crawl.
    if fetched.kind == "pages":
        from time import sleep

        from .fetch.http import _get, clean_html

        rate_limit = float(source.legal.get("rate_limit_s", 3))
        total_extracted = total_normalized = total_deduped = total_stored = 0

        for i, url in enumerate(fetched.structured):
            if i:
                sleep(rate_limit)  # polite crawl delay between page fetches
            try:
                content = clean_html(_get(url), source.fetch.content_selector)
            except Exception as exc:  # skip a bad page, keep crawling
                log.warning("failed to fetch %s: %s", url, exc)
                continue

            page = FetchResult(source_id=source.id, url=url, content=content, kind="text")
            e, n, d, s = _process(page, source, dry_run, url=url)
            total_extracted += e
            total_normalized += n
            total_deduped += d
            total_stored += s

        log.info("pages complete: extracted=%d normalized=%d stored=%d", total_extracted, total_normalized, total_stored)
        return RunResult(
            source_id=source.id,
            fetched=total_extracted,
            normalized=total_normalized,
            deduped=total_deduped,
            stored=total_stored,
        )

    extracted, normalized, deduped, stored = _process(fetched, source, dry_run)
    log.info("normalized=%d deduped=%d", normalized, deduped)
    return RunResult(
        source_id=source.id,
        fetched=extracted,
        normalized=normalized,
        deduped=deduped,
        stored=stored,
    )
