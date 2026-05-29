"""Gradio frontend for AI Repo Analyzer."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import gradio as gr
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _to_markdown(result: dict[str, Any]) -> str:
    suggestions = result.get("suggestions") or []
    risks = result.get("risks") or []
    technical_debt = result.get("technical_debt") or []
    languages = result.get("languages") or []
    frameworks = result.get("frameworks") or []

    def bullets(items: list[str]) -> str:
        if not items:
            return "- None"
        return "\n".join(f"- {item}" for item in items)

    return (
        f"## Summary\n{result.get('summary', '')}\n\n"
        f"## Architecture\n{result.get('architecture', '')}\n\n"
        f"## Detected Languages\n{bullets(languages)}\n\n"
        f"## Frameworks\n{bullets(frameworks)}\n\n"
        f"## Suggestions\n{bullets(suggestions)}\n\n"
        f"## Technical Debt\n{bullets(technical_debt)}\n\n"
        f"## Potential Risks\n{bullets(risks)}"
    )


def analyze_repo(repo_url: str) -> tuple[dict[str, Any] | None, str, str | None, str | None, str]:
    """Call backend API and adapt output for Gradio components."""
    if not repo_url or not repo_url.strip():
        return None, "", None, None, "Please enter a GitHub repository URL."

    endpoint = f"{API_BASE_URL}/analyze"
    try:
        response = requests.post(endpoint, json={"repo_url": repo_url.strip()}, timeout=600)
    except requests.RequestException as exc:
        return None, "", None, None, f"Failed to connect to backend: {exc}"

    if response.status_code != 200:
        detail = "Request failed"
        try:
            detail = response.json().get("detail", detail)
        except json.JSONDecodeError:
            detail = response.text or detail
        return None, "", None, None, f"API error ({response.status_code}): {detail}"

    result: dict[str, Any] = response.json()
    markdown = _to_markdown(result)

    diagram_path = result.get("diagram_path")
    if diagram_path and not Path(diagram_path).exists():
        diagram_path = None

    report_path = result.get("report_path")
    if report_path and not Path(report_path).exists():
        report_path = None

    status = f"Analysis complete using provider: {result.get('provider', 'local')}"
    return result, markdown, diagram_path, report_path, status


def create_ui() -> gr.Blocks:
    """Build Gradio Blocks UI."""
    with gr.Blocks(title="AI Repo Analyzer", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# AI Repo Analyzer")
        gr.Markdown(
            "Paste a public GitHub repository URL to generate a codebase analysis and markdown report."
        )

        repo_url = gr.Textbox(
            label="GitHub Repository URL",
            placeholder="https://github.com/owner/repository",
        )
        analyze_button = gr.Button("Analyze Repository", variant="primary")

        status = gr.Textbox(label="Status", interactive=False)
        result_json = gr.JSON(label="Raw API Response")
        result_markdown = gr.Markdown(label="Analysis")
        diagram = gr.Image(label="Architecture Diagram", type="filepath")
        report_file = gr.File(label="Download Report")

        analyze_button.click(
            fn=analyze_repo,
            inputs=[repo_url],
            outputs=[result_json, result_markdown, diagram, report_file, status],
        )

    return demo


if __name__ == "__main__":
    port = int(os.getenv("GRADIO_PORT", "7860"))
    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=port)
