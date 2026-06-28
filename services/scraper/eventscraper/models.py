"""Canonical data model shared across pipeline stages.

`ExtractedEvent` is what the LLM returns (loose, source-shaped). `Event` is the
normalized, store-ready record. Keep these in sync with db/migrations.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# Fixed interest taxonomy (top level). The LLM maps each event to >=1 of these.
TAXONOMY = [
    "Music / Concerts",
    "Clubs & Parties",
    "Theatre & Performance",
    "Film",
    "Art & Exhibitions",
    "Literature & Talks",
    "Family & Kids",
    "Food & Drink",
    "Sports & Outdoors",
    "Markets & Festivals",
    "Community & Politics",
    "Uni & Science",
]


class ExtractedEvent(BaseModel):
    """One event as returned by the LLM extractor (pre-normalization)."""

    title: str
    description: str | None = None
    # Local wall-clock strings as found on the page; normalized later.
    start: str
    end: str | None = None
    all_day: bool = False
    venue_name: str | None = None
    venue_address: str | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    price_min: float | None = None
    price_max: float | None = None
    currency: str = "EUR"
    url: str | None = None
    ticket_url: str | None = None
    image_url: str | None = None
    organizer: str | None = None


class Venue(BaseModel):
    name: str
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    region: str | None = None
    website: str | None = None


class Event(BaseModel):
    """Normalized, store-ready event."""

    title: str
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    all_day: bool = False
    venue: Venue | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    price_min: float | None = None
    price_max: float | None = None
    currency: str = "EUR"
    url: str | None = None
    ticket_url: str | None = None
    image_url: str | None = None
    organizer: str | None = None
    region: str | None = None
    dedupe_hash: str = ""
