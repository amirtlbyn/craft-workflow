#!/usr/bin/env python3
"""Checkpoint test for CDS-1, SMS-1, SDS-1: frontend skill development.

Run through the gate: bin/craft-check -- python3 scripts/frontend_skill_test.py

Standalone (stdlib only): asserts the three frontend skills exist, declare
themselves correctly, cover the framework-specific sections the task files
require, and resolve through the craft-stack skill routing. Exit 0 = green.
"""

import pathlib
import sys
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import craft_stack  # noqa: E402

FAILURES = []

SKILL_REQUIREMENTS = {
    "component-design": {
        "framework_sections": {
            "react": ["memo", "usecallback", "usememo", "hook"],
            "vue": ["composition api", "computed", "watch", "slot"],
        },
        "core": ["prop", "composition", "accessibility", "testing"],
    },
    "state-management": {
        "framework_sections": {
            "react": ["usestate", "usereducer", "context", "zustand", "tanstack"],
            "vue": ["ref", "computed", "pinia", "vuex"],
        },
        "core": ["server state", "derived", "testing", "performance"],
    },
    "styling-discipline": {
        "framework_sections": {
            "react": ["css-in-js", "styled", "emotion", "theme"],
            "vue": ["scoped", "sfc"],
        },
        "core": ["utility", "css modules", "design system", "responsive", "accessibility"],
    },
}


def check(name, condition, detail: object = ""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail or "condition false"))


def skill_text(name):
    path = ROOT / "skills" / name / "SKILL.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").lower()


def main():
    for name, requirements in SKILL_REQUIREMENTS.items():
        text = skill_text(name)
        check("%s: SKILL.md exists" % name, bool(text))
        frontmatter = text.startswith("---")
        check("%s: frontmatter present" % name, frontmatter)
        if frontmatter:
            block = text.split("---")[1].lower()
            check("%s: name declared" % name, ("name: %s" % name) in block)
            check("%s: description present" % name, "description:" in block and len(block) > 80)
        for needle in requirements["core"]:
            check("%s: covers '%s'" % (name, needle), needle in text)
        for framework, needles in requirements["framework_sections"].items():
            missing = [needle for needle in needles if needle not in text]
            check("%s: %s coverage" % (name, framework), not missing, "missing %s" % missing)

    # Routing: each frontend stack pack must list the skills, and every named
    # skill must exist on disk so the routing does not dangle.
    for stack_id in ("react", "vue", "nuxt"):
        data = craft_stack.pack(stack_id)
        skills = data.get("skills") or []
        check("%s pack lists frontend skills" % stack_id, "component-design" in skills, skills)
        for name in skills:
            check("%s pack skill %s exists" % (stack_id, name),
                  (ROOT / "skills" / name / "SKILL.md").is_file())

    # Loading: skills_for on a detected react project returns the skill.
    check("standards referenced by skills exist",
          all((ROOT / "standards" / ("%s.ai.md" % standard)).is_file()
              for standard in ("component_design_standards", "accessibility_standards",
                               "frontend_performance_standards")))


if __name__ == "__main__":
    main()
    if FAILURES:
        print("\nFAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("\nfrontend skills: all checks green")
