#!/usr/bin/env python3
"""SessionStart - tell a new session where the active spec stands, in a few lines.

A session that starts after a usage-limit reset, a /clear, or a compaction knows
nothing about the work in progress. Without help it re-reads the repository to
find its place, and that costs more than the work it resumes. This hook prints a
short status of the active spec. Claude Code adds a SessionStart hook's standard
output to the session's context.

It prints nothing when no craft session and no active spec exist, so a
repository that does not use this workflow pays nothing.

Fails open: any exception prints nothing and exits 0. It never blocks a session.

Kill switch: CRAFT_HOOKS=off
"""

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

MAX_TASK_CHARS = 140


def jev_enabled(cwd):
    """Return True when the optional Jev layer is on. Never raises."""
    try:
        override = str(os.environ.get("CRAFT_JEV", "")).strip().lower()
        if override in ("on", "off"):
            return override == "on"
        data = json.loads(craft_state.state_path("jev.json", cwd).read_text(encoding="utf-8"))
        return bool(data.get("enabled"))
    except Exception:
        return False


def context_lines(payload):
    """Return the lines to print. [] when there is nothing to say. Never raises."""
    try:
        if craft_state.hooks_disabled():
            return []
        cwd = craft_state.payload_cwd(payload)
        spec_name = craft_state.active_spec_name(cwd)
        if not spec_name and not craft_state.is_active(cwd):
            return []

        lines = ["craft-workflow: work in progress in this repository."]
        route = craft_state.current_route(cwd) or "not recorded"
        if spec_name:
            state, _detail = craft_state.spec_state(cwd)
            progress = craft_state.spec_progress(cwd)
            title = progress.get("title") or spec_name
            lines.append(
                "  spec       %s (.claude/specs/%s/)" % (title, spec_name)
            )
            lines.append(
                "  route      %s · risk %s · spec %s"
                % (route, progress.get("risk") or "not set", state)
            )
            if progress.get("total"):
                lines.append(
                    "  tasks      %d of %d done · state %s"
                    % (
                        progress.get("done", 0),
                        progress.get("total", 0),
                        progress.get("state") or "not set",
                    )
                )
            next_task = progress.get("next_task", "")
            if next_task:
                if len(next_task) > MAX_TASK_CHARS:
                    next_task = next_task[: MAX_TASK_CHARS - 1] + "…"
                lines.append("  next task  %s" % next_task)
        else:
            lines.append("  route      %s · no active spec" % route)

        green = craft_state.green_checks(cwd)
        recorded = craft_state.checks(cwd)
        if recorded:
            last = recorded[-1]
            lines.append(
                "  checks     %d recorded, %d green · last: exit %s for %s"
                % (
                    len(recorded),
                    len(green),
                    last.get("exit_code"),
                    str(last.get("command", ""))[:80],
                )
            )
        try:
            import craft_stack

            stack = craft_stack.summary(cwd)
            names = ", ".join("%s %s%s" % (item["emoji"], item["id"], " (%s/)" % item["dir"] if item["dir"] else "")
                              for item in stack.get("stacks") or []) or "%s (default)" % stack.get("primary")
            concurrency = stack.get("concurrency") or {}
            lines.append("  stack      %s · concurrency %s, %s" % (
                names, concurrency.get("model", "?"), concurrency.get("verdict", "?")))
        except Exception:
            pass
        if jev_enabled(cwd):
            lines.append("  deciders   on · routing decisions come from bin/craft-jev decide (bin/craft-decide status)")
        lines.append(
            "Resume from the spec directory. Do not re-explore the repository. "
            "Details: %s status" % (craft_state.PLUGIN_ROOT / "bin" / "craft-spec")
        )
        return lines
    except Exception:
        return []


def main():
    try:
        payload = craft_state.read_payload()
        lines = context_lines(payload)
        if lines:
            sys.stdout.write("\n".join(lines) + "\n")
            sys.stdout.flush()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
