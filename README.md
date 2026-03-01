# AI Repo Analyzer

AI Repo Analyzer is a production-ready web application that clones and analyzes public GitHub repositories, then generates architecture insights, dependency breakdowns, risk suggestions, and a downloadable Markdown report.

## Features

- FastAPI backend with `POST /analyze`
- Gradio frontend for interactive repository analysis
- Repository cloning with GitHub URL validation
- Static analysis for:
  - programming languages
  - dependency manifests and inferred frameworks
  - architecture graph and entry points
- Optional AI enrichment via pluggable providers:
  - OpenAI-compatible API
  - NVIDIA Kimi-2 via OpenAI-compatible endpoint
  - local fallback mode (no API key required)
- Architecture diagram export (`PNG` + `DOT`) using `networkx` and Graphviz
- Markdown report generation under `reports/`
- Docker support and GitHub Actions CI

## Project Structure

```text
ai-repo-analyzer/
  backend/
    main.py
    api/
      schemas.py
      service.py
  analysis/
    repo_cloner.py
    language_detector.py
    dependency_analyzer.py
    architecture_mapper.py
  llm_provider/
    base.py
    openai_provider.py
    kimi_provider.py
  report/
    report_generator.py
  frontend/
    ui.py
  tests/
    test_analysis.py
    test_api.py
    test_report.py
  .github/workflows/ci.yml
  Dockerfile
  requirements.txt
  .env.example
```

## Architecture Flow

1. User submits a GitHub URL.
2. Backend validates URL and clones repository into a temporary workspace.
3. Static analyzers inspect languages, dependencies, framework signals, imports, and entry points.
4. Architecture graph is generated and exported to `PNG`/`DOT`.
5. LLM provider (if configured) enriches summary, suggestions, and risk sections.
6. Markdown report is written to `reports/<repo>_<timestamp>/report.md`.
7. API returns response payload with paths to generated artifacts.

## API

### Health Check

```bash
GET /health
```

Response:

```json
{"status":"ok"}
```

### Analyze Repository

```bash
POST /analyze
Content-Type: application/json
```

Request body:

```json
{
  "repo_url": "https://github.com/user/repo"
}
```

Example `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/tiangolo/fastapi"}'
```

Response fields include:

- `summary`
- `languages`
- `architecture`
- `suggestions`
- `dependencies`
- `frameworks`
- `manifests`
- `risks`
- `technical_debt`
- `entry_points`
- `diagram_path`
- `report_path`
- `provider`

## Environment Variables

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

Important keys:

- `LLM_PROVIDER=local|openai|kimi`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `KIMI_API_KEY`
- `KIMI_BASE_URL`
- `KIMI_MODEL`

If no API key is configured, the app automatically uses local fallback mode.

## Local Setup

### 1) Create environment and install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Run backend

```bash
python backend/main.py
```

Backend default URL: `http://127.0.0.1:8000`

### 3) Run frontend (separate terminal)

```bash
python frontend/ui.py
```

Frontend default URL: `http://127.0.0.1:7860`

## Docker Usage

Build image:

```bash
docker build -t ai-repo-analyzer .
```

Run backend container:

```bash
docker run --rm -p 8000:8000 --env-file .env ai-repo-analyzer
```

## Testing and Linting

```bash
ruff check .
pytest -q
```

## CI

GitHub Actions workflow: `.github/workflows/ci.yml`

Pipeline executes:

- `ruff check .`
- `pytest -q`

on pushes and pull requests for `main` and `develop`.

## UI Screenshot

Preview image:

![AI Repo Analyzer UI](docs/screenshots/ui.png)

## Notes

- Requires `git` binary and network access to clone public repositories.
- Graphviz binary is required for PNG diagram export.
- Diagram generation failures are non-fatal and report generation still completes.
