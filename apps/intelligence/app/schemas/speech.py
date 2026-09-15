from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptionConfig(BaseModel):
    """
    `llm_corrections` and `category` exist because Intron's API applies LLM
    post-processing by default, under a telehealth category. For a benchmark
    that compares speech models, corrections are off: otherwise a corrected
    pipeline is scored against a raw transcript. For production use they are a
    product decision, made explicitly rather than inherited from a default.
    """

    llm_corrections: bool = False
    category: str | None = None
    languages: list[str] = Field(default_factory=lambda: ["rw", "en", "fr"])
    diarize: bool = False
    timestamps: bool = True
    pipeline_version: str | None = None


class NormalizedSegment(BaseModel):
    start_ms: int
    end_ms: int
    text: str
    # Nullable on purpose: never synthesise provider metadata.
    language: str | None = None
    confidence: float | None = None


class NormalizedTranscript(BaseModel):
    provider: str
    model: str | None = None
    provider_version: str | None = None
    text: str
    segments: list[NormalizedSegment] = Field(default_factory=list)
    latency_ms: int | None = None
    source_mode: str = "live"
    fixture_origin: str | None = None
    is_placeholder: bool = False
    raw: dict | None = None

    @property
    def mean_confidence(self) -> float | None:
        values = [s.confidence for s in self.segments if s.confidence is not None]
        return sum(values) / len(values) if values else None

    @property
    def language_switch_count(self) -> int:
        languages = [s.language for s in self.segments if s.language]
        return sum(1 for a, b in zip(languages, languages[1:]) if a != b)


class TranscribeRequest(BaseModel):
    audio_id: str
    audio_uri: str
    provider: str = "sahara"
    audio_sha256: str | None = None
    mode: str | None = None
    fixture_key: str | None = None
    pipeline_version: str | None = None
    config: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
