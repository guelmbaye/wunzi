"""
One WUNZI contract for every speech model.

No downstream code may branch on `provider == "sahara"` except benchmark
labelling and sponsor-specific UX. That is what makes the Sponsor Outcome Delta
a fair measurement rather than a story.
"""

from __future__ import annotations

import abc
import time
from typing import Any

from app.schemas.speech import NormalizedTranscript, TranscriptionConfig


class AsrError(RuntimeError):
    def __init__(self, provider: str, message: str, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class AsrProvider(abc.ABC):
    """Adapters contain no mediation logic. That separation is the sponsor proof."""

    name: str = "base"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abc.abstractmethod
    async def _call(self, audio_uri: str, config: TranscriptionConfig) -> dict[str, Any]:
        """Provider-specific request. Returns the raw provider payload."""

    @abc.abstractmethod
    def _normalize(self, raw: dict[str, Any]) -> NormalizedTranscript:
        """Provider payload → NormalizedTranscript. Never synthesise missing metadata."""

    async def transcribe(self, audio_uri: str, config: TranscriptionConfig) -> NormalizedTranscript:
        started = time.perf_counter()
        raw = await self._call(audio_uri, config)
        transcript = self._normalize(raw)
        transcript.latency_ms = int((time.perf_counter() - started) * 1000)
        transcript.provider = self.name
        transcript.model = transcript.model or self.model
        return transcript

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def verify_model(self) -> str | None:
        """
        Confirms the configured model exists, before a run spends anything.

        Returns an error string, or None when the check passed or the provider
        has no way to answer. A wrong model name is invisible until the first
        real call, and a run of two hundred discovers it two hundred times.

        Providers that cannot be probed return None rather than guessing — an
        unverifiable model is not the same as a missing one.
        """
        return None
