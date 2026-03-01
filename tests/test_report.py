from __future__ import annotations

from pathlib import Path

from report.report_generator import create_report_directory, generate_report


def test_generate_report(tmp_path: Path) -> None:
    report_dir = create_report_directory("acme-demo", output_root=tmp_path)
    report_path = generate_report(
        report_dir=report_dir,
        repo_url="https://github.com/acme/demo.git",
        repo_slug="acme-demo",
        analysis_data={
            "summary": "A demo repository",
            "architecture": "Layered architecture",
            "languages": ["Python"],
            "dependencies": ["fastapi", "uvicorn"],
            "frameworks": ["FastAPI"],
            "manifests": ["requirements.txt"],
            "suggestions": ["Improve tests"],
            "technical_debt": ["Missing docs"],
            "risks": ["No SCA pipeline"],
            "entry_points": ["main.py"],
            "provider": "local",
            "diagram_path": None,
        },
    )

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# AI Repo Analyzer Report" in content
    assert "## Repository Summary" in content
    assert "## Architecture Diagram" in content
