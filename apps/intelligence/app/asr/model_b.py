"""
Comparator 2 — Gemini-class speech model.

Configured through generic env vars so the strongest accessible transcription
configuration available at implementation time can be plugged in without
touching downstream code.
"""

from __future__ import annotations

import base64
from typing import Any

from app.asr.base import AsrProvider
from app.asr.http_client import post_json, read_audio_bytes
from app.schemas.speech import NormalizedSegment, NormalizedTranscript, TranscriptionConfig


class ModelBProvider(AsrProvider):
    name = "model_b"

    async def _call(self, audio_uri: str, config: TranscriptionConfig) -> dict[str, Any]:
        audio = await read_audio_bytes(audio_uri)

        return await post_json(
            self.name,
            f"{(self.base_url or '').rstrip('/')}/speech:recognize",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json_body={
                "model": self.model,
                "audio": {"content": base64.b64encode(audio).decode("ascii")},
                "config": {
                    "languageCodes": config.languages,
                    "enableWordTimeOffsets": config.timestamps,
                    "enableAutomaticPunctuation": True,
                },
            },
        )

    def _normalize(self, raw: dict[str, Any]) -> NormalizedTranscript:
        segments: list[NormalizedSegment] = []

        for result in raw.get("results", []):
            alternative = (result.get("alternatives") or [{}])[0]
            segments.append(
                NormalizedSegment(
                    start_ms=int(float(result.get("resultStartOffsetSeconds", 0)) * 1000),
                    end_ms=int(float(result.get("resultEndOffsetSeconds", 0)) * 1000),
                    text=alternative.get("transcript", "").strip(),
                    language=result.get("languageCode"),
                    confidence=alternative.get("confidence"),
                )
            )

        return NormalizedTranscript(
            provider=self.name,
            model=self.model,
            text=" ".join(s.text for s in segments).strip(),
            segments=segments,
            source_mode="live",
            raw=raw,
        )
