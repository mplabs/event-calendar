"""Static HTML fetcher: download a page and reduce it to clean text for the LLM."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import Source
from .base import USER_AGENT, FetchResult

_STRIP_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def _get(url: str) -> str:
    resp = httpx.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True
    )
    resp.raise_for_status()
    return resp.text


def clean_html(html: str, selector: str | None = None) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()
    root = soup.select_one(selector) if selector else soup.body or soup
    text = root.get_text(separator="\n", strip=True) if root else ""
    # Collapse runs of blank lines.
    lines = [ln for ln in (l.strip() for l in text.splitlines()) if ln]
    return "\n".join(lines)


def fetch_html(source: Source) -> FetchResult:
    html = _get(source.fetch.url)
    text = clean_html(html, source.fetch.content_selector)
    return FetchResult(
        source_id=source.id, url=source.fetch.url, content=text, kind="text"
    )
