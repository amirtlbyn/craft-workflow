"""Detect frontend build tools from configuration files and package scripts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildToolResult:
    name: str
    config: str
    evidence: str


CONFIG_FILES = {
    "vite": ("vite.config.js", "vite.config.ts", "vite.config.mjs", "vite.config.mts"),
    "next": ("next.config.js", "next.config.mjs", "next.config.ts"),
    "webpack": ("webpack.config.js", "webpack.config.ts", "webpack.config.cjs"),
    "turbopack": ("turbopack.config.js", "turbopack.config.ts"),
}


def _package_data(root: Path) -> dict:
    try:
        value = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def detect(project: str | Path = ".") -> list[BuildToolResult]:
    """Return configured build tools in deterministic priority order."""

    root = Path(project).resolve()
    package = _package_data(root)
    dependencies = set()
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        values = package.get(section)
        if isinstance(values, dict):
            dependencies.update(values)
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    results: list[BuildToolResult] = []
    for name, candidates in CONFIG_FILES.items():
        config = next((candidate for candidate in candidates if (root / candidate).is_file()), None)
        package_name = "next" if name == "next" else name
        script_match = any(name in str(command).lower() for command in scripts.values())
        dependency_match = package_name in dependencies
        if config:
            results.append(BuildToolResult(name, config, f"{config} exists"))
        elif dependency_match or script_match:
            reason = f"{package_name} dependency" if dependency_match else "package script references tool"
            results.append(BuildToolResult(name, "", reason))
    return results

