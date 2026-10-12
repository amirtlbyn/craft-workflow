#!/usr/bin/env python3
"""Stop - refuse a claim of `done` or Gate A that has no command behind it.

config/workflow.md says a session is `done` only when Gate A and Gate B both
pass, and that the workflow must never claim a check ran when it did not. This
hook applies that rule to the workflow itself.

When the final message claims `done` or claims Gate A passed, session.json must
hold a check that exited 0. If it does not, the stop is blocked and the model is
told which state is actually true and which command was never run.

The hook is inert unless a craft session is recorded at
<repo>/.claude/craft/session.json.

Fails open, and deliberately so in four cases:

  * stop_hook_active is already set, so a block can never loop
  * the payload carries no final message, so the transcript shape is not what
    this hook expects
  * the final message makes no claim of `done` or Gate A
  * anything at all raises

Kill switch: CRAFT_HOOKS=off
"""

import pathlib
import re
import sys

# Claude Code runs this file by path, so its own directory is already on
# sys.path. The line below keeps the import working when a test imports the
# module from somewhere else.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

PASS_WORD = r"(?:pass(?:ed|es)?|green|met|complete[d]?|satisfied|clear(?:ed)?)"

# What counts as a claim. The workflow writes its session states in backticks,
# so `done` is the common case. The rest are the ordinary English forms of the
# same claim. A bare "done" in the middle of a sentence is NOT a claim: "done
# reading the diff" must not block a stop.
DONE_CLAIM = re.compile(
    r"`done`"
    r"|\bstatus\s*[:=]\s*\**\s*done\b"
    r"|\b(?:is|are|now|marked|mark|marking|set\s+to|moved\s+to)\s+\**done\b"
    r"|^[\s>*#-]*\**done\**[\s.!:]*$"
    r"|\bgate\s*a\b[^\n]{0,80}?\b" + PASS_WORD + r"\b"
    r"|\b" + PASS_WORD + r"\b[^\n]{0,80}?\bgate\s*a\b",
    re.IGNORECASE | re.MULTILINE,
)

CORRECTION = """Stop refused. The final message claims `done` or claims Gate A passed,
and %(evidence)s

Gate A is tests green: the checkpoint command ran, and it passed. A claim with
no command behind it is the one thing this workflow must never produce.

  route                %(route)s
  checks recorded      %(check_count)d
  checks that exited 0 %(green_count)d
  checkpoint command   %(checkpoint)s

Do one of these two, then stop again:

  A. Run the checkpoint through craft-check. It runs the command and records
     its real exit code. Then repeat the claim if it passed:

         "%(bin)s/craft-check" -- <the checkpoint command>

  B. The command did not run, or it failed. Correct the claim. The true state is
     `blocked`. Name the command that did not run and what stopped it. Use
     `tests green` only after the checkpoint command is recorded with exit 0,
     and remember that `tests green` is still not `done`: Gate B, review green,
     is a separate gate.

Never write `done` for a command you did not run.

To turn every craft hook off for one command, set CRAFT_HOOKS=off."""


# A match inside a negated clause is not a claim: "Gate A has not passed" and
# "it is not `done` until Gate B is green" must not block a stop. A clause runs
# from the last break before the match to the first break after it.
CLAUSE_BREAK = re.compile(r"[.!?;:,\n]")

NEGATION = re.compile(
    r"\b(?:not|no|never|none|nothing|cannot|without|until|unless|before|yet"
    r"|instead\s+of|\w+n['\u2019]t|blocked|pending|fail|fails|failed|missing"
    r"|refused)\b",
    re.IGNORECASE,
)


def clause_around(text, start, end):
    """Return the clause of text that holds text[start:end]."""
    breaks_before = [m.end() for m in CLAUSE_BREAK.finditer(text, 0, start)]
    clause_start = breaks_before[-1] if breaks_before else 0
    after = CLAUSE_BREAK.search(text, end)
    clause_end = after.start() if after else len(text)
    return text[clause_start:clause_end]


def claims_done(message):
    """Return True when the message claims `done` or claims Gate A passed.

    A match whose clause holds a negation word is skipped.
    """
    try:
        text = str(message)
        for match in DONE_CLAIM.finditer(text):
            if not NEGATION.search(clause_around(text, match.start(), match.end())):
                return True
        return False
    except Exception:
        return False


def evidence_checks(cwd):
    """Return the recorded checks that prove Gate A, newest last.

    When the session records a checkpoint command, only a green check naming it
    counts. When it does not, any green check counts.
    """
    green = craft_state.green_checks(cwd)
    checkpoint = craft_state.checkpoint_command(cwd).strip()
    if not checkpoint:
        return green
    matching = []
    for check in green:
        command = str(check.get("command", ""))
        if checkpoint in command or command in checkpoint:
            matching.append(check)
    return matching


SPEC_CORRECTION = """Stop refused. The final message claims `done` or claims Gate A passed,
and %(problem)s

On the %(route)s route, Gate A is "spec verified": every acceptance criterion of
the approved spec has exactly one test that names its ID, and the checkpoint
passed. Do one of these two, then stop again:

  A. Fix it, then run:

         "%(bin)s/craft-spec" trace

  B. Correct the claim. The true state is `blocked` or `tests green`. Name what
     is missing.

To turn every craft hook off for one command, set CRAFT_HOOKS=off."""

SPEC_ROUTES = ("task", "project")


def spec_problem(cwd):
    """Return why the active spec does not support a done claim, or ''."""
    if not craft_state.active_spec_name(cwd):
        return ""
    if craft_state.current_route(cwd) not in SPEC_ROUTES:
        return ""
    state, _detail = craft_state.spec_state(cwd)
    if state == "not approved":
        return "the active spec was never approved. Nothing built from it can be done."
    if state == "stale":
        return "spec.md changed after its approval. The code was built against a spec nobody approved."
    traces = [
        check
        for check in craft_state.checks(cwd)
        if check.get("label") == "trace" or str(check.get("command", "")).strip() == "craft-spec trace"
    ]
    if not traces:
        return "no `craft-spec trace` is recorded, so no one checked that every criterion has a test."
    if traces[-1].get("exit_code") != 0:
        return "the last `craft-spec trace` found a criterion with no test."
    return ""


def decide(payload):
    """Return ("allow", "") or ("block", correction). Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("allow", "")

        # A block sets stop_hook_active on the next attempt. Allowing then is
        # what keeps this hook from looping forever.
        if payload.get("stop_hook_active"):
            return ("allow", "")

        cwd = craft_state.payload_cwd(payload)
        if not craft_state.is_active(cwd):
            return ("allow", "")

        message = payload.get("last_assistant_message")
        if not isinstance(message, str) or not message.strip():
            # The transcript is not the shape this hook expects. Let it stop.
            return ("allow", "")

        if not claims_done(message):
            return ("allow", "")

        if evidence_checks(cwd):
            problem = spec_problem(cwd)
            if not problem:
                return ("allow", "")
            return (
                "block",
                SPEC_CORRECTION
                % {
                    "problem": problem,
                    "route": craft_state.current_route(cwd),
                    "bin": str(craft_state.PLUGIN_ROOT / "bin"),
                },
            )

        all_checks = craft_state.checks(cwd)
        green = craft_state.green_checks(cwd)
        checkpoint = craft_state.checkpoint_command(cwd).strip()

        if not all_checks:
            evidence = "no command at all has been recorded for this session."
        elif not green:
            evidence = "every command recorded for this session exited non-zero."
        else:
            evidence = (
                "no recorded command that exited 0 matches the checkpoint command."
            )

        return (
            "block",
            CORRECTION
            % {
                "evidence": evidence,
                "route": craft_state.current_route(cwd) or "not recorded",
                "check_count": len(all_checks),
                "green_count": len(green),
                "checkpoint": checkpoint
                or "not set. config/workflow.md section 6 names it",
                "bin": str(craft_state.PLUGIN_ROOT / "bin"),
            },
        )
    except Exception:
        return ("allow", "")


if __name__ == "__main__":
    sys.exit(craft_state.run_hook(decide))
