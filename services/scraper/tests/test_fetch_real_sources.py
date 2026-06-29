"""Golden-file tests for the two vertical-slice sources.

These tests use saved HTML fixtures and do NOT hit the network. They verify
that the fetch + clean pipeline produces the expected text structure so we
catch regressions if either site's layout changes (at which point the fixture
needs refreshing from the live site).

Run:  pytest tests/test_fetch_real_sources.py -v
"""

import xml.etree.ElementTree as ET

from eventscraper.fetch.http import clean_html
from eventscraper.fetch.sitemap import _find_event_sitemap, _parse_event_urls


FIXTURES = "tests/fixtures"


# ---------------------------------------------------------------------------
# c-keller.de
# ---------------------------------------------------------------------------

def test_ckeller_selector_yields_events():
    html = open(f"{FIXTURES}/ckeller_konzerte.html").read()
    text = clean_html(html, "#col2_content")
    assert "Jun" in text or "Jul" in text, "no month abbreviation found"
    assert len([l for l in text.splitlines() if l.strip()]) >= 10, "too few lines"


def test_ckeller_date_title_structure():
    """Each event block should have a day number, a month abbreviation, then a title."""
    import re
    html = open(f"{FIXTURES}/ckeller_konzerte.html").read()
    text = clean_html(html, "#col2_content")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Find lines that look like day numbers (1-31)
    day_lines = [l for l in lines if re.fullmatch(r"\d{1,2}", l)]
    assert len(day_lines) >= 3, f"expected ≥3 day-number lines, got {day_lines}"
    # Find German month abbreviations
    months = {"Jan","Feb","Mär","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"}
    month_lines = [l for l in lines if l in months]
    assert len(month_lines) >= 3, f"expected ≥3 month lines, got {month_lines}"


# ---------------------------------------------------------------------------
# jena-veranstaltungen.de
# ---------------------------------------------------------------------------

def test_jena_event_detail_cleans_correctly():
    html = open(f"{FIXTURES}/jena_event_detail.html").read()
    text = clean_html(html, "main")
    assert "FRANK GAUDLITZ" in text
    assert "2026" in text
    assert "Kunstsammlung" in text or "Jena" in text


def test_jena_event_detail_has_occurrence_dates():
    """The detail page lists all occurrence dates for multi-day exhibitions."""
    import re
    html = open(f"{FIXTURES}/jena_event_detail.html").read()
    text = clean_html(html, "main")
    # Should contain multiple date lines like "Sonntag, 28.06.2026"
    dates = re.findall(r"\d{2}\.\d{2}\.\d{4}", text)
    assert len(dates) >= 3, f"expected ≥3 date strings, got {dates[:5]}"


def test_jena_sitemap_index_finds_event_sitemap():
    xml = open(f"{FIXTURES}/jena_sitemap_index.xml").read()
    url = _find_event_sitemap(xml, "ndsdestinationdataevent")
    assert url is not None
    assert "ndsdestinationdataevent" in url


def test_jena_sitemap_index_filter_miss_returns_none():
    xml = open(f"{FIXTURES}/jena_sitemap_index.xml").read()
    url = _find_event_sitemap(xml, "nonexistent_filter")
    assert url is None
