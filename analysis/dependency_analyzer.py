"""Dependency and framework detection across common ecosystem manifests."""

from __future__ import annotations

import json
import re
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

DEP_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+")

FRAMEWORK_KEYWORDS = {
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "React": ["react"],
    "Next.js": ["next"],
    "Vue": ["vue"],
    "Angular": ["angular"],
    "Express": ["express"],
    "Spring": ["spring", "spring-boot"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["torch", "pytorch"],
    "LangChain": ["langchain"],
}


@dataclass
class DependencyAnalysis:
    dependencies: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    manifests: list[str] = field(default_factory=list)


def _normalize_dependency(raw: str) -> str | None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith("-e "):
        line = line[3:].strip()

    if "#" in line:
        line = line.split("#", 1)[0].strip()

    if "@" in line and "git+" not in line and line.count("@") == 1:
        line = line.split("@", 1)[0].strip()

    match = DEP_TOKEN_RE.match(line)
    if not match:
        return None

    return match.group(0).lower()


def _parse_requirements_file(path: Path) -> list[str]:
    deps: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        dep = _normalize_dependency(line)
        if dep:
            deps.append(dep)
    return deps


def _parse_pyproject(path: Path) -> list[str]:
    deps: list[str] = []
    data = tomllib.loads(path.read_text(encoding="utf-8", errors="ignore"))

    project = data.get("project", {})
    for item in project.get("dependencies", []):
        dep = _normalize_dependency(item)
        if dep:
            deps.append(dep)

    optional_deps = project.get("optional-dependencies", {})
    for values in optional_deps.values():
        for item in values:
            dep = _normalize_dependency(item)
            if dep:
                deps.append(dep)

    tool_poetry = data.get("tool", {}).get("poetry", {})
    poetry_deps = tool_poetry.get("dependencies", {})
    for name in poetry_deps:
        if name.lower() == "python":
            continue
        dep = _normalize_dependency(name)
        if dep:
            deps.append(dep)

    return deps


def _parse_package_json(path: Path) -> list[str]:
    deps: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    for section in ["dependencies", "devDependencies", "peerDependencies"]:
        for dep_name in (data.get(section) or {}).keys():
            dep = _normalize_dependency(dep_name)
            if dep:
                deps.append(dep)
    return deps


def _parse_go_mod(path: Path) -> list[str]:
    deps: list[str] = []
    in_require_block = False
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if line.startswith("require ("):
            in_require_block = True
            continue
        if in_require_block and line == ")":
            in_require_block = False
            continue
        if line.startswith("require ") and not in_require_block:
            parts = line.split()
            if len(parts) >= 2:
                deps.append(parts[1].lower())
        elif in_require_block and line:
            parts = line.split()
            if parts:
                deps.append(parts[0].lower())
    return deps


def _parse_cargo_toml(path: Path) -> list[str]:
    deps: list[str] = []
    data = tomllib.loads(path.read_text(encoding="utf-8", errors="ignore"))
    for key in ["dependencies", "dev-dependencies", "build-dependencies"]:
        section = data.get(key, {})
        for dep_name in section.keys():
            dep = _normalize_dependency(dep_name)
            if dep:
                deps.append(dep)

    workspace_section = data.get("workspace", {}).get("dependencies", {})
    for dep_name in workspace_section.keys():
        dep = _normalize_dependency(dep_name)
        if dep:
            deps.append(dep)
    return deps


def _parse_pom_xml(path: Path) -> list[str]:
    deps: list[str] = []
    tree = ET.parse(path)
    root = tree.getroot()

    # Maven files often use namespaces.
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    for artifact in root.findall(f".//{ns}dependency/{ns}artifactId"):
        if artifact.text:
            dep = _normalize_dependency(artifact.text)
            if dep:
                deps.append(dep)
    return deps


def _infer_frameworks(dependencies: list[str]) -> list[str]:
    normalized = set(dependencies)
    frameworks: list[str] = []
    for framework, keywords in FRAMEWORK_KEYWORDS.items():
        if any(any(keyword in dep for keyword in keywords) for dep in normalized):
            frameworks.append(framework)
    return sorted(frameworks)


def analyze_dependencies(repo_path: Path) -> DependencyAnalysis:
    """Analyze dependency manifests and infer frameworks."""
    dependencies: set[str] = set()
    manifests: list[str] = []

    for path in repo_path.rglob("requirements*.txt"):
        manifests.append(str(path.relative_to(repo_path)))
        dependencies.update(_parse_requirements_file(path))

    pyproject_path = repo_path / "pyproject.toml"
    if pyproject_path.exists():
        manifests.append("pyproject.toml")
        dependencies.update(_parse_pyproject(pyproject_path))

    package_json_path = repo_path / "package.json"
    if package_json_path.exists():
        manifests.append("package.json")
        dependencies.update(_parse_package_json(package_json_path))

    go_mod_path = repo_path / "go.mod"
    if go_mod_path.exists():
        manifests.append("go.mod")
        dependencies.update(_parse_go_mod(go_mod_path))

    cargo_toml_path = repo_path / "Cargo.toml"
    if cargo_toml_path.exists():
        manifests.append("Cargo.toml")
        dependencies.update(_parse_cargo_toml(cargo_toml_path))

    pom_xml_path = repo_path / "pom.xml"
    if pom_xml_path.exists():
        manifests.append("pom.xml")
        dependencies.update(_parse_pom_xml(pom_xml_path))

    sorted_dependencies = sorted(dependencies)
    frameworks = _infer_frameworks(sorted_dependencies)

    return DependencyAnalysis(
        dependencies=sorted_dependencies,
        frameworks=frameworks,
        manifests=sorted(manifests),
    )
