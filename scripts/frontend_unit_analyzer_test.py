#!/usr/bin/env python3
"""Checkpoint test for frontend unit coverage: the bundle analyzer.

Converted from tests/test_frontend_build_analyzer.py (a dead pytest suite that
ran 0 tests because pytest is not installed and nothing collected it). Same
behaviors, now executed by the repo's standalone self-runner pattern. The
working-tree entry_count expectation (an entry per source file, plus the lazy
import) is preserved.

Run through the gate: bin/craft-check -- python3 scripts/frontend_unit_analyzer_test.py

Standalone (stdlib only, no pytest): builds throwaway project trees in a temp
directory and asserts what the analyzers must report. Exit 0 = green.
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
from frontend.build.detection import detect as detect_build  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        message = detail if isinstance(detail, str) and detail else repr(detail)
        print("FAIL  %s %s" % (name, message))


def project(root, files):
    root.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return root


def manifest(dependencies=None, dev_dependencies=None):
    data = {}
    if dependencies:
        data["dependencies"] = dependencies
    if dev_dependencies:
        data["devDependencies"] = dev_dependencies
    return json.dumps(data)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)

        # --- build-tool detection ------------------------------------------
        webpack = project(base / "wp-app", {"package.json": manifest(dev_dependencies={"webpack": "5"})})
        check("build detection uses config and package evidence",
              [(r.name, r.config) for r in detect_build(webpack)] == [("webpack", "")],
              detect_build(webpack))

        # --- bundle ---------------------------------------------------------
        bundle = project(base / "bundle-app", {
            "package.json": manifest({"react": "19"}, {"vite": "6"}),
            "src/index.js": "console.log('hi');\n" * 10,
        })
        report = analyze_bundle(bundle)
        check("bundle report counts files and dependencies",
              (report.file_count, report.total_source_bytes > 0, report.dependency_count, report.verdict)
              == (1, True, 2, "ok"),
              report)

        blob = project(base / "blob-app", {"src/blob.js": "x = 1;\n" * 200_000})
        blob_report = analyze_bundle(blob)
        check("bundle report flags oversized tree",
              blob_report.verdict in ("warning", "error"), blob_report.verdict)

        # --- assets ----------------------------------------------------------
        assets = project(base / "assets-app", {
            "public/hero.png": b"\x89PNG" + b"0" * 300_000,
            "public/icon.svg": b"<svg></svg>",
        })
        asset_report = analyze_assets(assets)
        check("assets over budget are flagged",
              [issue.path for issue in asset_report] == ["public/hero.png"],
              asset_report)

        # --- code splitting ----------------------------------------------------
        lazy = project(base / "lazy-app", {
            "package.json": manifest({"react": "19"}),
            "src/App.tsx": "const Page = React.lazy(() => import('./Page'));\n",
            "src/Page.tsx": "export default () => null;\n",
        })
        lazy_report = analyze_splitting(lazy)
        check("splitting detects lazy loading",
              (lazy_report.entry_count, lazy_report.lazy_count) == (2, 1),
              lazy_report)

        eager = project(base / "eager-app", {
            "src/pages/one.ts": "export default 1;\n",
            "src/pages/two.ts": "export default 2;\n",
            "src/pages/three.ts": "export default 3;\n",
            "src/pages/four.ts": "export default 4;\n",
        })
        eager_report = analyze_splitting(eager)
        check("splitting suggests splitting for eager routes",
              eager_report.unsplit_routes != (), eager_report.unsplit_routes)

        router = project(base / "router-app", {
            "nuxt.config.ts": "export default defineNuxtConfig({});",
            "pages/a.vue": "<template><div/></template>",
            "pages/b.vue": "<template><div/></template>",
            "pages/c.vue": "<template><div/></template>",
            "pages/d.vue": "<template><div/></template>",
        })
        router_report = analyze_splitting(router)
        check("splitting does not flag framework routers",
              router_report.unsplit_routes == (), router_report.unsplit_routes)

        # --- tree shaking -------------------------------------------------------
        unused = project(base / "unused-app", {
            "package.json": manifest({"lodash": "4", "dayjs": "1"}, {"eslint": "9"}),
            "src/index.js": "import dayjs from 'dayjs';\nrequire('eslint');\n",
        })
        unused_report = analyze_tree_shaking(unused)
        check("tree shaking finds the unused dependency",
              [item.name for item in unused_report] == ["lodash"],
              unused_report)

        scoped = project(base / "scoped-app", {
            "package.json": manifest({"@vueuse/core": "11", "vue": "3"}),
            "src/index.js": "import { useStorage } from '@vueuse/core';\nimport { createApp } from 'vue';\n",
        })
        scoped_report = analyze_tree_shaking(scoped)
        check("tree shaking handles scoped packages", scoped_report == [],
              scoped_report)

        # --- performance ----------------------------------------------------------
        perf = project(base / "perf-app", {
            "app.html": '<html><head><link rel="stylesheet" href="a.css"></head>'
                        '<body><script src="app.js"></script><img src="hero.png"></body></html>',
            "src/vitals.js": "import { getCLS, getLCP } from 'web-vitals';\n",
        })
        report = analyze_performance(perf)
        check("performance counts static risks",
              (report.render_blocking, report.synchronous_scripts, report.unstyled_images,
               report.vitals_instrumented) == (1, 1, 1, True),
              report)

        bare = project(base / "bare-app", {"index.html": "<p>hi</p>"})
        report = analyze_performance(bare)
        check("performance reports missing vitals",
              report.vitals_instrumented is False and any("web-vitals" in f for f in report.findings),
              report.findings)


if __name__ == "__main__":
    main()
    if FAILURES:
        print("\nFAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("\nfrontend unit analyzer: all checks green")
