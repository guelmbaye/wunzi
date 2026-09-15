"""Runtime configuration for the WUNZI intelligence service."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # ── Runtime ────────────────────────────────────────────────────────────
    wunzi_mode: str = "fixture"  # live | fixture
    pipeline_version: str = "pipeline-v1"
    dataset_version: str = "dataset-v1"
    internal_ai_service_secret: str = "change-me-internal-shared-secret"
    intelligence_log_level: str = "info"

    # ── ASR providers ──────────────────────────────────────────────────────
    default_asr_provider: str = "sahara"

    sahara_api_key: str | None = None
    # Published at docs.voice.intron.io/docs/stt/file-upload-sync.
    sahara_base_url: str = "https://infer.voice.intron.io"
    # The sync upload endpoint takes no model parameter; this is a label for
    # the benchmark report, not something sent on the wire.
    sahara_model: str = "intron-sahara-stt"

    whisper_api_key: str | None = None
    whisper_base_url: str = "https://api.openai.com/v1"
    whisper_model: str = "whisper-large-v3"

    model_b_api_key: str | None = None
    model_b_base_url: str | None = None
    model_b_model: str = "model_b"

    model_c_api_key: str | None = None
    model_c_base_url: str | None = None
    model_c_model: str = "model_c"

    asr_timeout_seconds: float = 120.0
    # Retries live here and nowhere else. Laravel does not retry transcription:
    # two layers of three attempts is nine ASR calls for one recording, and with
    # the queue job's own tries, twenty-seven. Worst case here is
    # asr_timeout_seconds x (1 + asr_max_retries) = 240s, which must stay under
    # INTELLIGENCE_TIMEOUT on the Laravel side.
    asr_max_retries: int = 1

    # ── LLM ────────────────────────────────────────────────────────────────
    llm_provider: str = "deterministic"  # deterministic | anthropic | openai
    llm_api_key: str | None = None
    llm_model: str = "claude-sonnet-4-6"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    llm_base_url: str = "https://api.anthropic.com/v1"

    # ── Critical Speech Guard ──────────────────────────────────────────────
    guard_amount_confidence_threshold: float = 0.90
    guard_date_confidence_threshold: float = 0.85
    guard_default_confidence_threshold: float = 0.80

    # ── Storage ────────────────────────────────────────────────────────────
    s3_endpoint: str | None = None
    s3_bucket: str = "wunzi-audio"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None

    fixture_root: Path = Path("/benchmark/fixtures")
    benchmark_root: Path = Path("/benchmark")

    @property
    def fixture_mode(self) -> bool:
        return self.wunzi_mode.lower() == "fixture"

    def provider_config(self, provider: str) -> dict:
        return {
            "sahara": {
                "api_key": self.sahara_api_key,
                "base_url": self.sahara_base_url,
                "model": self.sahara_model,
            },
            "whisper": {
                "api_key": self.whisper_api_key,
                "base_url": self.whisper_base_url,
                "model": self.whisper_model,
            },
            "model_b": {
                "api_key": self.model_b_api_key,
                "base_url": self.model_b_base_url,
                "model": self.model_b_model,
            },
            "model_c": {
                "api_key": self.model_c_api_key,
                "base_url": self.model_c_base_url,
                "model": self.model_c_model,
            },
        }[provider]


@lru_cache
def get_settings() -> Settings:
    return Settings()
