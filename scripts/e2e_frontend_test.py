#!/usr/bin/env python3
"""End-to-end test framework for the frontend rewrite (ETF-1).

Run through the gate: bin/craft-check -- python3 scripts/e2e_frontend_test.py
Standalone: python3 scripts/e2e_frontend_test.py

Generates throwaway sample projects per frontend framework in a temp
directory, then drives every layer of the rewrite against them the way a real
session would:

  1. sample project generation (react, vue, nuxt, mixed fullstack)
  2. stack detection through scripts/craft_stack.py (pack routing)
  3. build analysis (frontend/build/analyzer.py)
  4. skill routing (skills_for)
  5. review lens resolution (lens_addendum)
  6. the component gate (structural rules)

Exit 0 = every scenario green.
"""

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import craft_stack  # noqa: E402
from frontend.build.analyzer import (  # noqa: E402
    analyze_assets,
    analyze_bundle,
    analyze_performance,
    analyze_splitting,
    analyze_tree_shaking,
)

FAILURES = []
FRONTEND_STACKS = ("react", "vue", "nuxt")


def check(name, condition, detail: object = ""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail or "condition false"))


# ---------------------------------------------------------------------------
# Sample project templates
# ---------------------------------------------------------------------------

REACT_APP = {
    "package.json": json.dumps({
        "name": "sample-react",
        "scripts": {"test": "vitest run", "lint": "eslint ."},
        "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0"},
        "devDependencies": {"vite": "^6.0.0", "vitest": "^2.0.0", "eslint": "^9.0.0"},
    }),
    "vite.config.ts": "export default {}",
    "src/main.tsx": "import { createRoot } from 'react-dom/client';\nimport App from './App';\n\ncreateRoot(document.getElementById('root')!).render(<App />);\n",
    "src/App.tsx": "import { useState } from 'react';\n\nexport default function App() { const [open] = useState(false); return <main>hi</main>; }\n",
    "src/components/Button.tsx": (
        "export default function Button({ label }: { label: string }) {\n"
        "  return <button type=\"button\">{label}</button>;\n"
        "}\n"
    ),
    "src/components/Button.test.tsx": "import { test } from 'vitest';\ntest('RT-1: renders', () => {});\n",
}

VUE_APP = {
    "package.json": json.dumps({
        "name": "sample-vue",
        "dependencies": {"vue": "^3.5.0"},
        "devDependencies": {"vite": "^6.0.0", "vitest": "^2.0.0", "@vitejs/plugin-vue": "^5.0.0"},
    }),
    "vite.config.ts": "import vue from '@vitejs/plugin-vue';\nexport default {}",
    "src/App.vue": "<template><main>hi</main></template>\n",
    "src/components/BaseButton.vue": (
        "<template><button type=\"button\"><slot /></button></template>\n"
        "<script setup lang=\"ts\">defineProps<{ label?: string }>();</script>\n"
    ),
}

NUXT_APP = {
    "package.json": json.dumps({"name": "sample-nuxt", "dependencies": {"nuxt": "^4.0.0"}}),
    "nuxt.config.ts": "export default defineNuxtConfig({});",
    "app/app.vue": "<template><NuxtPage /></template>",
    "app/pages/index.vue": "<template><main>hi</main></template>",
}

MIXED_APP = {
    "manage.py": "#!/usr/bin/env python",
    "requirements.txt": "django==5\n",
    "web/package.json": json.dumps({"dependencies": {"react": "^19.0.0"}}),
    "web/src/index.tsx": "import { createRoot } from 'react-dom/client';\n",
}


def write_project(base: pathlib.Path, name: str, files: dict) -> pathlib.Path:
    root = base / name
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)

        # Session 1 — generation
        projects = {
            "react": write_project(base, "react-app", REACT_APP),
            "vue": write_project(base, "vue-app", VUE_APP),
            "nuxt": write_project(base, "nuxt-app", NUXT_APP),
            "mixed": write_project(base, "mixed-app", MIXED_APP),
        }
        for name, root in projects.items():
            check("generated %s sample" % name, (root / "package.json").is_file() or (root / "manage.py").is_file())

        # Session 2 — stack detection end to end
        expected = {"react": ["react"], "vue": ["vue"], "nuxt": ["nuxt"]}
        for name, stack_ids in expected.items():
            found = [item["id"] for item in craft_stack.detect(str(projects[name]))]
            check("%s sample detects %s" % (name, stack_ids), found == stack_ids, found)
        mixed = [item["id"] for item in craft_stack.detect(str(projects["mixed"]))]
        check("mixed sample detects django + react", sorted(mixed) == ["django", "react"], mixed)

        # Session 3 — build analysis over the react sample
        react = projects["react"]
        bundle = analyze_bundle(react)
        check("bundle inventory sees sources", bundle.file_count >= 4 and bundle.verdict == "ok", bundle)
        splitting = analyze_splitting(react)
        check("splitting report produced", splitting.route_pages >= 0)
        unused = [u.name for u in analyze_tree_shaking(react)]
        check("tree shaking flags declared-but-never-imported deps",
              set(unused) == {"vite", "eslint"}, unused)
        perf = analyze_performance(react)
        check("performance report produced", perf.fcp_budget_ms == 2000 and perf.lcp_budget_ms == 2500)
        check("asset scan quiet on clean sample", analyze_assets(react) == [])

        # Session 4 — skill routing
        skills = craft_stack.skills_for(cwd=str(react))
        check("react routes the three skills",
              all(name in skills for name in ("component-design", "state-management", "styling-discipline")), skills)
        for name, stack_id in (("react", "react"), ("nuxt", "nuxt")):
            for skill in craft_stack.pack(stack_id).get("skills") or []:
                check("%s sample: %s skill exists" % (name, skill),
                      (ROOT / "skills" / skill / "SKILL.md").is_file())

        # Session 5 — lens resolution
        for stack_id in FRONTEND_STACKS:
            for lens in ("component", "accessibility"):
                addendum = craft_stack.lens_addendum(lens, stack_id)
                check("%s resolves %s lens" % (stack_id, lens), len(addendum) > 40)

        # Session 6 — component gate rules against real sample content
        sys.path.insert(0, str(ROOT / "scripts"))
        import component_gate

        good_button = (ROOT and pathlib.Path(react / "src/components/Button.tsx")).read_text(encoding="utf-8")
        check("gate passes the sample Button", component_gate.violations(good_button, ".tsx") == [])
        leaky = good_button.replace(
            "return <button",
            "window.addEventListener('resize', () => 0);\n  return <button")
        check("gate flags listener leak injected into sample",
              "listener-teardown" in component_gate.violations(leaky, ".tsx"))

        # Detection failure paths stay safe. A malformed or dependency-free
        # package.json falls back to the generic node pack by design (pack
        # layer: any package.json is at least node); it must never report a
        # specific frontend stack on broken input.
        empty = base / "empty"
        empty.mkdir()
        check("empty project detects nothing", craft_stack.detect(str(empty)) == [])
        broken = base / "broken"
        broken.mkdir()
        (broken / "package.json").write_text("{not json")
        found = [item["id"] for item in craft_stack.detect(str(broken))]
        check("broken manifest never claims a frontend stack",
              found == ["node"] and not any(sid in FRONTEND_STACKS for sid in found), found)


if __name__ == "__main__":
    main()
    if FAILURES:
        print("\nFAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("\ne2e frontend framework: all checks green")
