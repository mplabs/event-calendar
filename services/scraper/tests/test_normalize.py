from datetime import datetime
from zoneinfo import ZoneInfo

from eventscraper.config import FetchConfig, Source
from eventscraper.dedupe import dedupe
from eventscraper.models import ExtractedEvent
from eventscraper.normalize import dedupe_hash, normalize, parse_dt

SOURCE = Source(
    id="t", name="Test", region="jena", fetch=FetchConfig(type="html", url="x")
)


def test_parse_dt_assumes_berlin_when_naive():
    dt = parse_dt("2026-07-01 20:00")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.utcoffset() == datetime(2026, 7, 1, tzinfo=ZoneInfo("Europe/Berlin")).utcoffset()


def test_parse_dt_german_format():
    dt = parse_dt("01.07.2026 20:30")
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2026, 7, 1)


def test_normalize_drops_event_without_date():
    raw = ExtractedEvent(title="No date", start="")
    assert normalize(raw, SOURCE) is None


def test_normalize_builds_event_and_hash():
    raw = ExtractedEvent(
        title="Konzert", start="2026-07-01 20:00", venue_name="Kassablanca"
    )
    ev = normalize(raw, SOURCE)
    assert ev is not None
    assert ev.region == "jena"
    assert ev.dedupe_hash == dedupe_hash("Konzert", ev.starts_at, "Kassablanca")


def test_dedupe_hash_is_stable_across_minor_variations():
    dt = parse_dt("2026-07-01 20:00")
    a = dedupe_hash("Großes  Konzert", dt, "Kassablanca")
    b = dedupe_hash("grosses konzert", dt, "kassablanca")
    assert a == b


def test_dedupe_keeps_richer_record():
    sparse = normalize(ExtractedEvent(title="Show", start="2026-07-01 20:00"), SOURCE)
    rich = normalize(
        ExtractedEvent(
            title="Show",
            start="2026-07-01 20:00",
            description="full info",
            url="https://x",
            categories=["Film"],
        ),
        SOURCE,
    )
    out = dedupe([sparse, rich])
    assert len(out) == 1
    assert out[0].description == "full info"
