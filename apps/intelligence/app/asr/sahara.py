"""
Sahara (Intron) adapter — the sponsor speech layer.

Sahara is a first-class provider: its raw payload is preserved and inspectable,
never hidden inside an opaque orchestration layer. The adapter contains no
mediation logic whatsoever.

Sahara v2.5 is used for continuous Kinyarwanda ⇄ English ⇄ French recognition:
the language switch must not reset the claim context, so we keep per-segment
language spans whenever the provider exposes them.
"""

from __future__ import annotations

import base64
from typing import Any

from app.asr.base import AsrProvider
from app.asr.http_client import post_json, read_audio_bytes
from app.schemas.speech import NormalizedSegment, NormalizedTranscript, TranscriptionConfig


class SaharaProvider(AsrProvider):
    name = "sahara"

    async def _call(self, audio_uri: str, config: TranscriptionConfig) -> dict[str, Any]:
        audio = await read_audio_bytes(audio_uri)

        return await post_json(
            self.name,
            f"{(self.base_url or '').rstrip('/')}/transcribe",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json_body={
                "model": self.model,
                "audio": base64.b64encode(audio).decode("ascii"),
                "languages": config.languages,
                "code_switching": True,
                "timestamps": config.timestamps,
                "return_language_spans": True,
                "return_confidence": True,
            },
        )

    def _normalize(self, raw: dict[str, Any]) -> NormalizedTranscript:
        segments: list[NormalizedSegment] = []

        for item in raw.get("segments", raw.get("chunks", [])):
            segments.append(
                NormalizedSegment(
                    start_ms=_ms(item, "start"),
                    end_ms=_ms(item, "end"),
                    text=item.get("text", ""),
                    # Sahara exposes language spans; other providers may not.
                    language=item.get("language") or item.get("lang"),
                    confidence=item.get("confidence") or item.get("avg_logprob_confidence"),
                )
            )

        return NormalizedTranscript(
            provider=self.name,
            model=raw.get("model") or self.model,
            provider_version=raw.get("version"),
            text=raw.get("text", "") or " ".join(s.text for s in segments).strip(),
            segments=segments,
            source_mode="live",
            raw=raw,
        )


def _ms(item: dict[str, Any], prefix: str) -> int:
    if f"{prefix}_ms" in item:
        return int(item[f"{prefix}_ms"])
    if prefix in item:
        return int(float(item[prefix]) * 1000)
    return 0
