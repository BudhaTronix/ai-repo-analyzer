"""Provider factory and helper utilities."""

from __future__ import annotations

import os
from typing import Any

from llm_provider.base import BaseLLMProvider, LocalFallbackProvider
from llm_provider.kimi_provider import KimiProvider
from llm_provider.openai_provider import OpenAIProvider


def get_llm_provider() -> BaseLLMProvider:
    """Return configured LLM provider, defaulting to deterministic local fallback."""
    configured = os.getenv("LLM_PROVIDER", "local").strip().lower()

    if configured == "openai":
        provider = OpenAIProvider()
        return provider if provider.is_available() else LocalFallbackProvider()

    if configured == "kimi":
        provider = KimiProvider()
        return provider if provider.is_available() else LocalFallbackProvider()

    return LocalFallbackProvider()


def generate_ai_sections(analysis_payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Generate sections with configured provider and fallback on runtime failures."""
    provider = get_llm_provider()

    try:
        generated = provider.generate_sections(analysis_payload)
        return generated, provider.name
    except Exception:
        fallback = LocalFallbackProvider()
        return fallback.generate_sections(analysis_payload), fallback.name
