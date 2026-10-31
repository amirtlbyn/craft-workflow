#!/usr/bin/env python3
"""PreToolUse on Write|Edit|Bash - hold the spec gate shut until the spec is approved.

The workflow is spec-driven. On the task and project routes, the developer
approves spec.md before any source or test file is written. Until now that was
prose. This makes it a rule.

The hook is inert unless all of these hold:

  1. A craft session is recorded at <repo>/.claude/craft/session.json
  2. Its route is task or project
  3. The target path is inside the host repository and outside <repo>/.claude/.
     For Bash, the targets are the paths of the write forms that
     craft_state.bash_effects() finds in the command text.

Then it denies the write unless approval.json holds an approval whose SHA-256
matches the active spec.md exactly as it is on disk now. A spec that changed
after its approval is `stale`, and the gate is shut again until the developer
approves the change. The developer records an approval with bin/craft-approve.

Every allowed Bash call in a craft session first stores a snapshot in
.claude/craft/snapshots/<tool use id>.json: approval.json on every route, and,
while the gate is shut, the changed files of the repository, each with a
backup in .claude/craft/backups/. gate_bash_after.py compares after the call.

A file that such a call changed while the gate was shut may be written again
only to restore it: `git checkout --` or `git restore` (from the index or
HEAD) for a file that was clean, `rm` for a file that was absent, `cp <its
backup>` for a tracked file that held uncommitted work, or a Write whose
content is the content before the call.

The approval is bound to the spec, not to the Claude session. Work resumes in a
new session, for example after a usage-limit reset, with no second approval.

Fails open. Any exception, any payload it does not recognise, any missing
configuration: the write goes through. One decision is not an error path: a
Bash command whose text cannot be read is denied while the gate is shut, when
it holds a redirection or a command that can write a file.

Kill switch: CRAFT_HOOKS=off
"""

import os
import pathlib
import re
import sys

# Claude Code runs this file by path, so its own directory is already on
# sys.path. The line below keeps the import working when a test imports the
# module from somewhere else.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

GATED_ROUTES = ("task", "project")
BIN = craft_state.PLUGIN_ROOT / "bin"
WRITE_HINT = re.compile(
    r">|\b(?:tee|sed|perl|cp|mv|rm|touch|truncate|ln|install|dd|patch|git|python[\d.]*|node|ruby|sh|bash|eval|xargs|find)\b"
)

UNREADABLE = """The spec gate is shut, and the text of this Bash command cannot be read (an
open quote, for example). It holds a redirection or a command that can write a
file, so it is denied. Write it again with balanced quotes."""

RESTORE_HINT = """
A Bash call changed this file while the gate was shut. A write to it is allowed
only when it restores the content before that call. Edit is not allowed. Run:

    %(command)s
"""

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
  3. Ask the developer to approve it: to type this line in the prompt, or
     press `a` on the board. This opens the gate:

         ! "%(bin)s/craft-approve"

     Do not run it yourself. Only the developer approves.
""",
    "not approved": """
The spec exists, and the developer has not approved it. Do this, in order:

  1. Present the criteria table, the non-goals, the risk tier, and the open
     questions of %(path_md)s. Stop and wait for approve, cut, add, or change.
  2. After the developer approves, ask the developer to record it: to type this
     line in the prompt, or press `a` on the board. This opens the gate:

         ! "%(bin)s/craft-approve"

     Do not run it yourself. Only the developer approves.
""",
    "stale": """
spec.md changed after it was approved (approved %(approved)s, now %(current)s).
A changed spec is a spec delta, and it needs the developer's approval:

  1. Show the delta: the rows added, changed, or removed, and why.
  2. After the developer approves, append the delta to log.md. Then ask the
     developer to type this line in the prompt, or press `a` on the board:

         ! "%(bin)s/craft-approve"

     Do not run it yourself. Only the developer approves.

When the change to spec.md was a mistake, restore the approved text instead.
""",
}

SCENARIOS_HEADER = """The scenarios gate is shut. On the %(route)s route, no test file is written
until the developer approves the test scenarios.

  blocked path      %(path)s
  spec              %(spec)s
  scenarios state   %(state)s
"""

SCENARIOS_STEPS = """  1. Create or refresh scenarios.md. It adds a section for each new criterion:

         "%(bin)s/craft-scenarios" draft

  2. Write one `- Given ..., when ..., then ...` line per case under each
     `## <ID>` heading.%(missing)s
  3. Present the scenarios to the developer. Stop.
  4. Ask the developer to approve them: to type this line in the prompt, or
     approve them on the board's Scenarios tab:

         ! "%(bin)s/craft-approve" --scenarios

     Do not run it yourself. Only the developer approves.
"""

SCENARIOS_NEXT_STEP = {
    "draft": "\nThe scenarios are not approved. Do this, in order:\n\n" + SCENARIOS_STEPS,
    "stale": (
        "\nscenarios.md or spec.md changed after the scenarios were approved. The developer\n"
        "must approve them again. Do this, in order:\n\n" + SCENARIOS_STEPS
    ),
}

SCENARIOS_FOOTER = """
Do not write the test somewhere else, and do not rename it to get around this.

Writes under .claude/ are always allowed."""

FOOTER = """
Do not write the file somewhere else, and do not rename it to get around this.
Code written before its spec is agreed builds what was typed, not what was wanted.

Writes under .claude/ are always allowed, with the Write tool or with Bash."""


def is_test_path(path, cwd):
    """Return True when path is a test file under the host repository."""
    import craft_stack

    root = craft_state.host_root(cwd)
    target = pathlib.Path(path)
    if not target.is_absolute():
        target = pathlib.Path(cwd or os.getcwd()) / target
    relative = pathlib.Path(os.path.normpath(str(target))).relative_to(root).as_posix()
    tests = craft_stack.test_spec(cwd)
    return relative.endswith(tuple(tests["extensions"])) and craft_state.path_matches(relative, tests["globs"])


def scenarios_denial(path, cwd, route):
    """Return the deny reason for a test write, or "" when the write may go on."""
    if not is_test_path(path, cwd):
        return ""
    state, detail = craft_state.scenarios_state(cwd)
    if state == "approved" or detail.get("error"):
        return ""
    missing = detail.get("missing") or []
    values = {
        "route": route,
        "path": path,
        "spec": detail.get("spec") or "none active",
        "state": state,
        "bin": str(BIN),
        "missing": "\n     Criteria with no case yet: %s." % ", ".join(missing) if missing else "",
    }
    step = SCENARIOS_NEXT_STEP["stale" if state == "stale" else "draft"]
    return SCENARIOS_HEADER % values + step % values + SCENARIOS_FOOTER


def spec_denial(path, route, state, detail):
    """Return the deny reason for a write while the spec is not approved."""
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
    return HEADER % values + NEXT_STEP.get(state, NEXT_STEP["none"]) % values + FOOTER


def bash_denial(command, cwd, route, state, detail):
    """Return the deny reason for a Bash command while the gate is shut, or ''."""
    effects = craft_state.bash_effects(command, cwd)
    if effects["unparsed"] and WRITE_HINT.search(command):
        return UNREADABLE
    records = craft_state.gated_writes(cwd)
    blocked = []
    for writer in effects["writers"]:
        for target in writer["targets"] + writer["redirects"]:
            if craft_state.is_inside_craft_area(target, cwd):
                continue
            relative = craft_state.repo_relative(target, cwd)
            record = records.get(relative)
            if record and craft_state.is_restore(writer, target, record):
                continue
            blocked.append(relative)
    if not blocked:
        return ""
    return spec_denial(", ".join(dict.fromkeys(blocked)), route, state, detail)


def bash_decision(payload, cwd, route):
    """Return the decision for a Bash call in a craft session. Store a snapshot when it is allowed.

    The snapshot holds approval.json on every route. While the spec gate is
    shut, it also holds the changed files and which of them are untracked. Each
    tracked changed file gets a backup.
    """
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return ("allow", "")
    snapshot = {"approval": craft_state.approval_snapshot(cwd)}
    if route in GATED_ROUTES:
        state, detail = craft_state.spec_state(cwd)
        if state == "approved":
            craft_state.clear_gated_writes(cwd)
        else:
            reason = bash_denial(command, cwd, route, state, detail)
            if reason:
                return ("deny", reason)
            untracked = set()
            files = craft_state.changed_files(cwd, untracked)
            if files is not None:
                craft_state.backup_files(files, cwd, untracked)
                snapshot["files"] = files
                snapshot["untracked"] = sorted(untracked)
    craft_state.save_bash_snapshot(payload.get("tool_use_id"), snapshot, cwd)
    return ("allow", "")


def restores_by_write(payload, relative, record, cwd):
    """Return True when a Write call puts back the content the file had before the Bash call."""
    tool_input = payload.get("tool_input")
    content = tool_input.get("content") if isinstance(tool_input, dict) else None
    if payload.get("tool_name") != "Write" or not isinstance(content, str):
        return False
    digest = craft_state.text_digest(content)
    if record.get("before") == "dirty":
        return digest == record.get("sha")
    if record.get("before") == "clean":
        return digest == craft_state.head_digest(relative, cwd)
    return False


def decide(payload):
    """Return ("allow", "") or ("deny", reason). Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("allow", "")
        is_bash = payload.get("tool_name") == "Bash"
        if not is_bash and not craft_state.is_write_tool(payload):
            return ("allow", "")

        cwd = craft_state.payload_cwd(payload)
        if not craft_state.is_active(cwd):
            # No craft session in this repository. The plugin stays out of the way.
            return ("allow", "")

        route = craft_state.current_route(cwd)
        if is_bash:
            return bash_decision(payload, cwd, route)
        if route not in GATED_ROUTES:
            return ("allow", "")

        path = craft_state.target_path(payload)
        if not path:
            return ("allow", "")
        if craft_state.is_inside_craft_area(path, cwd):
            return ("allow", "")

        state, detail = craft_state.spec_state(cwd)
        if state == "approved":
            craft_state.clear_gated_writes(cwd)
            reason = scenarios_denial(path, cwd, route)
            return ("deny", reason) if reason else ("allow", "")
        relative = craft_state.repo_relative(path, cwd)
        record = craft_state.gated_writes(cwd).get(relative)
        if record is None:
            return ("deny", spec_denial(path, route, state, detail))
        if restores_by_write(payload, relative, record, cwd):
            return ("allow", "")
        command = craft_state.restore_command(relative, record, cwd) or "no command restores it. Tell the developer."
        return ("deny", spec_denial(path, route, state, detail) + RESTORE_HINT % {"command": command})
    except Exception:
        return ("allow", "")


if __name__ == "__main__":
    sys.exit(craft_state.run_hook(decide))
