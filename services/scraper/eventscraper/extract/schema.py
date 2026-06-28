"""JSON schema + prompt for LLM event extraction."""

from __future__ import annotations

from ..models import TAXONOMY

# JSON schema handed to the model (OpenRouter structured output / json_schema).
EXTRACTION_SCHEMA = {
    "name": "event_list",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": ["string", "null"]},
                        "start": {
                            "type": "string",
                            "description": "Start datetime as printed, ISO-8601 if possible (Europe/Berlin).",
                        },
                        "end": {"type": ["string", "null"]},
                        "all_day": {"type": "boolean"},
                        "venue_name": {"type": ["string", "null"]},
                        "venue_address": {"type": ["string", "null"]},
                        "categories": {
                            "type": "array",
                            "items": {"type": "string", "enum": TAXONOMY},
                        },
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "price_min": {"type": ["number", "null"]},
                        "price_max": {"type": ["number", "null"]},
                        "currency": {"type": "string"},
                        "url": {"type": ["string", "null"]},
                        "ticket_url": {"type": ["string", "null"]},
                        "image_url": {"type": ["string", "null"]},
                        "organizer": {"type": ["string", "null"]},
                    },
                    "required": ["title", "start"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["events"],
        "additionalProperties": False,
    },
}

SYSTEM_PROMPT = (
    "You extract structured event listings from messy German web pages. "
    "Return ONLY events that have a concrete date. Use Europe/Berlin time. "
    "Do not invent events or fields you cannot find; use null for unknowns. "
    "Prefer a short neutral summary over copying long marketing text. "
    "Map each event to one or more categories from the provided taxonomy."
)


def build_user_prompt(content: str) -> str:
    taxonomy = ", ".join(TAXONOMY)
    return (
        f"Taxonomy (use only these for `categories`): {taxonomy}.\n\n"
        "Extract every event from the page content below.\n\n"
        "=== PAGE CONTENT ===\n"
        f"{content}"
    )
