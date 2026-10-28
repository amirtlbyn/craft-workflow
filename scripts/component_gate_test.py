#!/usr/bin/env python3
"""Checkpoint test for CGT-1: component gate implementation.

Run through the gate: bin/craft-check -- python3 scripts/component_gate_test.py

Standalone (stdlib only): exercises the structural rules of
scripts/component_gate.py directly (violations + decide), and asserts the hook
is registered in hooks/hooks.json. Exit 0 = green.
"""

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import component_gate  # noqa: E402

FAILURES = []


def check(name, condition, detail: object = ""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail or "condition false"))


def main():
    # Rule: a component file must define a component.
    ok_component = "export default function Button() { return null; }"
    check("component definition passes", component_gate.violations(ok_component, ".tsx") == [])
    check("empty placeholder denied", "no-component" in component_gate.violations("TODO", ".tsx"))
    check("vue template counts", component_gate.violations("<template><div/></template>", ".vue") == [])
    check("plain ts file exempt", component_gate.violations("export const x = 1;", ".ts") == [])

    # Rule: listener teardown.
    leaky = "export default function X() { window.addEventListener('resize', onResize); return null; }"
    check("listener without teardown denied",
          "listener-teardown" in component_gate.violations(leaky, ".tsx"), component_gate.violations(leaky, ".tsx"))
    clean = leaky.replace("return null;", "return () => window.removeEventListener('resize', onResize);")
    check("teardown present passes",
          "listener-teardown" not in component_gate.violations(clean, ".tsx"))
    angular_clean = ("export class X { constructor() { this.sub = s.subscribe(fn); } "
                     "ngOnDestroy() { this.sub.unsubscribe(); } }")
    check("angular ngOnDestroy accepted",
          "listener-teardown" not in component_gate.violations(angular_clean, ".ts"))
    check("teardown rule only on component files",
          component_gate.violations(leaky, ".ts") == [])

    # Rule: raw hex in inline styles.
    hexy = '<template><div style="color: #ff0000">x</div></template>'
    check("raw hex denied", "raw-hex-style" in component_gate.violations(hexy, ".vue"))
    token = '<template><div :style="{ color: token }">x</div></template>'
    check("token style passes", component_gate.violations(token, ".vue") == [])

    # Hook decision plumbing. The hook is inert without a craft session, so
    # the test writes the session marker craft_state.is_active looks for.
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        (base / "package.json").write_text(json.dumps({"dependencies": {"react": "19"}}))
        craft_dir = base / ".claude" / "craft"
        craft_dir.mkdir(parents=True)
        (craft_dir / "session.json").write_text(json.dumps({"route": "task"}))
        payload = {
            "tool_name": "Write",
            "cwd": str(base),
            "tool_input": {"file_path": str(base / "src" / "Button.tsx"), "content": "TODO"},
        }
        decision, reason = component_gate.decide(payload)
        check("gate denies placeholder component", decision == "deny", reason[:80])
        payload["tool_input"]["content"] = ok_component
        decision, reason = component_gate.decide(payload)
        check("gate allows valid component", decision == "allow", reason[:80])

        # Non-frontend repository stays inert.
        plain = pathlib.Path(tempfile.mkdtemp())
        payload["cwd"] = str(plain)
        payload["tool_input"]["file_path"] = str(plain / "Button.tsx")
        decision, _ = component_gate.decide(payload)
        check("no frontend stack: inert", decision == "allow")

    # Registration: the hook must be wired into hooks.json.
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    commands = []
    for group in hooks.get("hooks", {}).get("PreToolUse", []):
        for hook in group.get("hooks", []):
            commands.append(hook.get("command", ""))
    check("component_gate registered", any("component_gate.py" in command for command in commands))
    check("gate fails open on garbage", component_gate.decide({}) == ("allow", ""))


if __name__ == "__main__":
    main()
    if FAILURES:
        print("\nFAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("\ncomponent gate: all checks green")
