#!/usr/bin/env python3
"""Checkpoint test for FSD-1: frontend stack detection.

Run through the gate: bin/craft-check -- python3 scripts/frontend_stack_detection_test.py

Standalone (stdlib only, no pytest): builds throwaway project trees in a temp
directory and asserts what the detectors must report. Exit 0 = green.
"""

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from frontend.build.detection import detect as detect_build  # noqa: E402
from frontend.stacks.detection import detect as detect_frontend  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
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

        # Session 1 — React
        react = project(base / "react-app", {
            "package.json": manifest({"react": "19", "react-dom": "19"}),
            "vite.config.ts": "export default {}",
        })
        found = detect_frontend(react)
        check("react detected with vite", [(r.framework, r.build_tools) for r in found] == [("react", ("vite",))], found)

        nextjs = project(base / "next-app", {
            "package.json": manifest({"react": "19", "next": "15"}),
            "next.config.mjs": "export default {}",
        })
        found = detect_frontend(nextjs)
        check("react with next config", [(r.framework, r.build_tools) for r in found] == [("react", ("next",))], found)

        remix = project(base / "remix-app", {
            "package.json": manifest({"react": "18", "@remix-run/node": "2"}),
            "remix.config.js": "export default {}",
        })
        found = detect_frontend(remix)
        check("react with remix config", [(r.framework, r.build_tools) for r in found] == [("react", ("remix",))], found)

        # Session 2 — Vue
        vue = project(base / "vue-app", {
            "package.json": manifest({"vue": "3"}),
            "vite.config.js": "export default {}",
        })
        found = detect_frontend(vue)
        check("vue detected", [r.framework for r in found] == ["vue"], found)

        nuxt = project(base / "nuxt-app", {
            "package.json": manifest({"nuxt": "^4.0.0"}),
            "nuxt.config.ts": "export default defineNuxtConfig({})",
        })
        found = detect_frontend(nuxt)
        check("nuxt wins over vue", [(r.framework, r.build_tools) for r in found] == [("nuxt", ("nuxt",))], found)

        cli = project(base / "cli-app", {
            "package.json": manifest({"vue": "3", "@vue/cli-service": "5"}),
            "vue.config.js": "export default {}",
        })
        found = detect_frontend(cli)
        check("vue-cli build tool", [(r.framework, r.build_tools) for r in found] == [("vue", ("vue-cli",))], found)

        # Session 3 — build tools + edge cases
        webpack = project(base / "wp-app", {
            "package.json": manifest(dev_dependencies={"webpack": "5"}),
            "webpack.config.cjs": "module.exports = {};",
        })
        found = detect_build(webpack)
        check("webpack config detection", [(r.name, r.config) for r in found] == [("webpack", "webpack.config.cjs")], found)

        empty = base / "empty"
        empty.mkdir()
        check("empty project -> no detections", detect_frontend(empty) == [] and detect_build(empty) == [])

        broken = project(base / "broken", {"package.json": "{"})
        check("malformed manifest is safe", detect_frontend(broken) == [])

        workspace = project(base / "monorepo", {
            "web/package.json": manifest({"vue": "3"}),
            "api/package.json": manifest({"react": "19"}),
        })
        frameworks = sorted(r.framework for r in detect_frontend(workspace))
        check("workspace directories detected", frameworks == ["react", "vue"], frameworks)

        nested = project(base / "deep-repo", {"a/b/package.json": manifest({"vue": "3"})})
        check("second-level directories out of scope", detect_frontend(nested) == [])


if __name__ == "__main__":
    main()
    if FAILURES:
        print("\nFAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("\nfrontend stack detection: all checks green")
