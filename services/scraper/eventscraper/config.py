"""Configuration: environment settings and the sources.yaml registry."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SOURCES_PATH = Path(os.environ.get("SOURCES_PATH", "sources.yaml"))


@dataclass
class Settings:
    openrouter_api_key: str = os.environ.get("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.environ.get(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    model_extract: str = os.environ.get(
        "LLM_MODEL_EXTRACT", "google/gemini-2.0-flash-001"
    )
    app_url: str = os.environ.get("OPENROUTER_APP_URL", "")
    app_name: str = os.environ.get("OPENROUTER_APP_NAME", "Jena Event Aggregator")


@dataclass
class FetchConfig:
    type: str
    url: str = ""
    content_selector: str | None = None
    # sitemap fetch type extras
    sitemap_url: str = ""
    sitemap_filter: str = ""


@dataclass
class Source:
    id: str
    name: str
    region: str
    fetch: FetchConfig
    enabled: bool = False
    legal: dict = field(default_factory=dict)


def load_sources(path: Path = SOURCES_PATH) -> list[Source]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources: list[Source] = []
    for raw in data.get("sources", []):
        fetch = FetchConfig(**raw["fetch"])
        sources.append(
            Source(
                id=raw["id"],
                name=raw["name"],
                region=raw["region"],
                fetch=fetch,
                enabled=raw.get("enabled", False),
                legal=raw.get("legal", {}),
            )
        )
    return sources


def get_source(source_id: str, path: Path = SOURCES_PATH) -> Source:
    for source in load_sources(path):
        if source.id == source_id:
            return source
    raise KeyError(f"source not found in {path}: {source_id}")


settings = Settings()
