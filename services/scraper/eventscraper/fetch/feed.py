"""Feed fetcher: RSS/Atom (feedparser) and iCal (icalendar).

Feeds are already structured, so we emit `kind="events"` and skip the LLM for
fields we can read directly. The LLM is still used downstream to classify into
the taxonomy when categories are missing.
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import Source
from .base import USER_AGENT, FetchResult


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def _get_bytes(url: str) -> bytes:
    resp = httpx.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True
    )
    resp.raise_for_status()
    return resp.content


def _parse_ical(raw: bytes) -> list[dict]:
    from icalendar import Calendar

    cal = Calendar.from_ical(raw)
    events: list[dict] = []
    for comp in cal.walk("VEVENT"):
        def g(key: str) -> str | None:
            v = comp.get(key)
            return str(v) if v is not None else None

        dtstart = comp.get("dtstart")
        dtend = comp.get("dtend")
        events.append(
            {
                "title": g("summary") or "",
                "description": g("description"),
                "start": dtstart.dt.isoformat() if dtstart else None,
                "end": dtend.dt.isoformat() if dtend else None,
                "venue_name": g("location"),
                "url": g("url"),
            }
        )
    return events


def _parse_rss(raw: bytes) -> list[dict]:
    import feedparser

    parsed = feedparser.parse(raw)
    events: list[dict] = []
    for entry in parsed.entries:
        events.append(
            {
                "title": entry.get("title", ""),
                "description": entry.get("summary"),
                "start": entry.get("published") or entry.get("updated"),
                "url": entry.get("link"),
            }
        )
    return events


def fetch_feed(source: Source) -> FetchResult:
    raw = _get_bytes(source.fetch.url)
    head = raw[:512].lstrip().lower()
    if b"begin:vcalendar" in head or source.fetch.url.endswith(".ics"):
        events = _parse_ical(raw)
    else:
        events = _parse_rss(raw)
    return FetchResult(
        source_id=source.id,
        url=source.fetch.url,
        content="",
        kind="events",
        structured=events,
    )
