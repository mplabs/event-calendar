"""Shared fetch types and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

USER_AGENT = (
    "JenaEventAggregator/0.1 (+https://events.example.org; respectful aggregator)"
)


@dataclass
class FetchResult:
    """Raw content from a source.

    `kind` tells the extractor how to treat `content`:
      - "text"   -> clean text / HTML to send to the LLM
      - "events" -> already-structured events (e.g. parsed iCal/RSS) as dicts
    """

    source_id: str
    url: str
    content: str
    kind: str = "text"
    structured: list[dict] = field(default_factory=list)
