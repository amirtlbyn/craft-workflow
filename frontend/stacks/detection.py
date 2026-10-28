"""Detect JavaScript frontend frameworks from a project directory.

The detector is deliberately dependency-free and conservative: malformed or
missing manifests produce an empty result, and a framework is reported only
when its package is present in dependencies or devDependencies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DetectionResult:
    """A detected frontend framework and its related toolchain evidence."""

    framework: str
    directory: str = ""
    packages: tuple[str, ...] = ()
    build_tools: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


FRAMEWORK_PACKAGES = {
    "react": ("react",),
    "vue": ("vue",),
    "nuxt": ("nuxt", "nuxt-nightly", "@nuxt/framework"),
}

BUILD_TOOL_FILES = {
    "nuxt": ("nuxt.config.js", "nuxt.config.mjs", "nuxt.config.ts", "nuxt.config.mts"),
    "vite": ("vite.config.js", "vite.config.ts", "vite.config.mjs", "vite.config.mts"),
    "next": ("next.config.js", "next.config.mjs", "next.config.ts"),
    "remix": ("remix.config.js", "remix.config.ts"),
    "webpack": ("webpack.config.js", "webpack.config.ts", "webpack.config.cjs"),
    "turbopack": ("turbopack.config.js", "turbopack.config.ts"),
    "vue-cli": ("vue.config.js",),
}


def _manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _packages(data: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        values = data.get(section)
        if isinstance(values, dict):
            result.update(str(name) for name in values)
    return result


def _framework(packages: set[str]) -> tuple[str, tuple[str, ...]] | None:
    matches = [(name, names) for name, names in FRAMEWORK_PACKAGES.items() if any(pkg in packages for pkg in names)]
    if not matches:
        return None
    # Frameworks share packages (vue inside nuxt); resolve hybrids explicitly.
    priority = {"nuxt": 4, "vue": 2, "react": 1}
    return max(matches, key=lambda item: priority[item[0]])


def detect(project: str | Path = ".") -> list[DetectionResult]:
    """Detect frontend frameworks in a root and first-level workspaces."""

    root = Path(project).resolve()
    directories = [root]
    try:
        directories.extend(path for path in root.iterdir() if path.is_dir() and not path.name.startswith("."))
    except OSError:
        return []

    results: list[DetectionResult] = []
    for directory in directories:
        manifest_path = directory / "package.json"
        data = _manifest(manifest_path)
        packages = _packages(data)
        match = _framework(packages)
        if match is None:
            continue
        framework, package_names = match
        tools = tuple(name for name, files in BUILD_TOOL_FILES.items() if any((directory / file).is_file() for file in files))
        evidence = [f"package.json contains {package}" for package in package_names if package in packages]
        evidence.extend(f"{tool} config" for tool in tools)
        relative = "" if directory == root else directory.relative_to(root).as_posix()
        results.append(DetectionResult(framework, relative, tuple(sorted(packages)), tools, tuple(evidence)))
    return results

