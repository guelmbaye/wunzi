"""
LLM boundary.

The LLM MAY: parse semantics, extract claims, resolve pronouns, canonicalise,
compare propositions, generate clarification questions, synthesise neutral prose.

The LLM MUST NOT: decide truth, infer credibility, fabricate missing facts,
select a winning party, propose a settlement.

No state transition ever occurs from malformed model output.
"""

from __future__ import annotations

import abc
import json
import re
from typing import Any

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class StructuredOutputError(ValueError):
    pass


class LlmProvider(abc.ABC):
    name = "base"

    @abc.abstractmethod
    async def complete_json(self, system: str, user: str, schema_hint: str | None = None) -> dict[str, Any]:
        """Returns validated JSON. Implementations retry once on parse failure."""

    @staticmethod
    def parse_json(text: str) -> dict[str, Any]:
        candidate = text.strip()

        fenced = _JSON_FENCE.search(candidate)
        if fenced:
            candidate = fenced.group(1).strip()

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError(f"Model did not return valid JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise StructuredOutputError("Model returned JSON that is not an object.")

        return parsed
