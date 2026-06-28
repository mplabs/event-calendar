"""In-batch dedupe. Cross-source/cross-run merging happens at upsert time via
the unique dedupe_hash; this just collapses duplicates within a single fetch."""

from __future__ import annotations

from .models import Event


def dedupe(events: list[Event]) -> list[Event]:
    seen: dict[str, Event] = {}
    for ev in events:
        existing = seen.get(ev.dedupe_hash)
        if existing is None:
            seen[ev.dedupe_hash] = ev
            continue
        # Prefer the record with more information.
        if _score(ev) > _score(existing):
            seen[ev.dedupe_hash] = ev
    return list(seen.values())


def _score(ev: Event) -> int:
    fields = [ev.description, ev.url, ev.ticket_url, ev.image_url, ev.venue]
    return sum(1 for f in fields if f) + len(ev.categories)
