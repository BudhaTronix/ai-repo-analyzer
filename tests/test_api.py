from __future__ import annotations

from fastapi.testclient import TestClient

from analysis.repo_cloner import InvalidRepositoryURLError, RepositoryCloneError
from backend.main import app

client = TestClient(app)


def test_analyze_endpoint_success(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_analyze(repo_url: str):
        return {
            "summary": "Test summary",
            "languages": ["Python"],
            "architecture": "Test architecture",
            "suggestions": ["Add tests"],
            "dependencies": ["fastapi"],
            "frameworks": ["FastAPI"],
            "manifests": ["requirements.txt"],
            "risks": ["None"],
            "technical_debt": ["Low coverage"],
            "entry_points": ["main.py"],
            "diagram_path": None,
            "report_path": "/tmp/report.md",
            "provider": "local",
        }

    monkeypatch.setattr("backend.main.analyze_repository", fake_analyze)

    response = client.post("/analyze", json={"repo_url": "https://github.com/acme/demo"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "Test summary"
    assert payload["languages"] == ["Python"]
    assert payload["report_path"] == "/tmp/report.md"


def test_analyze_endpoint_invalid_url(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_analyze(repo_url: str):
        raise InvalidRepositoryURLError("invalid")

    monkeypatch.setattr("backend.main.analyze_repository", fake_analyze)

    response = client.post("/analyze", json={"repo_url": "bad-url"})
    assert response.status_code == 422


def test_analyze_endpoint_clone_failure(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_analyze(repo_url: str):
        raise RepositoryCloneError("clone failed")

    monkeypatch.setattr("backend.main.analyze_repository", fake_analyze)

    response = client.post("/analyze", json={"repo_url": "https://github.com/acme/demo"})
    assert response.status_code == 400
