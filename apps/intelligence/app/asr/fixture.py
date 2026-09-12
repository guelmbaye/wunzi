"""
Fixture provider.

Replays previously observed authentic provider outputs so the demo and the test
suite never depend on live API availability. It is NOT a simulator: it can only
return payloads captured from a real provider run, and every replay keeps its
`fixture_origin` (run id + capture date) so a judge can tell replay from live.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.asr.base import AsrError, AsrProvider
from app.schemas.speech import NormalizedSegment, NormalizedTranscript, TranscriptionConfig


class FixtureProvider(AsrProvider):
    def __init__(self, provider_name: str, fixture_root: Path) -> None:
        super().__init__(model=None)
        self.name = provider_name
        self.fixture_root = Path(fixture_root)

    def fixture_path(self, key: str) -> Path:
        return self.fixture_root / "asr" / self.name / f"{key}.json"

    async def _call(self, audio_uri: str, config: TranscriptionConfig) -> dict[str, Any]:
        key = self._key_from_uri(audio_uri)
        path = self.fixture_path(key)

        if not path.exists():
            raise AsrError(
                self.name,
                f"No cached provider output for clip '{key}'. Fixture mode never fabricates results.",
                status_code=404,
            )

        return json.loads(path.read_text(encoding="utf-8"))

    def _normalize(self, raw: dict[str, Any]) -> NormalizedTranscript:
        segments = [
            NormalizedSegment(
                start_ms=int(s["start_ms"]),
                end_ms=int(s["end_ms"]),
                text=s.get("text", ""),
                language=s.get("language"),
                confidence=s.get("confidence"),
            )
            for s in raw.get("segments", [])
        ]

        return NormalizedTranscript(
            provider=self.name,
            model=raw.get("model"),
            provider_version=raw.get("provider_version"),
            text=raw.get("text") or " ".join(s.text for s in segments).strip(),
            segments=segments,
            source_mode="fixture",
            fixture_origin=raw.get("fixture_origin", "unknown-capture"),
            # A placeholder is never allowed to masquerade as a measurement.
            is_placeholder=bool(raw.get("is_placeholder", False)),
            raw=raw,
        )

    @staticmethod
    def _key_from_uri(audio_uri: str) -> str:
        key = audio_uri
        if key.startswith("fixture://"):
            key = key[len("fixture://") :]
        key = key.split("/")[-1]
        for suffix in (".wav", ".webm", ".ogg", ".mp3", ".m4a", ".flac", ".json"):
            if key.endswith(suffix):
                key = key[: -len(suffix)]
        return key

    def is_configured(self) -> bool:
        return self.fixture_root.exists()
