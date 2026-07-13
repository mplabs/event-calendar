"""LLM client that talks to OpenRouter."""

from __future__ import annotations

import json
import logging

import httpx
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..models import ExtractedEvent
from .schema import EXTRACTION_SCHEMA, SYSTEM_PROMPT, build_user_prompt

log = logging.getLogger(__name__)

# Keep token cost bounded; chunk longer pages upstream if needed.
MAX_CONTENT_CHARS = 24_000


class OpenRouterClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")
        self.model = model or settings.model_extract
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if settings.app_url:
            headers["HTTP-Referer"] = settings.app_url
        if settings.app_name:
            headers["X-Title"] = settings.app_name
        return headers

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=20))
    def _chat(self, content: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(content)},
            ],
            "response_format": {"type": "json_schema", "json_schema": EXTRACTION_SCHEMA},
            "temperature": 0,
        }
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        log.info("llm extract model=%s tokens=%s", self.model, usage)
        return data["choices"][0]["message"]["content"]

    def extract_events(self, content: str) -> list[ExtractedEvent]:
        if not content.strip():
            return []
        content = content[:MAX_CONTENT_CHARS]
        raw = self._chat(content)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("LLM returned non-JSON; dropping batch")
            return []

        events: list[ExtractedEvent] = []
        for item in parsed.get("events", []):
            try:
                events.append(ExtractedEvent(**item))
            except ValidationError as exc:
                log.warning("skipping invalid extracted event: %s", exc)
        return events


def get_default_client() -> OpenRouterClient:
    return OpenRouterClient()
