"""Provider registry. Swapping the ASR must never require touching downstream code."""

from __future__ import annotations

from app.asr.base import AsrProvider
from app.asr.fixture import FixtureProvider
from app.asr.model_b import ModelBProvider
from app.asr.model_c import ModelCProvider
from app.asr.sahara import SaharaProvider
from app.asr.whisper import WhisperProvider
from app.config import Settings, get_settings

_LIVE_PROVIDERS: dict[str, type[AsrProvider]] = {
    "sahara": SaharaProvider,
    "whisper": WhisperProvider,
    "model_b": ModelBProvider,
    "model_c": ModelCProvider,
}


def provider_names() -> list[str]:
    return list(_LIVE_PROVIDERS)


def get_provider(name: str, settings: Settings | None = None, force_mode: str | None = None) -> AsrProvider:
    settings = settings or get_settings()

    if name not in _LIVE_PROVIDERS:
        raise KeyError(f"Unknown ASR provider '{name}'. Known: {', '.join(_LIVE_PROVIDERS)}")

    mode = (force_mode or settings.wunzi_mode).lower()
    config = settings.provider_config(name)

    if mode == "fixture":
        return FixtureProvider(name, settings.fixture_root)

    provider = _LIVE_PROVIDERS[name](
        api_key=config["api_key"],
        base_url=config["base_url"],
        model=config["model"],
    )

    if not provider.is_configured():
        # Never silently substitute a provider: the caller decides what to do.
        raise KeyError(f"Provider '{name}' is not configured for live mode (missing API key).")

    return provider
