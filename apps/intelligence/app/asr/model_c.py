"""
Comparator 3 — NVIDIA Nemotron-ASR or another credible global/local ASR.

The final choice depends on participant access and actual support for the
evaluation audio; the adapter contract is what matters here.
"""

from __future__ import annotations

import base64
from typing import Any

from app.asr.base import AsrProvider
from app.asr.http_client import post_json, read_audio_bytes
from app.schemas.speech import NormalizedSegment, NormalizedTranscript, TranscriptionConfig


class ModelCProvider(AsrProvider):
    name = "model_c"

    async def _call(self, audio_uri: str, config: TranscriptionConfig) -> dict[str, Any]:
        audio = await read_audio_bytes(audio_uri)

        return await post_json(
            self.name,
            f"{(self.base_url or '').rstrip('/')}/asr",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json_body={
                "model": self.model,
                "audio_b64": base64.b64encode(audio).decode("ascii"),
                "language_hints": config.languages,
                "word_timestamps": config.timestamps,
            },
        )

    def _normalize(self, raw: dict[str, Any]) -> NormalizedTranscript:
        segments = [
            NormalizedSegment(
                start_ms=int(item.get("start_ms", 0)),
                end_ms=int(item.get("end_ms", 0)),
                text=item.get("text", "").strip(),
                language=item.get("language"),
                confidence=item.get("confidence"),
            )
            for item in raw.get("utterances", raw.get("segments", []))
        ]

        return NormalizedTranscript(
            provider=self.name,
            model=self.model,
            text=raw.get("transcript", "") or " ".join(s.text for s in segments).strip(),
            segments=segments,
            source_mode="live",
            raw=raw,
        )
