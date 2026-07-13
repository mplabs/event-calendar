"""Pipeline tests: per-page store + url backfill, no real DB/LLM/network."""

from __future__ import annotations

from eventscraper import extract as extract_mod
from eventscraper import pipeline, store as store_mod
from eventscraper.config import FetchConfig, Source
from eventscraper.fetch.base import FetchResult
from eventscraper.models import ExtractedEvent


class FakeClient:
    """Returns one canned event per page; leaves url empty so backfill can fill it."""

    def extract_events(self, content: str) -> list[ExtractedEvent]:
        return [ExtractedEvent(title=content, start="2026-07-01 20:00")]


def _source() -> Source:
    return Source(
        id="s1",
        name="S1",
        region="Jena",
        fetch=FetchConfig(type="sitemap"),
        legal={"rate_limit_s": 0},  # no real sleep between pages
    )


def test_pages_stores_per_page_and_backfills_url(monkeypatch):
    stored_calls: list[list] = []

    monkeypatch.setattr(extract_mod, "get_default_client", lambda: FakeClient())
    monkeypatch.setattr(store_mod, "store", lambda events, source: stored_calls.append(events) or len(events))
    monkeypatch.setattr(
        pipeline, "fetch",
        lambda source: FetchResult(
            source_id=source.id, url="", content="",
            kind="pages", structured=["http://a/1", "http://a/2"],
        ),
    )
    # per-page fetch: return the url as content so each page is distinct
    monkeypatch.setattr("eventscraper.fetch.http._get", lambda url: url)
    monkeypatch.setattr("eventscraper.fetch.http.clean_html", lambda html, sel: html)

    result = pipeline.run_source(_source())

    # stored once per page (durability), 2 pages
    assert len(stored_calls) == 2
    assert result.stored == 2
    # url backfilled onto the event that had none
    assert stored_calls[0][0].url == "http://a/1"
    assert stored_calls[1][0].url == "http://a/2"
