"""
Comparator 1 — OpenAI Whisper large-v3.

A strong, widely recognised multilingual baseline. The point of the benchmark is
not to pick weak competitors.
"""

from __future__ import annotations

from typing import Any

from app.asr.base import AsrProvider
from app.asr.http_client import post_json, read_audio_bytes
from app.schemas.speech import NormalizedSegment, NormalizedTranscript, TranscriptionConfig


class WhisperProvider(AsrProvider):
    name = "whisper"

    async def _call(self, audio_uri: str, config: TranscriptionConfig) -> dict[str, Any]:
        audio = await read_audio_bytes(audio_uri)

        return await post_json(
            self.name,
            f"{(self.base_url or '').rstrip('/')}/audio/transcriptions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            files={"file": ("audio.wav", audio, "audio/wav")},
            data={
                "model": self.model,
                "response_format": "verbose_json",
                "timestamp_granularities[]": "segment",
            },
        )

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
