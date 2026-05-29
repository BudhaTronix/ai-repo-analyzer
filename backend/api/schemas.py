"""Pydantic schemas for API request/response payloads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., description="Public GitHub repository URL")


class AnalyzeResponse(BaseModel):
    summary: str
    languages: list[str]
    architecture: str
    suggestions: list[str]
    dependencies: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    manifests: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    technical_debt: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    diagram_path: str | None = None
    report_path: str
    provider: str = "local"
