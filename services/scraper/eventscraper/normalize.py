"""Normalize ExtractedEvent -> Event: parse dates, timezone, build dedupe hash."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

from dateutil import parser as dateparser

from .config import Source
from .models import Event, ExtractedEvent, Venue

BERLIN = ZoneInfo("Europe/Berlin")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    dt: datetime | None = None
    # ISO first (year-first); dateutil's dayfirst=True would mis-read "2026-07-01".
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        # Fall back to fuzzy parsing for German day-first formats (01.07.2026).
        try:
            dt = dateparser.parse(value, dayfirst=True, fuzzy=True)
        except (ValueError, OverflowError):
            return None
    if dt is None:
        return None
    # Assume local Jena time when the source omits a timezone.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BERLIN)
    return dt


def _slug(text: str) -> str:
    # casefold first so German ß -> "ss" (NFKD leaves ß intact); then drop accents.
    text = text.casefold()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def dedupe_hash(title: str, starts_at: datetime, venue_name: str | None) -> str:
    """Stable key so the same event from multiple sources merges into one row.

    Date granularity is the day; minor title/venue variations collapse via slug.
    """
    basis = "|".join(
        [_slug(title), starts_at.astimezone(BERLIN).strftime("%Y-%m-%d"), _slug(venue_name or "")]
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def normalize(raw: ExtractedEvent, source: Source) -> Event | None:
    starts_at = parse_dt(raw.start)
    if starts_at is None:
        return None  # no usable date -> drop

    venue = None
    if raw.venue_name:
        venue = Venue(
            name=raw.venue_name.strip(),
            address=raw.venue_address,
            region=source.region,
        )

    return Event(
        title=raw.title.strip(),
        description=raw.description,
        starts_at=starts_at,
        ends_at=parse_dt(raw.end),
        all_day=raw.all_day,
        venue=venue,
        categories=raw.categories,
        tags=raw.tags,
        price_min=raw.price_min,
        price_max=raw.price_max,
        currency=raw.currency or "EUR",
        url=raw.url,
        ticket_url=raw.ticket_url,
        image_url=raw.image_url,
        organizer=raw.organizer,
        region=source.region,
        dedupe_hash=dedupe_hash(raw.title, starts_at, raw.venue_name),
    )
