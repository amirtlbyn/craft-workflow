#!/usr/bin/env python3
"""Checkpoint test for CSI-1: craft-stack integration with frontend stacks.

Run through the gate: bin/craft-check -- python3 scripts/craft_stack_integration_test.py

Standalone (stdlib only): verifies detect/skills/checks/lens/for/globs all
work for frontend stacks, that mixed fullstack projects keep both stacks, and
that existing backend detection is unchanged. Exit 0 = green.
"""

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import craft_stack  # noqa: E402

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
        path.write_text(content, encoding="utf-8")
    return root


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)

        # Session 1 — detection and priority.
        react = project(base / "react-app", {"package.json": json.dumps({"dependencies": {"react": "19"}})})
        found = craft_stack.detect(str(react))
        check("react detected by craft-stack", [item["id"] for item in found] == ["react"], found)

        fullstack = project(base / "fullstack", {
            "manage.py": "#!/usr/bin/env python",
            "requirements.txt": "django==5\n",
            "web/package.json": json.dumps({"dependencies": {"react": "19"}}),
        })
        found = craft_stack.detect(str(fullstack))
        ids = sorted(item["id"] for item in found)
        check("mixed stack: django + react", ids == ["django", "react"], found)
        owner = craft_stack.owner_of("web/src/App.tsx", str(fullstack), found)
        check("web path owned by react", owner and owner["id"] == "react", owner)
        owner = craft_stack.owner_of("app/models.py", str(fullstack), found)
        check("backend path owned by django", owner and owner["id"] == "django", owner)

        # Session 2 — skills routing.
        skills = craft_stack.skills_for(cwd=str(react))
        check("react skills routed", "component-design" in skills, skills)

        # Session 3 — checks resolution reads the pack.
        checks = craft_stack.checks_for("react", cwd=str(react))
        check("react checks resolve", "tests" in checks, checks)

        # Session 4 — lens addenda.
        addendum = craft_stack.lens_addendum("component", "react")
        check("react component lens resolves", len(addendum) > 40)

        # Session 5 — backward compatibility.
        django = project(base / "django-app", {
            "manage.py": "#!/usr/bin/env python",
            "requirements.txt": "django==5\n",
        })
        found = craft_stack.detect(str(django))
        check("django detection unchanged", [item["id"] for item in found] == ["django"], found)
        check("django is primary", craft_stack.primary(str(django)) == "django")
        skills = craft_stack.skills_for(cwd=str(django))
        check("django skills unchanged", "django-practices" in skills and "component-design" not in skills, skills)
        go = project(base / "go-app", {"go.mod": "module example.com/x\n"})
        check("go detection unchanged", [item["id"] for item in craft_stack.detect(str(go))] == ["go"])

        # globs merge both stacks in a mixed repo.
        globs = craft_stack.globs_for("views", cwd=str(fullstack))
        check("views globs include frontend patterns",
              any("*.tsx" in glob or "components" in glob for glob in globs), globs)

        # Every shipped pack's named skills exist (no dangling routing).
        dangling = []
        for stack_id, data in craft_stack.load_packs().items():
            for name in data.get("skills") or []:
                if not (ROOT / "skills" / name / "SKILL.md").is_file():
                    dangling.append("%s -> %s" % (stack_id, name))
        check("no dangling skill routing", not dangling, dangling)

        # FRONTEND_STACKS are routed in config/workflow.md (doc regression).
        workflow = (ROOT / "config" / "workflow.md").read_text(encoding="utf-8")
        workflow_lines = workflow.splitlines()
        FRONTEND_STACKS = ("react", "vue", "nuxt", "angular")

        def row_of(marker, source=workflow_lines):
            return next((line for line in source if marker in line), "")

        stack_table = workflow_lines[workflow_lines.index("## 9. Stacks — one workflow, any backend language"):]
        for stack_id in FRONTEND_STACKS:
            pack = craft_stack.load_packs()[stack_id]
            names = pack.get("skills") or []

            # §9 stack-table row: emoji id, detection evidence, every pack skill.
            table_row = row_of("`%s` |" % stack_id, stack_table)
            check("workflow stack table routes %s" % stack_id, bool(table_row), "no row")
            check("workflow stack table lists every %s skill" % stack_id,
                  table_row and all("`%s`" % name in table_row for name in names),
                  (table_row, names))

            # Skill-map row (the craft routing map): trigger text routes each skill.
            # The nuxt map row routes to `nuxt-ssr-data` in place of styling-discipline.
            if stack_id == "nuxt":
                map_row = row_of("Nuxt code:")
                expected_skills = ("nuxt-ssr-data", "component-design", "state-management")
            else:
                map_row = row_of("%s component code" % pack.get("label", stack_id).title())
                expected_skills = tuple(names)
            check("workflow skill map routes %s" % stack_id, bool(map_row), "no row")
            check("workflow skill map for %s names every pack skill" % stack_id,
                  map_row and all("`%s`" % name in map_row for name in expected_skills),
                  (map_row, expected_skills))

            # Every skill named in those workflow rows exists on disk.
            missing = [name for name in names
                       if not (ROOT / "skills" / name / "SKILL.md").is_file()]
            check("workflow %s skills exist on disk" % stack_id, not missing, missing)


if __name__ == "__main__":
    main()
    if FAILURES:
        print("\nFAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("\ncraft-stack integration: all checks green")
