"""Language detection utilities for source repositories."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".md": "Markdown",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".toml": "TOML",
    ".dockerfile": "Dockerfile",
}

SHEBANG_LANGUAGE_MAP = {
    "python": "Python",
    "bash": "Shell",
    "sh": "Shell",
    "zsh": "Shell",
    "node": "JavaScript",
    "ruby": "Ruby",
    "php": "PHP",
}


def _detect_shebang_language(file_path: Path) -> str | None:
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
            first_line = handle.readline().strip()
    except OSError:
        return None

    if not first_line.startswith("#!"):
        return None

    lowered = first_line.lower()
    for key, language in SHEBANG_LANGUAGE_MAP.items():
        if key in lowered:
            return language
    return None


def detect_languages(repo_path: Path) -> dict[str, int]:
    """Detect languages in a repository by extension and shebang inspection."""
    if not repo_path.exists() or not repo_path.is_dir():
        return {}

    counts: Counter[str] = Counter()

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        root_path = Path(root)

        for filename in files:
            file_path = root_path / filename
            suffix = file_path.suffix.lower()

            language = EXTENSION_LANGUAGE_MAP.get(suffix)
            if not language and filename.lower() == "dockerfile":
                language = "Dockerfile"

            if not language and suffix == "":
                language = _detect_shebang_language(file_path)

            if language:
                counts[language] += 1

    return dict(counts)


def sorted_language_list(language_counts: dict[str, int]) -> list[str]:
    """Return languages sorted by descending file counts then name."""
    return [
        lang
        for lang, _count in sorted(language_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
