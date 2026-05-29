"""Base classes and fallback provider for LLM integration."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

DEFAULT_SUGGESTIONS = [
    "Add or improve README setup instructions and architecture notes.",
    "Introduce or expand automated tests for critical modules.",
    "Set up CI quality gates for linting, tests, and dependency checks.",
]

DEFAULT_RISKS = [
    "Potential outdated dependencies without automated vulnerability scanning.",
    "Limited validation and error handling paths may cause runtime failures.",
]

DEFAULT_TECH_DEBT = [
    "Insufficient module-level documentation can slow onboarding.",
    "Missing integration tests may hide cross-module regressions.",
]


class BaseLLMProvider(ABC):
    """Abstract provider interface for AI-generated analysis content."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when this provider can make remote inference calls."""

    @abstractmethod
    def generate_sections(self, analysis_payload: dict[str, Any]) -> dict[str, Any]:
        """Return generated sections based on static analysis payload."""


class LocalFallbackProvider(BaseLLMProvider):
    """Deterministic fallback provider that does not require API keys."""

    name = "local"

    def is_available(self) -> bool:
        return True

    def generate_sections(self, analysis_payload: dict[str, Any]) -> dict[str, Any]:
        languages = analysis_payload.get("languages") or []
        frameworks = analysis_payload.get("frameworks") or []
        dependencies = analysis_payload.get("dependencies") or []
        architecture_summary = analysis_payload.get("architecture_summary") or ""

        language_summary = ", ".join(languages[:5]) if languages else "unknown languages"
        framework_summary = ", ".join(frameworks[:5]) if frameworks else "no clear framework"

        summary = (
            "Static analysis indicates this repository is primarily built with "
            f"{language_summary}. Inferred framework usage: {framework_summary}. "
            f"Detected approximately {len(dependencies)} declared dependencies."
        )

        suggestions = list(DEFAULT_SUGGESTIONS)
        if not frameworks:
            suggestions.append("Document chosen framework patterns for consistency across modules.")
        if len(dependencies) > 80:
            suggestions.append("Audit dependency sprawl and remove unused packages.")

        risks = list(DEFAULT_RISKS)
        if "JavaScript" in languages or "TypeScript" in languages:
            risks.append("Client-side dependency supply-chain risk should be monitored.")

        technical_debt = list(DEFAULT_TECH_DEBT)

        return {
            "summary": summary,
            "architecture": architecture_summary or "Architecture summary unavailable.",
            "suggestions": suggestions,
            "technical_debt": technical_debt,
            "risks": risks,
        }


def _strip_markdown_code_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        value = value.strip("`")
        if value.lower().startswith("json"):
            value = value[4:].strip()
    return value


def parse_llm_json_payload(raw_content: str) -> dict[str, Any]:
    """Parse LLM JSON output and normalize keys."""
    content = _strip_markdown_code_fence(raw_content)
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def normalize_generated_sections(
    generated: dict[str, Any],
    static_fallback: dict[str, Any],
) -> dict[str, Any]:
    """Normalize generated content and fill missing keys from fallback."""
    result = {
        "summary": generated.get("summary") or static_fallback.get("summary", ""),
        "architecture": generated.get("architecture")
        or static_fallback.get("architecture", ""),
        "suggestions": generated.get("suggestions") or static_fallback.get("suggestions", []),
        "technical_debt": generated.get("technical_debt")
        or static_fallback.get("technical_debt", []),
        "risks": generated.get("risks") or static_fallback.get("risks", []),
    }

    for list_field in ["suggestions", "technical_debt", "risks"]:
        if not isinstance(result[list_field], list):
            result[list_field] = [str(result[list_field])]
        result[list_field] = [str(item) for item in result[list_field] if str(item).strip()]

    result["summary"] = str(result["summary"])
    result["architecture"] = str(result["architecture"])
    return result
