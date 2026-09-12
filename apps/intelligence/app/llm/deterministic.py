"""
Deterministic provider.

Default engine for the challenge build: rules and lexicons only, no network.
Consistency matters more than prose creativity, and a judge can inspect exactly
why each claim was produced. Semantic comparison falls back to UNCERTAIN rather
than guessing — uncertainty is a valid, visible state in WUNZI.
"""

from __future__ import annotations

from typing import Any

from app.llm.base import LlmProvider


class DeterministicProvider(LlmProvider):
    name = "deterministic"

    async def complete_json(self, system: str, user: str, schema_hint: str | None = None) -> dict[str, Any]:
        return {
            "relationship": "UNCERTAIN",
            "reason": "deterministic engine: no semantic model available for free-text comparison",
            "confidence": None,
        }
