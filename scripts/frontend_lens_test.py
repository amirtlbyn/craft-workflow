#!/usr/bin/env python3
"""Checkpoint test for CRL-1 and ARL-1: frontend review lenses.

Run through the gate: bin/craft-check -- python3 scripts/frontend_lens_test.py

Standalone (stdlib only): asserts the component and accessibility lens files
exist and carry the checklist sections the task files require, that the
review-protocol routes them, and that every frontend stack pack resolves both
lenses through `bin/craft-stack lens`. Exit 0 = green.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import craft_stack  # noqa: E402

FAILURES = []

COMPONENT_NEEDLES = ["prop", "emit", "hook", "computed",
                     "memo", "loading", "teardown", "error bound"]
ACCESSIBILITY_NEEDLES = ["keyboard", "aria", "focus", "contrast", "label",
                         "live", "reduced", "dialog", "alt", "semantic"]


def check(name, condition, detail: object = ""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail or "condition false"))


def lens_text(name):
    path = ROOT / "skills" / "review-protocol" / "lenses" / ("%s.md" % name)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").lower()


def main():
    component = lens_text("component")
    accessibility = lens_text("accessibility")

    check("component.md exists", bool(component))
    check("accessibility.md exists", bool(accessibility))
    check("component lens has checklist", "## checklist" in component)
    check("accessibility lens has checklist", "## checklist" in accessibility)
    check("component lens has stack notes", "## stack notes" in component)
    check("accessibility lens has stack notes", "## stack notes" in accessibility)

    missing = [needle for needle in COMPONENT_NEEDLES if needle not in component]
    check("component lens coverage", not missing, "missing %s" % missing)
    missing = [needle for needle in ACCESSIBILITY_NEEDLES if needle not in accessibility]
    check("accessibility lens coverage", not missing, "missing %s" % missing)

    # Severity ceilings and confidence thresholds per the task spec.
    check("component ceiling high / confidence 0.7",
          "high" in component and "0.7" in component)
    check("accessibility ceiling critical / confidence 0.8",
          "critical" in accessibility and "0.8" in accessibility)

    # The review protocol must route both lenses.
    protocol = (ROOT / "skills" / "review-protocol" / "SKILL.md").read_text(encoding="utf-8").lower()
    check("protocol routes component lens", "| `component` |" in protocol)
    check("protocol routes accessibility lens", "| `accessibility` |" in protocol)

    # Every frontend stack resolves both lenses with real content.
    for stack_id in ("react", "vue", "nuxt"):
        for lens in ("component", "accessibility"):
            addendum = craft_stack.lens_addendum(lens, stack_id)
            check("%s resolves %s lens" % (stack_id, lens), len(addendum) > 40, addendum[:60])


if __name__ == "__main__":
    main()
    if FAILURES:
        print("\nFAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("\nfrontend review lenses: all checks green")
