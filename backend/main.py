"""FastAPI entrypoint for AI Repo Analyzer."""
# ruff: noqa: E402

from __future__ import annotations

import os
import sys
from pathlib import Path

import gradio as gr
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.repo_cloner import InvalidRepositoryURLError, RepositoryCloneError
from backend.api.schemas import AnalyzeRequest, AnalyzeResponse
from backend.api.service import AnalysisServiceError, analyze_repository
from frontend.ui import create_ui

load_dotenv()

app = FastAPI(
    title="AI Repo Analyzer",
    description="Analyze GitHub repositories and generate architecture/security reports.",
    version="1.0.0",
)

try:
    gradio_ui = create_ui()
    app = gr.mount_gradio_app(app, gradio_ui, path="/ui")
except Exception:
    # API remains available even if Gradio cannot be mounted in constrained environments.
    pass


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        result = analyze_repository(request.repo_url)
        return AnalyzeResponse(**result)
    except InvalidRepositoryURLError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RepositoryCloneError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AnalysisServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unexpected failure during repository analysis.",
        ) from exc


if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
