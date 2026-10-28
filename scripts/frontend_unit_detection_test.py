#!/usr/bin/env python3
"""Checkpoint test for frontend unit coverage: stack detection.

Converted from tests/test_frontend_detection.py (a dead pytest suite that ran
0 tests because pytest is not installed and nothing collected it). Same
behaviors, now executed by the repo's standalone self-runner pattern.

Run through the gate: bin/craft-check -- python3 scripts/frontend_unit_detection_test.py

Standalone (stdlib only, no pytest): builds throwaway project trees in a temp
directory and asserts what the detectors must report. Exit 0 = green.

Dedupe note: malformed-manifest, second-level-scope, and first-level-workspace
checks already live in scripts/frontend_stack_detection_test.py — they are not
repeated here.
"""

import json
import pathlib
import sys
import tempfile
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import craft_stack  # noqa: E402
from frontend.build.detection import detect as detect_build  # noqa: E402
from frontend.stacks.detection import detect as detect_frontend  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail if isinstance(detail, str) and detail else repr(detail)))


def project(root, files):
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
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

        # --- framework + build tool pairing --------------------------------
        react = project(base / "react-app", {
            "package.json": manifest({"react": "19"}),
            "vite.config.ts": "export default {}",
        })
        found = detect_frontend(react)
        check("react detected with vite",
              [(r.framework, r.build_tools) for r in found] == [("react", ("vite",))], found)

        nextjs = project(base / "next-app", {
            "package.json": manifest({"react": "^19.0.0", "next": "^15.0.0"}),
            "next.config.mjs": "export default {}",
        })
        found = detect_frontend(nextjs)
        check("react with next build tool",
              [(r.framework, r.build_tools) for r in found] == [("react", ("next",))], found)

        remix = project(base / "remix-app", {
            "package.json": manifest({"react": "^18.0.0", "@remix-run/node": "^2.0.0"}),
            "remix.config.js": "export default {}",
        })
        found = detect_frontend(remix)
        check("react with remix build tool",
              [(r.framework, r.build_tools) for r in found] == [("react", ("remix",))], found)

        cli = project(base / "cli-app", {
            "package.json": manifest({"vue": "^3.0.0", "@vue/cli-service": "^5.0.0"}),
            "vue.config.js": "export default {}",
        })
        found = detect_frontend(cli)
        check("vue-cli build tool",
              [(r.framework, r.build_tools) for r in found] == [("vue", ("vue-cli",))], found)

        # --- craft_stack pack routing --------------------------------------
        vue_only = project(base / "vue-pack", {"package.json": manifest({"vue": "3"})})
        found = craft_stack.detect(str(vue_only))
        check("vue dependency routes the frontend pack over node",
              [item["id"] for item in found] == ["vue"], found)

        nuxt = project(base / "nuxt-app", {
            "package.json": manifest({"nuxt": "^4.0.0"}),
            "nuxt.config.ts": "export default defineNuxtConfig({})",
        })
        found = craft_stack.detect(str(nuxt))
        check("nuxt pack wins over vue", [item["id"] for item in found] == ["nuxt"], found)

        # --- nuxt specifics -------------------------------------------------
        nuxt_full = project(base / "nuxt-full", {
            "package.json": manifest({"nuxt": "^4.0.0", "vue": "^3.5.0"}),
            "nuxt.config.ts": "export default defineNuxtConfig({})",
        })
        found = detect_frontend(nuxt_full)
        check("nuxt project reports nuxt framework",
              [(r.framework, r.build_tools) for r in found] == [("nuxt", ("nuxt",))], found)

        bare = project(base / "nuxt-bare", {"package.json": manifest({"nuxt": "^4.0.0"})})
        check("nuxt dep detected without vue dep",
              [r.framework for r in detect_frontend(bare)] == ["nuxt"],
              detect_frontend(bare))

        check("build detection reports nuxt config",
              [(r.name, r.config) for r in detect_build(nuxt_full)] == [("nuxt", "nuxt.config.ts")],
              detect_build(nuxt_full))

        check("build detection reports nuxt dependency without config",
              [(r.name, r.config) for r in detect_build(bare)] == [("nuxt", "")],
              detect_build(bare))

        for lens in ("ssr", "data", "hydration", "component", "accessibility"):
            addendum = craft_stack.lens_addendum(lens, "nuxt")
            check("nuxt lens resolves %s section" % lens, len(addendum) > 40, len(addendum))

        # --- skills_for only names skills that exist on disk ----------------
        patched = [{"id": "nuxt", "dir": "", "evidence": "x"}]
        with mock.patch.object(craft_stack, "detect", lambda cwd=None: patched):
            skills = craft_stack.skills_for(cwd=str(nuxt), with_concurrency=False)
        check("skills_for returns the nuxt pack's skills", bool(skills), skills)
        missing = [name for name in skills
                   if not (craft_stack.PLUGIN_ROOT / "skills" / name / "SKILL.md").exists()]
        check("skills_for omits skills without files", not missing, missing)

        # --- angular is no longer a supported frontend stack ---------------
        angular = project(base / "ng-app", {"package.json": manifest({"@angular/core": "^18.0.0"})})
        check("angular is not detected as a frontend stack",
              [r.framework for r in detect_frontend(angular)] == [],
              detect_frontend(angular))


if __name__ == "__main__":
    main()
    if FAILURES:
        print("\nFAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("\nfrontend unit detection: all checks green")
