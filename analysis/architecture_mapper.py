"""Architecture graph extraction and diagram generation."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

PYTHON_SUFFIXES = {".py"}
JS_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
ENTRY_POINT_CANDIDATES = [
    "main.py",
    "app.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "index.js",
    "server.js",
    "src/main.ts",
    "src/main.js",
]

IMPORT_FROM_RE = re.compile(r"^\s*import\s+.+?\s+from\s+[\"']([^\"']+)[\"']", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+[\"']([^\"']+)[\"']", re.MULTILINE)
REQUIRE_RE = re.compile(r"require\([\"']([^\"']+)[\"']\)")


@dataclass
class ArchitectureAnalysis:
    graph: nx.DiGraph
    summary: str
    entry_points: list[str] = field(default_factory=list)
    internal_modules: list[str] = field(default_factory=list)


def _module_name_from_path(repo_path: Path, file_path: Path) -> str:
    rel = file_path.relative_to(repo_path)
    stemmed = rel.with_suffix("")
    parts = [p for p in stemmed.parts if p != "__init__"]
    if not parts:
        return "root"
    return ".".join(parts)


def _resolve_relative_import(module_name: str, import_name: str, level: int) -> str:
    parts = module_name.split(".")[:-1]
    if level > 0:
        cutoff = max(0, len(parts) - level + 1)
        parts = parts[:cutoff]
    if import_name:
        parts.extend(import_name.split("."))
    return ".".join(parts) if parts else import_name


def _parse_python_imports(module_name: str, file_path: Path) -> list[str]:
    targets: list[str] = []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return targets

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            import_module = node.module or ""
            if node.level:
                resolved = _resolve_relative_import(module_name, import_module, node.level)
                if resolved:
                    targets.append(resolved)
                elif node.names:
                    for alias in node.names:
                        alias_target = _resolve_relative_import(module_name, alias.name, node.level)
                        if alias_target:
                            targets.append(alias_target)
            elif import_module:
                targets.append(import_module)

    return targets


def _parse_js_imports(content: str) -> list[str]:
    imports: list[str] = []
    imports.extend(IMPORT_FROM_RE.findall(content))
    imports.extend(IMPORT_RE.findall(content))
    imports.extend(REQUIRE_RE.findall(content))
    return imports


def _detect_entry_points(repo_path: Path) -> list[str]:
    entry_points: list[str] = []
    for candidate in ENTRY_POINT_CANDIDATES:
        path = repo_path / candidate
        if path.exists():
            entry_points.append(candidate)

    package_json = repo_path / "package.json"
    if package_json.exists():
        entry_points.append("package.json:scripts")

    return sorted(set(entry_points))


def _summarize_graph(graph: nx.DiGraph) -> str:
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    if node_count == 0:
        return "No module-level dependencies were detected from source files."

    top_nodes = sorted(graph.degree, key=lambda item: item[1], reverse=True)[:5]
    hubs = ", ".join(f"{name} ({degree})" for name, degree in top_nodes if degree > 0)
    if not hubs:
        hubs = "no strong hubs"

    return (
        f"Detected {node_count} modules and {edge_count} dependency edges. "
        f"Most connected modules: {hubs}."
    )


def analyze_architecture(repo_path: Path) -> ArchitectureAnalysis:
    """Build a module dependency graph from Python and JS/TS imports."""
    graph = nx.DiGraph()
    internal_modules: set[str] = set()

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()
        if suffix not in PYTHON_SUFFIXES and suffix not in JS_SUFFIXES:
            continue

        module_name = _module_name_from_path(repo_path, file_path)
        internal_modules.add(module_name)
        graph.add_node(module_name, kind="internal")

        if suffix in PYTHON_SUFFIXES:
            for target in _parse_python_imports(module_name, file_path):
                graph.add_node(target, kind="external")
                graph.add_edge(module_name, target)
        else:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for target in _parse_js_imports(content):
                graph.add_node(target, kind="external")
                graph.add_edge(module_name, target)

    summary = _summarize_graph(graph)
    entry_points = _detect_entry_points(repo_path)

    return ArchitectureAnalysis(
        graph=graph,
        summary=summary,
        entry_points=entry_points,
        internal_modules=sorted(internal_modules),
    )


def _trim_graph_for_rendering(graph: nx.DiGraph, max_nodes: int = 100) -> nx.DiGraph:
    if graph.number_of_nodes() <= max_nodes:
        return graph.copy()

    ranked = sorted(graph.degree, key=lambda item: item[1], reverse=True)
    selected_nodes = {name for name, _degree in ranked[:max_nodes]}
    return graph.subgraph(selected_nodes).copy()


def export_architecture_diagram(
    graph: nx.DiGraph,
    output_dir: Path,
    filename: str = "architecture",
) -> tuple[Path | None, Path | None]:
    """Export architecture diagram in DOT and PNG formats.

    Returns:
        Tuple of (png_path_or_none, dot_path_or_none).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    trimmed = _trim_graph_for_rendering(graph)

    dot_path = output_dir / f"{filename}.dot"
    png_path = output_dir / f"{filename}.png"

    written_dot: Path | None = None
    written_png: Path | None = None

    try:
        from networkx.drawing.nx_pydot import write_dot

        write_dot(trimmed, dot_path)
        written_dot = dot_path
    except Exception:
        written_dot = None

    try:
        from networkx.drawing.nx_pydot import to_pydot

        pydot_graph = to_pydot(trimmed)
        pydot_graph.set_rankdir("LR")
        pydot_graph.write_png(str(png_path))
        if png_path.exists():
            written_png = png_path
    except Exception:
        written_png = None

    return written_png, written_dot
