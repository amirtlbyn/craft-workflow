#!/usr/bin/env python3
"""PreToolUse on Write|Edit - hold the spec gate shut until the spec is approved.

The workflow is spec-driven. On the task and project routes, the developer
approves spec.md before any source or test file is written. Until now that was
prose. This makes it a rule.

The hook is inert unless all of these hold:

  1. A craft session is recorded at <repo>/.claude/craft/session.json
  2. Its route is task or project
  3. The target path is inside the host repository and outside <repo>/.claude/

Then it denies the write unless approval.json holds an approval whose SHA-256
matches the active spec.md exactly as it is on disk now. A spec that changed
after its approval is `stale`, and the gate is shut again until the developer
approves the change. bin/craft-approve records an approval.

The approval is bound to the spec, not to the Claude session. Work resumes in a
new session, for example after a usage-limit reset, with no second approval.

Fails open. Any exception, any payload it does not recognise, any missing
configuration: the write goes through.

Kill switch: CRAFT_HOOKS=off
"""

import pathlib
import sys

# Claude Code runs this file by path, so its own directory is already on
# sys.path. The line below keeps the import working when a test imports the
# module from somewhere else.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

GATED_ROUTES = ("task", "project")
BIN = craft_state.PLUGIN_ROOT / "bin"

HEADER = """The spec gate is shut. On the %(route)s route, no source or test file is
written until the developer approves the spec.

  blocked path   %(path)s
  spec           %(spec)s
  spec state     %(state)s
"""

NEXT_STEP = {
    "none": """
There is no spec yet. Do this, in order:

  1. Load the `spec` skill, or run /spec. Create the spec:

         "%(bin)s/craft-spec" new --route %(route)s --title "<title>"

  2. Write spec.md. Present the criteria, non-goals, and risk tier. Stop.
  3. After the developer approves, record it. This opens the gate:

         "%(bin)s/craft-approve"
""",
    "not approved": """
The spec exists, and the developer has not approved it. Do this, in order:

  1. Present the criteria table, the non-goals, the risk tier, and the open
     questions of %(path_md)s. Stop and wait for approve, cut, add, or change.
  2. After the developer approves, record it. This opens the gate:

         "%(bin)s/craft-approve"
""",
    "stale": """
spec.md changed after it was approved (approved %(approved)s, now %(current)s).
A changed spec is a spec delta, and it needs the developer's approval:

  1. Show the delta: the rows added, changed, or removed, and why.
  2. After the developer approves, append the delta to log.md and run:

         "%(bin)s/craft-approve"

When the change to spec.md was a mistake, restore the approved text instead.
""",
}

FOOTER = """
Do not write the file somewhere else, and do not rename it to get around this.
Code written before its spec is agreed builds what was typed, not what was wanted.

Writes under .claude/ are always allowed. To turn every craft hook off for one
command, set CRAFT_HOOKS=off."""


def decide(payload):
    """Return ("allow", "") or ("deny", reason). Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("allow", "")
        if not craft_state.is_write_tool(payload):
            return ("allow", "")

        cwd = craft_state.payload_cwd(payload)
        if not craft_state.is_active(cwd):
            # No craft session in this repository. The plugin stays out of the way.
            return ("allow", "")

        route = craft_state.current_route(cwd)
        if route not in GATED_ROUTES:
            return ("allow", "")

        path = craft_state.target_path(payload)
        if not path:
            return ("allow", "")
        if craft_state.is_inside_craft_area(path, cwd):
            return ("allow", "")

        state, detail = craft_state.spec_state(cwd)
        if state == "approved":
            return ("allow", "")

        values = {
            "route": route,
            "path": path,
            "spec": detail.get("spec") or "none active",
            "state": state,
            "bin": str(BIN),
            "path_md": detail.get("path") or "spec.md",
            "approved": (detail.get("approved_sha256") or "")[:12] or "unknown",
            "current": (detail.get("sha256") or "")[:12] or "unknown",
        }
        reason = HEADER % values + NEXT_STEP.get(state, NEXT_STEP["none"]) % values + FOOTER
        return ("deny", reason)
    except Exception:
        return ("allow", "")


if __name__ == "__main__":
    sys.exit(craft_state.run_hook(decide))
