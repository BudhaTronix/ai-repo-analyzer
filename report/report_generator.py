"""Markdown report generation for repository analysis results."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def create_report_directory(repo_slug: str, output_root: Path = Path("reports")) -> Path:
    """Create a timestamped report directory for a repository analysis run."""
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    directory = output_root / f"{repo_slug}_{timestamp}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _as_bulleted(items: list[str]) -> str:
    if not items:
        return "- None detected"
    return "\n".join(f"- {item}" for item in items)


def generate_report(
    report_dir: Path,
    repo_url: str,
    repo_slug: str,
    analysis_data: dict[str, Any],
) -> Path:
    """Generate markdown report in the supplied report directory."""
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.md"

    summary = analysis_data.get("summary", "")
    architecture = analysis_data.get("architecture", "")
    languages = analysis_data.get("languages", [])
    dependencies = analysis_data.get("dependencies", [])
    frameworks = analysis_data.get("frameworks", [])
    manifests = analysis_data.get("manifests", [])
    suggestions = analysis_data.get("suggestions", [])
    technical_debt = analysis_data.get("technical_debt", [])
    risks = analysis_data.get("risks", [])
    entry_points = analysis_data.get("entry_points", [])
    provider = analysis_data.get("provider", "local")
    diagram_path = analysis_data.get("diagram_path")

    diagram_section = "Diagram generation failed or was unavailable in this environment."
    if diagram_path:
        diagram_name = Path(diagram_path).name
        diagram_section = f"![Architecture Diagram]({diagram_name})"

    content = f"""# AI Repo Analyzer Report

## Metadata
- Repository URL: {repo_url}
- Repository Slug: {repo_slug}
- Generated At (UTC): {datetime.now(tz=UTC).isoformat()}
- LLM Provider: {provider}

## Repository Summary
{summary}

## Architecture Explanation
{architecture}

## Detected Languages
{_as_bulleted(languages)}

## Frameworks
{_as_bulleted(frameworks)}

## Dependencies
Total dependencies detected: {len(dependencies)}

{_as_bulleted(dependencies)}

## Dependency Manifest Files
{_as_bulleted(manifests)}

## Entry Points
{_as_bulleted(entry_points)}

## Suggestions
{_as_bulleted(suggestions)}

## Technical Debt
{_as_bulleted(technical_debt)}

## Potential Security Risks
{_as_bulleted(risks)}

## Architecture Diagram
{diagram_section}
"""

    report_path.write_text(content, encoding="utf-8")
    return report_path
