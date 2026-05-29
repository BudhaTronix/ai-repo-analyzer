"""Kimi-2 provider implementation via OpenAI-compatible API."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from llm_provider.base import (
    BaseLLMProvider,
    LocalFallbackProvider,
    normalize_generated_sections,
    parse_llm_json_payload,
)


class KimiProvider(BaseLLMProvider):
    """Provider for Kimi model using an OpenAI-compatible endpoint."""

    name = "kimi"

    def __init__(self) -> None:
        self.api_key = os.getenv("KIMI_API_KEY", "").strip()
        self.base_url = os.getenv("KIMI_BASE_URL", "https://api.moonshot.ai/v1").strip()
        self.model = os.getenv("KIMI_MODEL", "moonshotai/kimi-k2-instruct").strip()

        self._client: OpenAI | None = None
        if self.api_key:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def is_available(self) -> bool:
        return bool(self.api_key and self._client)

    def _build_messages(self, analysis_payload: dict[str, Any]) -> list[dict[str, str]]:
        system = (
            "You are a staff engineer specializing in repository audits. "
            "Return strict JSON with keys summary, architecture, suggestions, technical_debt, risks."
        )
        user = (
            "Generate production-focused repo analysis from this static payload.\n"
            f"Payload:\n{json.dumps(analysis_payload, indent=2)}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def generate_sections(self, analysis_payload: dict[str, Any]) -> dict[str, Any]:
        if not self.is_available() or not self._client:
            return LocalFallbackProvider().generate_sections(analysis_payload)

        fallback = LocalFallbackProvider().generate_sections(analysis_payload)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(analysis_payload),
            temperature=0.2,
        )

        content = response.choices[0].message.content or ""
        parsed = parse_llm_json_payload(content)
        return normalize_generated_sections(parsed, fallback)
