"""Repository cloning and URL validation utilities."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

GITHUB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


class InvalidRepositoryURLError(ValueError):
    """Raised when a repository URL is not a valid GitHub public URL."""


class RepositoryCloneError(RuntimeError):
    """Raised when cloning a repository fails."""


def validate_github_url(repo_url: str) -> str:
    """Validate and normalize a GitHub repository URL.

    Args:
        repo_url: User-provided repository URL.

    Returns:
        Normalized clone URL in the form https://github.com/{owner}/{repo}.git

    Raises:
        InvalidRepositoryURLError: If the URL is invalid.
    """
    if not repo_url or not isinstance(repo_url, str):
        raise InvalidRepositoryURLError("Repository URL must be a non-empty string.")

    candidate = repo_url.strip()
    match = GITHUB_URL_RE.fullmatch(candidate)
    if not match:
        raise InvalidRepositoryURLError(
            "Repository URL must match https://github.com/{owner}/{repo}."
        )

    owner = match.group("owner")
    repo = match.group("repo")
    return f"https://github.com/{owner}/{repo}.git"


def repo_slug_from_url(repo_url: str) -> str:
    """Convert a GitHub URL into a filesystem-safe repo slug."""
    normalized = validate_github_url(repo_url)
    match = GITHUB_URL_RE.fullmatch(normalized.removesuffix(".git"))
    if not match:
        # Should never happen because validate_github_url already checked format.
        raise InvalidRepositoryURLError("Failed to parse repository URL.")

    owner = match.group("owner")
    repo = match.group("repo")
    raw = f"{owner}-{repo}"
    return re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-")


def clone_repository(repo_url: str, workspace: Path, timeout_seconds: int = 180) -> Path:
    """Clone a public GitHub repository into the given workspace.

    Args:
        repo_url: GitHub URL to clone.
        workspace: Existing writable directory for clone target.
        timeout_seconds: Clone timeout in seconds.

    Returns:
        Path to cloned repository.

    Raises:
        InvalidRepositoryURLError: If the URL is invalid.
        RepositoryCloneError: If git clone fails.
    """
    normalized_url = validate_github_url(repo_url)
    slug = repo_slug_from_url(normalized_url)

    workspace.mkdir(parents=True, exist_ok=True)
    target_dir = workspace / slug

    if target_dir.exists():
        raise RepositoryCloneError(f"Target directory already exists: {target_dir}")

    cmd = ["git", "clone", "--depth", "1", normalized_url, str(target_dir)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RepositoryCloneError("git executable was not found in PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepositoryCloneError(
            f"Timed out cloning repository after {timeout_seconds} seconds."
        ) from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        msg = stderr or stdout or "Unknown clone error."
        raise RepositoryCloneError(f"Failed to clone repository: {msg}")

    if not target_dir.exists():
        raise RepositoryCloneError("Clone command succeeded but target directory is missing.")

    return target_dir
