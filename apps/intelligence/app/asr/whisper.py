"""
Comparator 1 — OpenAI Whisper large-v3.

A strong, widely recognised multilingual baseline. The point of the benchmark is
not to pick weak competitors.
"""

from __future__ import annotations

from typing import Any

from app.asr.base import AsrProvider
from app.asr.http_client import content_type_for, post_json, read_audio_bytes
from app.schemas.speech import NormalizedSegment, NormalizedTranscript, TranscriptionConfig


class WhisperProvider(AsrProvider):
    name = "whisper"

    async def _call(self, audio_uri: str, config: TranscriptionConfig) -> dict[str, Any]:
        audio = await read_audio_bytes(audio_uri)
        filename, mime = content_type_for(audio_uri)

        return await post_json(
            self.name,
            f"{(self.base_url or '').rstrip('/')}/audio/transcriptions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            files={"file": (filename, audio, mime)},
            data={
                "model": self.model,
                "response_format": "verbose_json",
                "timestamp_granularities[]": "segment",
            },
        )

    async def verify_model(self) -> str | None:
        """One cheap GET against /models/{id}, which costs nothing."""
        import httpx

        url = f"{(self.base_url or '').rstrip('/')}/models/{self.model}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url, headers={"Authorization": f"Bearer {self.api_key}"}
                )
        except Exception:  # noqa: BLE001 — a probe failure is not a run failure
            return None

        if response.status_code == 404:
            return (
                f"model '{self.model}' does not exist on this API. OpenAI's hosted "
                "name is 'whisper-1'; 'whisper-large-v3' is the Hugging Face name."
            )
        if response.status_code in (401, 403):
            return "the API key was rejected."

        return None

    def _normalize(self, raw: dict[str, Any]) -> NormalizedTranscript:
        segments = [
            NormalizedSegment(
                start_ms=int(float(item.get("start", 0)) * 1000),
                end_ms=int(float(item.get("end", 0)) * 1000),
                text=item.get("text", "").strip(),
                # Whisper reports one language per request, not per span:
                # we do not invent per-segment language metadata.
                language=raw.get("language"),
                confidence=None,
            )
            for item in raw.get("segments", [])
        ]

        return NormalizedTranscript(
            provider=self.name,
            model=self.model,
            text=raw.get("text", ""),
            segments=segments,
            source_mode="live",
            raw=raw,
        )
