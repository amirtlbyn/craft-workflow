#!/usr/bin/env python3
"""Checkpoint test for BTI-1: build tool integration.

Run through the gate: bin/craft-check -- python3 scripts/build_tool_integration_test.py

Standalone (stdlib only): builds throwaway frontend trees and asserts what the
static analyzers in frontend/build/analyzer.py must report. Exit 0 = green.
"""

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from frontend.build.analyzer import (  # noqa: E402
    analyze_assets,
    analyze_bundle,
    analyze_performance,
    analyze_splitting,
    analyze_tree_shaking,
)

FAILURES = []


def check(name, condition, detail: object = ""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail or "condition false"))


def project(root, files):
    root.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_bytes(content)
    return root


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)

        # Session 1 — bundle analysis
        app = project(base / "app", {
            "package.json": json.dumps({"dependencies": {"react": "19"}, "devDependencies": {"vite": "6"}}),
            "src/index.js": "console.log('hi');\n" * 50,
        })
        report = analyze_bundle(app)
        check("bundle inventory counts files", report.file_count == 1 and report.total_source_bytes > 0, report)
        check("bundle counts dependencies", report.dependency_count == 2)
        check("bundle verdict ok when small", report.verdict == "ok", report.warnings)

        huge = project(base / "huge", {"src/blob.js": "x = 1;\n" * 200_000})
        check("oversized tree warns", analyze_bundle(huge).verdict in ("warning", "error"))

        # Session 2 — asset optimization
        assets = project(base / "assets-app", {
            "public/hero.png": b"\x89PNG" + b"0" * 300_000,
            "public/icon.svg": b"<svg></svg>",
            "public/tiny.png": b"\x89PNG" + b"0" * 1_000,
        })
        issues = analyze_assets(assets)
        check("oversized png flagged", [i.path for i in issues] == ["public/hero.png"], issues)

        # Session 3 — code splitting
        lazy_app = project(base / "lazy", {
            "package.json": json.dumps({"dependencies": {"react": "19"}}),
            "src/App.tsx": "const Page = React.lazy(() => import('./Page'));\n",
            "src/Page.tsx": "export default () => null;\n",
        })
        report = analyze_splitting(lazy_app)
        check("lazy loading detected", report.lazy_count == 1, report)

        eager = project(base / "eager", {
            "src/pages/one.ts": "export default 1;\n",
            "src/pages/two.ts": "export default 2;\n",
            "src/pages/three.ts": "export default 3;\n",
            "src/pages/four.ts": "export default 4;\n",
        })
        report = analyze_splitting(eager)
        check("eager routes suggested for splitting", report.unsplit_routes != (), report)

        nuxt_app = project(base / "nuxt-split", {
            "nuxt.config.ts": "export default defineNuxtConfig({});",
            "pages/a.vue": "<template/><script setup>const x = import('x').then(()=>0)</script>",
        })
        report = analyze_splitting(nuxt_app)
        check("framework router not flagged", report.unsplit_routes == (), report)

        # Session 4 — tree shaking
        shaken = project(base / "shaken", {
            "package.json": json.dumps({"dependencies": {"lodash": "4", "dayjs": "1"}, "devDependencies": {"eslint": "9"}}),
            "src/index.js": "import dayjs from 'dayjs';\nrequire('eslint');\n",
        })
        unused = analyze_tree_shaking(shaken)
        check("unused dependency found", [d.name for d in unused] == ["lodash"], unused)
        check("used deps not flagged", "dayjs" not in [d.name for d in unused])

        scoped = project(base / "scoped", {
            "package.json": json.dumps({"dependencies": {"@vueuse/core": "11", "vue": "3"}}),
            "src/index.js": "import { useStorage } from '@vueuse/core';\nimport { createApp } from 'vue';\n",
        })
        check("scoped imports handled", analyze_tree_shaking(scoped) == [])

        # Session 5 — performance monitoring
        perf = project(base / "perf", {
            "app.html": '<html><head><link rel="stylesheet" href="a.css"></head>'
                        '<body><script src="app.js"></script>'
                        '<img src="hero.png"></body></html>',
            "src/vitals.js": "import { getCLS, getLCP } from 'web-vitals';\n",
        })
        report = analyze_performance(perf)
        check("render blocking counted", report.render_blocking == 1, report)
        check("synchronous script counted", report.synchronous_scripts == 1, report)
        check("unstyled image counted", report.unstyled_images == 1, report)
        check("vitals instrumentation seen", report.vitals_instrumented is True, report)

        bare = analyze_performance(project(base / "bare", {"index.html": "<p>hi</p>"}))
        check("missing vitals reported", bare.vitals_instrumented is False and any("web-vitals" in f for f in bare.findings))


if __name__ == "__main__":
    main()
    if FAILURES:
        print("\nFAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("\nbuild tool integration: all checks green")
