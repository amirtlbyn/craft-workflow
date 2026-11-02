#!/usr/bin/env python3
"""PostToolUse and PostToolUseFailure on Bash - undo a forged approval, and report files changed while the spec gate was shut.

Before each Bash call in a craft session, gate_spec.py stores a snapshot in
.claude/craft/snapshots/<tool use id>.json. This hook reads it and removes it.
It runs after a call that succeeded and after one that failed or timed out.
When both events reach it for one call, the second finds no snapshot and does
nothing.

1. approval.json. When it changed during the call, by any route at all (a
   glob, a variable, `find -exec`, a symlink), the hook puts the earlier
   content back, or deletes a file the call created, and reports it. Only the
   developer approves, and the developer's `!` command and the board's `a` key
   are not Bash tool calls.

2. Source files, while the gate is shut. gate_spec.py denies the Bash write
   forms it can read. A form it cannot read, such as `python3 gen.py`, still
   runs. Each file inside the repository and outside .claude/ that git does
   not ignore, and that the call changed, goes into session.json
   `gated_writes` with how it was before: clean, absent, deleted, dirty with
   a backup, or untracked (no backup, report only). Claude is told the one
   command that restores each file.
   verify_gates.py refuses the stop while such a file still differs.

When the gate is open again, `gated_writes` is cleared. Outside a git work tree
there is no file check.

Fails open. Any exception, any payload it does not recognise, any missing
configuration: nothing is reported.

Kill switch: CRAFT_HOOKS=off, in the developer's own environment
"""

import pathlib
import sys

# Claude Code runs this file by path, so its own directory is already on
# sys.path. The line below keeps the import working when a test imports the
# module from somewhere else.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

FORGED = """approval.json changed during this Bash command, and only the developer
approves. The hook put back its content from before the command.
Result: forged approval reverted.

To approve, ask the developer to type `! "%(bin)s/craft-approve"` in the prompt,
or to press `a` on the board. If the developer approved on the board while this
command ran, ask the developer to approve again."""

REVERT = """The spec gate is shut, and this Bash command changed files of the repository.
On the %(route)s route, no source or test file is written until the developer
approves the spec. Restore each file now, with exactly this command:

%(rows)s

The stop is refused while a file still differs from its content before this
command. If the developer edited one of these files during the command, do not
restore it: tell the developer instead.

When the change is wanted, present the spec to the developer and ask for the
approval first."""

NO_BACKUP = (
    "no backup: an untracked file, a file over 1 MB, or over the 20 MB a call may copy. "
    "Tell the developer. The stop is not refused for it."
)


def revert_rows(paths, records, cwd):
    """Return one line per path: the path and the command that restores it."""
    rows = []
    for path in paths:
        command = craft_state.restore_command(path, records[path], cwd)
        rows.append("  %s\n      %s" % (path, command or NO_BACKUP))
    return "\n".join(rows)


def decide(payload):
    """Return ("allow", "") or ("report", reason). Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("allow", "")
        if payload.get("tool_name") != "Bash":
            return ("allow", "")
        if payload.get("hook_event_name") not in (None, "PostToolUse", "PostToolUseFailure"):
            return ("allow", "")

        cwd = craft_state.payload_cwd(payload)
        if not craft_state.is_active(cwd):
            return ("allow", "")
        snapshot = craft_state.pop_bash_snapshot(payload.get("tool_use_id"), cwd)
        if snapshot is None:
            # No snapshot, or the other after-call event already read it.
            return ("allow", "")

        messages = []
        if craft_state.restore_approval(snapshot.get("approval"), cwd):
            messages.append(FORGED % {"bin": craft_state.PLUGIN_ROOT / "bin"})

        before = snapshot.get("files")
        if not craft_state.gate_shut(cwd):
            craft_state.clear_gated_writes(cwd)
        elif isinstance(before, dict):
            after = craft_state.changed_files(cwd)
            if after is not None:
                records = craft_state.gated_records(before, after, cwd, set(snapshot.get("untracked") or ()))
                craft_state.add_gated_writes(records, cwd)
                left = craft_state.settle_gated_writes(cwd, current=after)
                differing = [path for path in sorted(records) if path in left]
                if differing:
                    messages.append(
                        REVERT % {"route": craft_state.current_route(cwd), "rows": revert_rows(differing, left, cwd)}
                    )
        return ("report", "\n\n".join(messages)) if messages else ("allow", "")
    except Exception:
        return ("allow", "")


if __name__ == "__main__":
    sys.exit(craft_state.run_hook(decide))
