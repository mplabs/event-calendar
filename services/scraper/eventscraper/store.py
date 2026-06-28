"""Persistence: upsert venues, events, and source provenance into Postgres."""

from __future__ import annotations

import logging

import psycopg
from psycopg.rows import dict_row

from .config import Source, settings
from .models import Event

log = logging.getLogger(__name__)


def connect() -> psycopg.Connection:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(settings.database_url, row_factory=dict_row)


def upsert_source(conn: psycopg.Connection, source: Source) -> None:
    conn.execute(
        """
        INSERT INTO source (id, name, region, enabled, last_run_at)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (id) DO UPDATE
          SET name = EXCLUDED.name,
              region = EXCLUDED.region,
              enabled = EXCLUDED.enabled,
              last_run_at = now()
        """,
        (source.id, source.name, source.region, source.enabled),
    )


def _upsert_venue(conn: psycopg.Connection, event: Event) -> str | None:
    if not event.venue:
        return None
    row = conn.execute(
        """
        INSERT INTO venue (name, address, lat, lng, region, website)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (name, region) DO UPDATE
          SET address = COALESCE(EXCLUDED.address, venue.address)
        RETURNING id
        """,
        (
            event.venue.name,
            event.venue.address,
            event.venue.lat,
            event.venue.lng,
            event.venue.region,
            event.venue.website,
        ),
    ).fetchone()
    return row["id"] if row else None


def upsert_event(conn: psycopg.Connection, event: Event, source: Source) -> str:
    venue_id = _upsert_venue(conn, event)
    row = conn.execute(
        """
        INSERT INTO event (
            title, description, starts_at, ends_at, all_day, venue_id,
            categories, tags, price_min, price_max, currency,
            url, ticket_url, image_url, organizer, region, dedupe_hash, last_seen_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
        ON CONFLICT (dedupe_hash) DO UPDATE SET
            description = COALESCE(EXCLUDED.description, event.description),
            ends_at     = COALESCE(EXCLUDED.ends_at, event.ends_at),
            venue_id    = COALESCE(EXCLUDED.venue_id, event.venue_id),
            categories  = CASE WHEN cardinality(EXCLUDED.categories) > 0
                               THEN EXCLUDED.categories ELSE event.categories END,
            ticket_url  = COALESCE(EXCLUDED.ticket_url, event.ticket_url),
            image_url   = COALESCE(EXCLUDED.image_url, event.image_url),
            status      = 'active',
            last_seen_at = now()
        RETURNING id
        """,
        (
            event.title, event.description, event.starts_at, event.ends_at,
            event.all_day, venue_id, event.categories, event.tags,
            event.price_min, event.price_max, event.currency, event.url,
            event.ticket_url, event.image_url, event.organizer, event.region,
            event.dedupe_hash,
        ),
    ).fetchone()
    event_id = row["id"]

    conn.execute(
        """
        INSERT INTO event_source (event_id, source_id, source_url, raw_hash, extracted_at)
        VALUES (%s, %s, %s, %s, now())
        ON CONFLICT (event_id, source_id) DO UPDATE
          SET source_url = EXCLUDED.source_url,
              raw_hash = EXCLUDED.raw_hash,
              extracted_at = now()
        """,
        (event_id, source.id, event.url, event.dedupe_hash),
    )
    return event_id


def store(events: list[Event], source: Source) -> int:
    with connect() as conn:
        upsert_source(conn, source)
        for event in events:
            upsert_event(conn, event, source)
        conn.commit()
    log.info("stored %d events from %s", len(events), source.id)
    return len(events)
