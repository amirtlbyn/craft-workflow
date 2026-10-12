#!/usr/bin/env python3
"""PreToolUse on Write|Edit - refuse to edit a document the developer owns.

A `*.human.md` document carries a HUMAN-OWNED banner. An agent that wants a
change reports the fragment and lets the developer decide. Until now that was a
sentence in standards/README.md. This makes it structural.

This is the one hook that runs with no craft session active. Ownership is a
property of the file, not of the session.

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

DENIAL = """This file is owned by the developer, so an agent must not edit it.

  %(path)s

Do this instead:

  1. Quote the exact fragment you would change, with the file name and the line
     number.
  2. Say what is wrong with it, and what it should say.
  3. Give that to the developer. The developer decides.

A `*.human.md` document carries a HUMAN-OWNED banner. To change one at the
source, edit it in the repository it comes from, then run
scripts/sync-standards.sh and regenerate standards/SOURCE.lock.

This rule is in standards/README.md and in config/workflow.md section 1."""


def decide(payload):
    """Return ("allow", "") or ("deny", reason). Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("allow", "")
        if not craft_state.is_write_tool(payload):
            return ("allow", "")

        path = craft_state.target_path(payload)
        if not path:
            return ("allow", "")

        globs = craft_state.globs_for("human_owned")
        if not globs:
            # No configuration means no opinion.
            return ("allow", "")
        if not craft_state.path_matches(path, globs):
            return ("allow", "")

        return ("deny", DENIAL % {"path": path})
    except Exception:
        return ("allow", "")


if __name__ == "__main__":
    sys.exit(craft_state.run_hook(decide))
