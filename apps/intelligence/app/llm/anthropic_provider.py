"""Anthropic-backed semantic parsing. Low temperature; strict JSON contract."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.llm.base import LlmProvider, StructuredOutputError


class AnthropicProvider(LlmProvider):
    name = "anthropic"

    async def complete_json(self, system: str, user: str, schema_hint: str | None = None) -> dict[str, Any]:
        settings = get_settings()
        prompt = user if not schema_hint else f"{user}\n\nRespond with JSON only, matching:\n{schema_hint}"

        for attempt in range(2):  # parse → repair once → give up
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{settings.llm_base_url.rstrip('/')}/messages",
                    headers={
                        "x-api-key": settings.llm_api_key or "",
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": settings.llm_model,
                        "max_tokens": settings.llm_max_tokens,
                        "temperature": settings.llm_temperature,
                        "system": system,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
            response.raise_for_status()
            body = response.json()

            text = "".join(
                block.get("text", "") for block in body.get("content", []) if block.get("type") == "text"
            )

            try:
                return self.parse_json(text)
            except StructuredOutputError:
                if attempt == 1:
                    raise
                prompt = (
                    f"{prompt}\n\nYour previous answer was not valid JSON. "
                    "Return only a JSON object, with no preamble and no code fences."
                )

        raise StructuredOutputError("Unreachable")
