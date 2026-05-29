"""Core analysis orchestration service."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from analysis.architecture_mapper import analyze_architecture, export_architecture_diagram
from analysis.dependency_analyzer import analyze_dependencies
from analysis.language_detector import detect_languages, sorted_language_list
from analysis.repo_cloner import clone_repository, repo_slug_from_url, validate_github_url
from llm_provider import generate_ai_sections
from report.report_generator import create_report_directory, generate_report


class AnalysisServiceError(RuntimeError):
    """Raised for unrecoverable analysis pipeline issues."""


def _build_static_summary(
    languages: list[str],
    frameworks: list[str],
    dependencies: list[str],
    architecture_summary: str,
) -> str:
    lang_text = ", ".join(languages[:5]) if languages else "unknown languages"
    framework_text = ", ".join(frameworks[:5]) if frameworks else "no obvious framework"
    return (
        f"Repository appears to use {lang_text} with {framework_text}. "
        f"Detected {len(dependencies)} declared dependencies. {architecture_summary}"
    )


def _default_suggestions() -> list[str]:
    return [
        "Add architecture and data-flow docs for faster onboarding.",
        "Increase automated test coverage around critical modules.",
        "Enable dependency update and vulnerability scanning in CI.",
    ]


def analyze_repository(repo_url: str, reports_root: Path = Path("reports")) -> dict[str, Any]:
    """Execute full repository analysis pipeline and return API-ready response."""
    normalized_url = validate_github_url(repo_url)
    repo_slug = repo_slug_from_url(normalized_url)

    report_dir = create_report_directory(repo_slug=repo_slug, output_root=reports_root)

    with tempfile.TemporaryDirectory(prefix="ai-repo-analyzer-") as tmpdir:
        workspace = Path(tmpdir)
        cloned_repo = clone_repository(normalized_url, workspace)

        language_counts = detect_languages(cloned_repo)
        languages = sorted_language_list(language_counts)

        dependency_analysis = analyze_dependencies(cloned_repo)
        architecture_analysis = analyze_architecture(cloned_repo)

        diagram_png, _diagram_dot = export_architecture_diagram(
            architecture_analysis.graph,
            output_dir=report_dir,
            filename="architecture",
        )

        static_payload = {
            "repo_url": normalized_url,
            "repo_slug": repo_slug,
            "languages": languages,
            "language_counts": language_counts,
            "frameworks": dependency_analysis.frameworks,
            "dependencies": dependency_analysis.dependencies,
            "manifests": dependency_analysis.manifests,
            "entry_points": architecture_analysis.entry_points,
            "architecture_summary": architecture_analysis.summary,
            "internal_modules": architecture_analysis.internal_modules,
        }

        generated_sections, provider_name = generate_ai_sections(static_payload)

        summary = generated_sections.get(
            "summary",
            _build_static_summary(
                languages,
                dependency_analysis.frameworks,
                dependency_analysis.dependencies,
                architecture_analysis.summary,
            ),
        )
        architecture = generated_sections.get("architecture", architecture_analysis.summary)
        suggestions = generated_sections.get("suggestions") or _default_suggestions()
        technical_debt = generated_sections.get("technical_debt") or []
        risks = generated_sections.get("risks") or []

        report_payload = {
            "summary": summary,
            "architecture": architecture,
            "languages": languages,
            "dependencies": dependency_analysis.dependencies,
            "frameworks": dependency_analysis.frameworks,
            "manifests": dependency_analysis.manifests,
            "suggestions": suggestions,
            "technical_debt": technical_debt,
            "risks": risks,
            "entry_points": architecture_analysis.entry_points,
            "provider": provider_name,
            "diagram_path": str(diagram_png.resolve()) if diagram_png else None,
        }

        report_path = generate_report(
            report_dir=report_dir,
            repo_url=normalized_url,
            repo_slug=repo_slug,
            analysis_data=report_payload,
        )

    return {
        "summary": summary,
        "languages": languages,
        "architecture": architecture,
        "suggestions": suggestions,
        "dependencies": dependency_analysis.dependencies,
        "frameworks": dependency_analysis.frameworks,
        "manifests": dependency_analysis.manifests,
        "risks": risks,
        "technical_debt": technical_debt,
        "entry_points": architecture_analysis.entry_points,
        "diagram_path": str(diagram_png.resolve()) if diagram_png else None,
        "report_path": str(report_path.resolve()),
        "provider": provider_name,
    }
