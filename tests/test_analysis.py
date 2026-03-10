from __future__ import annotations

import json
import subprocess
from pathlib import Path

import networkx as nx
import pytest

from analysis import architecture_mapper
from analysis.dependency_analyzer import analyze_dependencies
from analysis.language_detector import detect_languages
from analysis.repo_cloner import (
    InvalidRepositoryURLError,
    clone_repository,
    repo_slug_from_url,
    validate_github_url,
)


def test_validate_github_url_accepts_valid_url() -> None:
    normalized = validate_github_url("https://github.com/example/project")
    assert normalized == "https://github.com/example/project.git"


def test_validate_github_url_rejects_invalid_url() -> None:
    with pytest.raises(InvalidRepositoryURLError):
        validate_github_url("https://gitlab.com/example/project")


def test_repo_slug_from_url() -> None:
    assert repo_slug_from_url("https://github.com/acme/demo") == "acme-demo"


def test_clone_repository_runs_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(cmd, capture_output, text, timeout, check):  # type: ignore[no-untyped-def]
        target = Path(cmd[-1])
        target.mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    repo_path = clone_repository("https://github.com/example/repo", tmp_path)
    assert repo_path.exists()
    assert repo_path.name == "example-repo"


def test_detect_languages(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "index.js").write_text("console.log('hi')\n", encoding="utf-8")
    (tmp_path / "script").write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")

    languages = detect_languages(tmp_path)
    assert languages["Python"] == 1
    assert languages["JavaScript"] == 1
    assert languages["Shell"] == 1


def test_dependency_analyzer(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("fastapi==0.115.6\nrequests>=2.0\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": "^18.0.0"},
                "devDependencies": {"typescript": "^5.0.0"},
            }
        ),
        encoding="utf-8",
    )

    analysis = analyze_dependencies(tmp_path)

    assert "fastapi" in analysis.dependencies
    assert "requests" in analysis.dependencies
    assert "react" in analysis.dependencies
    assert "FastAPI" in analysis.frameworks
    assert "React" in analysis.frameworks


def test_architecture_diagram_fallback_png(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    graph = nx.DiGraph()
    graph.add_edge("app.main", "fastapi")
    graph.add_edge("app.main", "app.routes")

    def fail_png_render(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("forced png rendering failure")

    monkeypatch.setattr("networkx.drawing.nx_pydot.to_pydot", fail_png_render)

    png_path, _dot_path = architecture_mapper.export_architecture_diagram(graph, tmp_path)
    assert png_path is not None
    assert png_path.exists()
