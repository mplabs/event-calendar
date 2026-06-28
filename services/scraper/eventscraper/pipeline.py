"""Orchestrates the stages: fetch -> extract -> normalize -> dedupe -> store."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import Source
from .dedupe import dedupe
from .extract import extract
from .fetch import fetch
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


def run_source(source: Source, *, persist: bool = True, dry_run: bool = False) -> RunResult:
    log.info("fetching %s (%s)", source.id, source.fetch.type)
    fetched = fetch(source)

    extracted = extract(fetched)
    log.info("extracted %d raw events", len(extracted))

    normalized: list[Event] = []
    for raw in extracted:
        ev = normalize(raw, source)
        if ev is not None:
            normalized.append(ev)

    deduped = dedupe(normalized)
    log.info("normalized=%d deduped=%d", len(normalized), len(deduped))

    stored = 0
    if persist and not dry_run:
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
