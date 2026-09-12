from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LlmProvider
from app.llm.deterministic import DeterministicProvider
from app.llm.openai_provider import OpenAiProvider

_PROVIDERS = {
    "deterministic": DeterministicProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAiProvider,
}


def get_llm(settings: Settings | None = None) -> LlmProvider:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    if provider != "deterministic" and not settings.llm_api_key:
        # Falling back is safe here: the deterministic engine never invents
        # semantics, it only returns UNCERTAIN.
        return DeterministicProvider()

    return _PROVIDERS.get(provider, DeterministicProvider)()
