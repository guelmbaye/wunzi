"""OpenAI-backed semantic parsing with JSON response mode when available."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.llm.base import LlmProvider


class OpenAiProvider(LlmProvider):
    name = "openai"

    async def complete_json(self, system: str, user: str, schema_hint: str | None = None) -> dict[str, Any]:
        settings = get_settings()
        prompt = user if not schema_hint else f"{user}\n\nJSON schema:\n{schema_hint}"

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key or ''}"},
                json={
                    "model": settings.llm_model,
                    "temperature": settings.llm_temperature,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
        response.raise_for_status()
        body = response.json()

        return self.parse_json(body["choices"][0]["message"]["content"])
