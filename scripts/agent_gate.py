#!/usr/bin/env python3
"""PreToolUse on Agent|Task - record each reviewer spawn for Gate B.

Gate B counts a review round only when a reviewer the round names was really
spawned (config/workflow.md section 3, CRF-13). This hook is how a spawn becomes
a fact: when a craft session is active and tool_input.subagent_type ends in
`reviewer` (reviewer, deep-reviewer, craft-workflow:reviewer, ...), it appends
{"agent": <short name>, "at": <time>} to session.json `spawns`.

It denies one thing: the model floor. A `coder` spawn with model haiku is
refused while the active spec says Risk: high (CRF-18). The floor is sonnet.

Recording is inert unless a craft session is recorded at
<repo>/.claude/craft/session.json. Fails open: any exception means allow.

Kill switch: CRAFT_HOOKS=off
"""

import pathlib
import sys

# Claude Code runs this file by path, so its own directory is already on
# sys.path. The line below keeps the import working when a test imports the
# module from somewhere else.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402


def decide(payload):
    """Record a reviewer spawn, and deny haiku for coder on a Risk: high spec. Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("allow", "")
        cwd = craft_state.payload_cwd(payload)
        tool_input = payload.get("tool_input") or {}
        agent = str(tool_input.get("subagent_type") or "").strip().rsplit(":", 1)[-1]
        if (
            agent.endswith("coder")
            and "haiku" in str(tool_input.get("model") or "").lower()
            and craft_state.spec_progress(cwd).get("risk") == "high"
        ):
            return ("deny", "The active spec says Risk: high. The model floor for coder is sonnet. Spawn it with sonnet or opus.")
        if not craft_state.is_active(cwd):
            return ("allow", "")
        if agent.endswith("reviewer"):
            craft_state.record_spawn(agent, cwd)
    except Exception:
        pass
    return ("allow", "")


if __name__ == "__main__":
    sys.exit(craft_state.run_hook(decide))
