"""Static bundle and build analysis for JavaScript frontends.

Every analyzer here is read-only and stdlib-only: it inspects source files and
build manifests in the project tree, it never runs a bundler. The craft rules
apply: nothing raises, every public function returns a safe default, and
nothing writes.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .detection import CONFIG_FILES

SKIP_DIRECTORIES = {
    ".git", ".claude", ".hg", ".svn", ".tox", ".venv", "venv", "env", ".env",
    "node_modules", "__pycache__", "site-packages", "build", "dist", "target",
    "vendor", ".gradle", ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".next", ".nuxt", ".output", "coverage", "out", "bin", "obj",
}
SOURCE_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte")
ASSET_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico",
                    ".css", ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".webm")
MAX_SCAN_FILES = 800
MAX_READ_BYTES = 512 * 1024

# Session 1 — thresholds from frontend-technical-spec.md §7.1.
BUNDLE_THRESHOLDS = {
    "bundle_size": {"warning": 500_000, "error": 2_000_000},
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _iter_sources(base: Path, extensions=SOURCE_EXTENSIONS, limit=MAX_SCAN_FILES):
    """Yield (relative_posix, path) for source files under base, skipped dirs pruned."""
    count = 0
    for directory, subdirectories, filenames in os.walk(str(base)):
        subdirectories[:] = [name for name in subdirectories
                             if name not in SKIP_DIRECTORIES and not name.startswith(".")]
        for filename in sorted(filenames):
            if not filename.endswith(tuple(extensions)):
                continue
            count += 1
            if count > limit:
                return
            yield (Path(directory) / filename).relative_to(base).as_posix(), Path(directory) / filename


def _read(path: Path, limit=MAX_READ_BYTES) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Session 1 — bundle analysis (static size inventory)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BundleReport:
    """A static inventory of what will feed the bundle."""

    total_source_bytes: int
    file_count: int
    largest: tuple[tuple[str, int], ...] = ()
    dependency_count: int = 0
    verdict: str = "ok"
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "total_source_bytes": self.total_source_bytes,
            "file_count": self.file_count,
            "largest": list(self.largest),
            "dependency_count": self.dependency_count,
            "verdict": self.verdict,
            "warnings": list(self.warnings),
        }


def _dependency_names(base: Path) -> set[str]:
    try:
        data = json.loads(_read(base / "package.json") or "{}")
    except ValueError:
        return set()
    names: set[str] = set()
    if isinstance(data, dict):
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            values = data.get(section)
            if isinstance(values, dict):
                names.update(str(name) for name in values)
    return names


def analyze_bundle(project: str | Path = ".") -> BundleReport:
    """Inventory source bytes and flag oversized trees against the spec thresholds."""

    base = Path(project).resolve()
    sizes: list[tuple[str, int]] = []
    total = 0
    for relative, path in _iter_sources(base):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        total += size
        sizes.append((relative, size))
    sizes.sort(key=lambda item: -item[1])
    warnings: list[str] = []
    verdict = "ok"
    if total > BUNDLE_THRESHOLDS["bundle_size"]["error"]:
        verdict = "error"
        warnings.append("source tree is %d bytes, over the %d error threshold"
                        % (total, BUNDLE_THRESHOLDS["bundle_size"]["error"]))
    elif total > BUNDLE_THRESHOLDS["bundle_size"]["warning"]:
        verdict = "warning"
        warnings.append("source tree is %d bytes, over the %d warning threshold"
                        % (total, BUNDLE_THRESHOLDS["bundle_size"]["warning"]))
    return BundleReport(total, len(sizes), tuple(sizes[:10]), len(_dependency_names(base)), verdict, tuple(warnings))


# ---------------------------------------------------------------------------
# Session 2 — asset optimization (oversized unoptimized assets)
# ---------------------------------------------------------------------------

# Above these byte sizes an asset almost certainly needs compression or a
# modern format. SVG and fonts are text/vector, so their budget is smaller.
ASSET_BUDGETS = {
    ".png": 200_000, ".jpg": 200_000, ".jpeg": 200_000, ".gif": 200_000,
    ".webp": 150_000, ".avif": 150_000, ".svg": 50_000, ".ico": 50_000,
    ".css": 100_000, ".woff": 100_000, ".woff2": 100_000, ".ttf": 150_000,
    ".otf": 150_000, ".mp4": 2_000_000, ".webm": 2_000_000,
}
MODERN_IMAGE_FORMATS = (".webp", ".avif")


@dataclass(frozen=True)
class AssetIssue:
    path: str
    size: int
    reason: str


def analyze_assets(project: str | Path = ".", min_size=4_000) -> list[AssetIssue]:
    """Report assets over their format budget and images stuck on legacy formats.

    min_size ignores trivial files so generated icon sets do not drown the
    report.
    """

    base = Path(project).resolve()
    issues: list[AssetIssue] = []
    for relative, path in _iter_sources(base, ASSET_EXTENSIONS):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size < min_size:
            continue
        suffix = path.suffix.lower()
        budget = ASSET_BUDGETS.get(suffix)
        if budget is not None and size > budget:
            issues.append(AssetIssue(relative, size, "%s asset is %d bytes, budget is %d" % (suffix, size, budget)))
        elif suffix in (".png", ".jpg", ".jpeg", ".gif") and size > 100_000:
            issues.append(AssetIssue(relative, size,
                                     "%s asset is %d bytes; consider webp or avif" % (suffix, size)))
    issues.sort(key=lambda issue: -issue.size)
    return issues


# ---------------------------------------------------------------------------
# Session 3 — code splitting (lazy loading opportunities)
# ---------------------------------------------------------------------------

LAZY_PATTERNS = {
    "dynamic_import": re.compile(r"""\bimport\s*\(\s*['"][^'"]+['"]"""),
    "react_lazy": re.compile(r"""\bReact\.lazy\s*\(|\blazy\s*\(\s*\(\s*\)\s*=>"""),
    "define_async_component": re.compile(r"""\bdefineAsyncComponent\s*\("""),
    "loadable": re.compile(r"""\bloadable\s*\(|\bimport\s+loadable"""),
}
ROUTE_HINTS = re.compile(r"""/(pages|views|routes|app)/[\w.-]+\.(vue|tsx?|jsx?|svelte)$""", re.IGNORECASE)


@dataclass(frozen=True)
class SplittingReport:
    entry_count: int
    lazy_count: int
    route_pages: int
    unsplit_routes: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "entry_count": self.entry_count,
            "lazy_count": self.lazy_count,
            "route_pages": self.route_pages,
            "unsplit_routes": list(self.unsplit_routes),
            "suggestions": list(self.suggestions),
        }


def analyze_splitting(project: str | Path = ".") -> SplittingReport:
    """Detect lazy-loading usage and route pages that load eagerly."""

    base = Path(project).resolve()
    lazy_count = 0
    routes: list[str] = []
    route_pages = 0
    for relative, path in _iter_sources(base):
        text = _read(path)
        if not text:
            continue
        if any(pattern.search(text) for pattern in LAZY_PATTERNS.values()):
            lazy_count += 1
        if ROUTE_HINTS.search("/" + relative):
            route_pages += 1
            routes.append(relative)
    # Framework routers (nuxt/next file conventions) split per route at build
    # time; flag client-routed trees only.
    has_framework_router = (base / "nuxt.config.ts").is_file() or (base / "nuxt.config.js").is_file() \
        or (base / "next.config.js").is_file() or (base / "next.config.mjs").is_file()
    unsplit = tuple(routes) if not has_framework_router and lazy_count == 0 and route_pages > 3 else ()
    suggestions = []
    if unsplit:
        suggestions.append("route pages load eagerly: add dynamic import() or React.lazy() for below-the-fold pages")
    return SplittingReport(lazy_count, lazy_count, route_pages, unsplit, tuple(suggestions))


# ---------------------------------------------------------------------------
# Session 4 — tree shaking validation (unused dependencies)
# ---------------------------------------------------------------------------

BARE_IMPORT = re.compile(r"""(?:^|\n)\s*import\s+(?:[\w*{},\s]+\s+from\s+)?['"]([^'".][^'"]*)['"]""")
SIDE_EFFECT_REQUIRE = re.compile(r"""\brequire\s*\(\s*['"]([^'".][^'"]*)['"]""")


@dataclass(frozen=True)
class UnusedDependency:
    name: str
    section: str


def analyze_tree_shaking(project: str | Path = ".") -> list[UnusedDependency]:
    """Report manifest dependencies never imported by any scanned source file.

    Scoped packages match on their scope root: @vueuse/core is considered used
    when any source imports from "@vueuse/...".
    """

    base = Path(project).resolve()
    manifest = {}
    try:
        manifest = json.loads(_read(base / "package.json") or "{}")
    except ValueError:
        return []
    if not isinstance(manifest, dict):
        return []

    imported_roots: set[str] = set()
    for _, path in _iter_sources(base):
        text = _read(path, 128 * 1024)
        for match in BARE_IMPORT.finditer(text):
            specifier = match.group(1)
            parts = specifier.split("/")
            imported_roots.add("/".join(parts[:2]) if specifier.startswith("@") else parts[0])
        for match in SIDE_EFFECT_REQUIRE.finditer(text):
            specifier = match.group(1)
            parts = specifier.split("/")
            imported_roots.add("/".join(parts[:2]) if specifier.startswith("@") else parts[0])

    unused: list[UnusedDependency] = []
    for section in ("dependencies", "devDependencies"):
        values = manifest.get(section)
        if not isinstance(values, dict):
            continue
        for name in values:
            root = "/".join(name.split("/")[:2]) if name.startswith("@") else name.split("/")[0]
            if root not in imported_roots:
                unused.append(UnusedDependency(name, section))
    unused.sort(key=lambda item: item.name)
    return unused


# ---------------------------------------------------------------------------
# Session 5 — performance monitoring (static Web Vitals risk audit)
# ---------------------------------------------------------------------------

WEB_VITALS_RISKS = {
    "render_blocking_style": re.compile(r"""<link[^>]+rel=["']stylesheet["'][^>]*>""", re.IGNORECASE),
    "synchronous_script": re.compile(r"""<script\s+(?![^>]*\b(?:async|defer|type=))[^>]*\bsrc=["']""", re.IGNORECASE),
    "layout_shift_risk": re.compile(r"""<img(?![^>]*\b(width|height|aspect-ratio)[=>])[^>]*\bsrc=["']""", re.IGNORECASE),
    "web_vitals_source": re.compile(r"""\bweb-vitals\b|\bgetCLS\b|\bgetLCP\b|\breportWebVitals\b"""),
}
HTML_EXTENSIONS = SOURCE_EXTENSIONS + (".html",)
LCP_BUDGET_MS = 2_500
FCP_BUDGET_MS = 2_000


@dataclass(frozen=True)
class PerformanceReport:
    fcp_budget_ms: int
    lcp_budget_ms: int
    render_blocking: int
    synchronous_scripts: int
    unstyled_images: int
    vitals_instrumented: bool
    findings: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "fcp_budget_ms": self.fcp_budget_ms,
            "lcp_budget_ms": self.lcp_budget_ms,
            "render_blocking": self.render_blocking,
            "synchronous_scripts": self.synchronous_scripts,
            "unstyled_images": self.unstyled_images,
            "vitals_instrumented": self.vitals_instrumented,
            "findings": list(self.findings),
        }


def analyze_performance(project: str | Path = ".") -> PerformanceReport:
    """Audit the tree for static Web Vitals risks against the spec §7.1 budgets."""

    base = Path(project).resolve()
    render_blocking = 0
    synchronous = 0
    unstyled_images = 0
    instrumented = False
    for _, path in _iter_sources(base, HTML_EXTENSIONS):
        text = _read(path, 128 * 1024)
        if not text:
            continue
        if not instrumented and WEB_VITALS_RISKS["web_vitals_source"].search(text):
            instrumented = True
        for pattern_name in ("render_blocking_style", "synchronous_script", "layout_shift_risk"):
            count = len(WEB_VITALS_RISKS[pattern_name].findall(text))
            if pattern_name == "render_blocking_style":
                render_blocking += count
            elif pattern_name == "synchronous_script":
                synchronous += count
            else:
                unstyled_images += count
    findings: list[str] = []
    if synchronous:
        findings.append("%d synchronous <script src> tag(s): add async or defer" % synchronous)
    if unstyled_images:
        findings.append("%d <img> without width/height: reserve space to protect CLS" % unstyled_images)
    if not instrumented:
        findings.append("no web-vitals instrumentation found: add getCLS/getLCP reporting before tuning")
    return PerformanceReport(FCP_BUDGET_MS, LCP_BUDGET_MS, render_blocking, synchronous,
                             unstyled_images, instrumented, tuple(findings))
