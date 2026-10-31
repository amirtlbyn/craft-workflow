#!/usr/bin/env python3
"""Stop - refuse a claim of `done` or Gate A that has no command behind it.

config/workflow.md says a session is `done` only when Gate A and Gate B both
pass, and that the workflow must never claim a check ran when it did not. This
hook applies that rule to the workflow itself.

When the final message claims `done` or claims Gate A passed, session.json must
hold a check that exited 0. If it does not, the stop is blocked and the model is
told which state is actually true and which command was never run.

It also refuses any stop, with or without a claim, while a file that a Bash
call changed with the spec gate shut still differs from its content before that
call. gate_bash_after.py records those files in session.json `gated_writes`.
This refusal does not stop at stop_hook_active: it repeats up to three times in
a row, and the fourth stop goes through with a warning. A file that held
uncommitted work over 1 MB has no backup, so it never refuses a stop. When the
gate is open again, the record is cleared.

The hook is inert unless a craft session is recorded at
<repo>/.claude/craft/session.json.

Fails open, and deliberately so in four cases:

  * stop_hook_active is already set, so a claim block can never loop
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
DONE_WORD = (
    r"`done`"
    r"|\b(?:status|state)\s*[:=]\s*\**\s*done\b"
    r"|\b(?:is|are|now|marked|mark|marking|set\s+to|moved\s+to)\s+\**done\b"
    # complete, finished and ready to merge are a claim only about the work itself, never about a spec or a draft.
    r"|\b(?:session\s*\d+|task|project|change|work|implementation|merge\s+request|everything"
    r"|all\s+(?:tasks|sessions))\s+(?:is|are)\s+(?:now\s+)?(?:complete[d]?|finished|ready\s+to\s+merge)\b"
    r"|\bsession\s+\w+\s*[:\-]?\s*\**done\b"
    r"|^[\s>*#-]*\**done\**[\s.!:]*$"
    r"|\bgate\s*b\b[^\n]{0,80}?\b" + PASS_WORD + r"\b"
    r"|\b" + PASS_WORD + r"\b[^\n]{0,80}?\bgate\s*b\b"
)
DONE_ONLY = re.compile(DONE_WORD, re.IGNORECASE | re.MULTILINE)
DONE_CLAIM = re.compile(
    DONE_WORD
    + r"|\bgate\s*a\b[^\n]{0,80}?\b" + PASS_WORD + r"\b"
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

Never write `done` for a command you did not run."""


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


def clause_before(text, start, end):
    """Return the clause of text that ends at end: from the last break before start to end."""
    breaks_before = [m.end() for m in CLAUSE_BREAK.finditer(text, 0, start)]
    return text[(breaks_before[-1] if breaks_before else 0):end]


# A line that also names another state or a next step is a progress report, not a claim.
OTHER_STATE = re.compile(
    r"\bin\s+progress\b|\bpending\b|\bnext\b|\brunning\b|\bre-running\b|\bneeds\s+review\b"
    r"|\bstill\s+needs\b|\bapprove\s+to\s+start\b|\bto\s+start\b|\bnot\s+yet\b",
    re.IGNORECASE,
)
# The words just before a match name its subject. Planning, a plan, a review, a fix, or a delta
# being done is not the session being done.
NOT_THE_WORK = re.compile(r"\b(?:plan|planning|review|fix|fixes|delta|draft|spec|scenarios?|design)\b", re.IGNORECASE)
LIST_LINE = re.compile(r"^\s*(?:[-*>|]|\d+\.)")
SESSION_WORD = re.compile(r"\bsessions?\s*\d+", re.IGNORECASE)
DONE_WORDS = re.compile(r"\b(?:done|complete[d]?|finished)\b", re.IGNORECASE)


def sentence_of(line, position):
    """Return the sentence of line that holds position. A sentence ends at . ! or ? before a space, outside backticks."""
    first, last = 0, len(line)
    for end in re.finditer(r"[.!?](?=\s|$)", line):
        if line.count("`", 0, end.start()) % 2:
            continue
        if end.end() <= position:
            first = end.end()
        else:
            last = end.end()
            break
    return line[first:last]


def is_progress_report(text, match):
    """Return True when the line of the match is a question, a progress report, or about something else."""
    start = text.rfind("\n", 0, match.start()) + 1
    end = text.find("\n", match.end())
    line = text[start:(len(text) if end < 0 else end)]
    if "?" in sentence_of(line, match.start() - start) or OTHER_STATE.search(sentence_of(line, match.start() - start)):
        return True
    before = re.split(r"[,;:()]", text[start:match.start()])[-1]
    if NOT_THE_WORK.search(" ".join(re.findall(r"[\w'-]+", before)[-3:])):
        return True
    sessions = [row for row in text.splitlines() if LIST_LINE.match(row) and SESSION_WORD.search(row)]
    return len(sessions) > 1 and not all(DONE_WORDS.search(row) for row in sessions)


def claims_done(message, pattern=DONE_CLAIM):
    """Return True when the message claims `done` or claims Gate A passed.

    With pattern=DONE_ONLY, only a claim of `done` counts. A match whose
    clause holds a negation word is skipped, and so is a match on a line that
    is a question, a progress report, or about a plan, review, fix, or delta.
    """
    try:
        text = str(message)
        for match in pattern.finditer(text):
            if NEGATION.search(clause_before(text, match.start(), match.end())):
                continue
            if not is_progress_report(text, match):
                return True
        return False
    except Exception:
        return False


def evidence_checks(cwd):
    """Return [the check that proves Gate A], or [] when none does.

    The proof is the newest run of the checkpoint from the repository root, of
    any exit code: it must have exited 0, and the files outside .claude/ must
    hold the content they held when it ran. See craft_state.checkpoint_evidence.
    """
    check, state = craft_state.checkpoint_evidence(cwd)
    return [check] if state == "ok" else []


SPEC_CORRECTION = """Stop refused. The final message claims `done` or claims Gate A passed,
and %(problem)s

On the %(route)s route, Gate A is "spec verified": every acceptance criterion of
the approved spec has exactly one test that names its ID, and the checkpoint
passed. Do one of these two, then stop again:

  A. Fix it, then run:

         "%(bin)s/craft-spec" trace

  B. Correct the claim. The true state is `blocked` or `tests green`. Name what
     is missing."""

UNREVERTED = """Stop refused (%(count)d of %(limit)d). While the spec gate was shut, a Bash
command changed these files, and they still differ from their content before
that command. Restore each one with exactly this command, then stop again:

%(rows)s

If the developer edited one of these files, do not restore it: tell the
developer. When the change is wanted, ask the developer to approve the spec."""

UNREVERTED_WARNING = """craft: these files changed while the spec gate was shut, and they are not
restored. The stop was refused %(limit)d times, so this stop goes through:

%(paths)s"""

MAX_REFUSALS = 3

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


GATE_B_CORRECTION = """Stop refused for Gate B. %(problem)s

On the %(route)s route, `done` needs Gate B as well as Gate A: a review round
recorded for the active spec by a reviewer that was really spawned, no
Critical or High finding left confirmed or unadjudicated, and review rounds that
cover every lens the diff earns (`bin/craft-spec lenses` lists them).

%(fix)s"""

CLOSING = """Do the steps above, then stop again. Or correct the claim: the true state is
`blocked` or `tests green`, and Gate B is not run."""

GATE_B_REFUSALS = "gate_b_refusals"


def gate_b_problem(cwd):
    """Return (problem, fix) when Gate B does not support a `done` claim, else ("", "")."""
    spec_name = craft_state.active_spec_name(cwd)
    reviews = craft_state.read_reviews(cwd)
    findings = craft_state.read_findings(cwd)
    floor = craft_state.lens_floor(cwd)
    gate = craft_state.gate_b(findings, reviews, spec_name, floor, craft_state.reviewer_spawns(cwd))
    bin_dir = craft_state.PLUGIN_ROOT / "bin"
    record = (
        '"%s/craft-session" record-review --lenses <lenses that ran> --reviewers <reviewers you spawned> '
        "--decision APPROVE|REQUEST_CHANGES|COMMENT" % bin_dir
    )
    incomplete = " The lens floor is incomplete (time limit): treat it as a minimum." if any(
        "floor incomplete" in str(entry.get("reason", "")) for entry in floor
    ) else ""
    lenses = ",".join(gate["floor"])
    problems, fixes = [], []
    if gate["state"] == "not run" and not gate["rounds"]:
        problems.append("Gate B has not run: no review round is recorded for %s.%s" % (spec_name or "this session", incomplete))
        fixes.append(
            "Run `%s/craft-spec lenses`, spawn the reviewer with the lenses it lists (now: %s), adjudicate its\n"
            "findings, then record the round:\n\n    %s" % (bin_dir, lenses, record)
        )
    elif gate["state"] == "not run":
        problems.append(
            "Gate B has not run: no reviewer was spawned for the recorded round(s). A round counts only when a\n"
            "reviewer it names was spawned (Agent tool) after the round before it."
        )
        fixes.append("Spawn the reviewer with the lenses %s, then record the round naming it:\n\n    %s" % (lenses, record))
    if gate["blocking"]:
        unadjudicated = gate["proposed_ids"]
        problems.append(
            "Critical or High findings are not closed: %s.%s" % (
                ", ".join(gate["blocking_ids"]),
                " Never adjudicated (proposed): %s." % ", ".join(unadjudicated) if unadjudicated else "",
            )
        )
        fixes.append(
            "The main session adjudicates each one. Confirm it and fix it, then mark it fixed:\n\n"
            '    "%s/craft-session" finding <id> --state fixed\n\n'
            "Only the developer can reject a finding (the board's Review tab, or a `!` line)." % bin_dir
        )
    if gate["missing"] and gate["counted"]:
        problems.append("the review rounds do not cover these lenses: %s.%s" % (", ".join(gate["missing"]), incomplete))
        fixes.append(
            "Spawn the reviewer with the missing lenses (%s), then record the round:\n\n    %s"
            % (",".join(gate["missing"]), record)
        )
    return ("\n".join(problems), "\n\n".join(fixes))


def unreverted_decision(cwd):
    """Return ("block", reason), ("warn", message), or ("allow", "") for the gated writes.

    The stop is refused up to MAX_REFUSALS times in a row, even when
    stop_hook_active is set. The next stop goes through with a warning, and
    the count starts again.
    """
    if not craft_state.read_session(cwd).get("gated_writes"):
        return ("allow", "")
    if not craft_state.gate_shut(cwd):
        craft_state.clear_gated_writes(cwd)
        return ("allow", "")
    left = craft_state.blocking_writes(cwd)
    blocking = sorted(left)
    if not blocking:
        craft_state.set_refusals(0, cwd)
        return ("allow", "")
    count = craft_state.read_session(cwd).get("unreverted_refusals", 0)
    count = count if isinstance(count, int) else 0
    if count >= MAX_REFUSALS:
        craft_state.set_refusals(0, cwd)
        return ("warn", UNREVERTED_WARNING % {"limit": MAX_REFUSALS, "paths": "\n".join("  " + path for path in blocking)})
    craft_state.set_refusals(count + 1, cwd)
    rows = "\n".join(
        "  %s\n      %s" % (path, craft_state.restore_command(path, left[path], cwd)) for path in blocking
    )
    return ("block", UNREVERTED % {"count": count + 1, "limit": MAX_REFUSALS, "rows": rows})


def decide(payload):
    """Return ("allow", ""), ("block", correction), or ("warn", message). Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("allow", "")
        cwd = craft_state.payload_cwd(payload)
        if not craft_state.is_active(cwd):
            return ("allow", "")

        action, reason = unreverted_decision(cwd)
        if action == "block":
            return (action, reason)
        warning = reason if action == "warn" else ""
        action, reason = claim_decision(payload, cwd)
        if action == "allow" and warning:
            return ("warn", warning)
        return (action, reason)
    except Exception:
        return ("allow", "")


def gate_b_text(cwd, route):
    """Return the Gate B refusal text for a `done` claim, or ''. Counts refusals in a row."""
    problem, fix = gate_b_problem(cwd)
    if not problem:
        craft_state.set_refusals(0, cwd, GATE_B_REFUSALS)
        return ""
    return GATE_B_CORRECTION % {"problem": problem, "route": route, "fix": fix}


def claim_decision(payload, cwd):
    """Return ("allow", "") or ("block", correction) for a claim of `done` or Gate A.

    Every problem found goes into one refusal: Gate A, the spec, and Gate B.
    stop_hook_active ends the Gate A and spec refusals, which would loop. Gate B
    is still checked, and refuses up to MAX_REFUSALS stops in a row, so
    "re-run the checkpoint, then say done again" cannot skip the review.
    """
    try:
        message = payload.get("last_assistant_message")
        if not isinstance(message, str) or not message.strip():
            # The transcript is not the shape this hook expects. Let it stop.
            return ("allow", "")

        if not claims_done(message):
            return ("allow", "")

        active = bool(payload.get("stop_hook_active"))
        route = craft_state.current_route(cwd)
        parts = []
        if not active:
            part = gate_a_text(cwd, route)
            if part:
                parts.append(part)
        if route in SPEC_ROUTES and claims_done(message, DONE_ONLY):
            count = craft_state.read_session(cwd).get(GATE_B_REFUSALS, 0)
            count = count if isinstance(count, int) and active else 0
            if count >= MAX_REFUSALS:
                craft_state.set_refusals(0, cwd, GATE_B_REFUSALS)
            else:
                text = gate_b_text(cwd, route)
                if text:
                    # Only a Gate B refusal on its own is counted. When Gate A also failed,
                    # this stop is refused once, as before.
                    if not parts:
                        craft_state.set_refusals(count + 1, cwd, GATE_B_REFUSALS)
                    parts.append(text)
        if not parts:
            return ("allow", "")
        return ("block", "\n\n---\n\n".join(parts) + ("\n\n" + CLOSING if len(parts) > 1 or "Gate B" in parts[-1] else ""))
    except Exception:
        return ("allow", "")


def gate_a_text(cwd, route):
    """Return the refusal text for Gate A and the spec check, or '' when both hold."""
    evidence_check, state = craft_state.checkpoint_evidence(cwd)
    if state == "ok":
        problem = spec_problem(cwd)
        if not problem:
            return ""
        return SPEC_CORRECTION % {"problem": problem, "route": route, "bin": str(craft_state.PLUGIN_ROOT / "bin")}

    all_checks = craft_state.checks(cwd)
    green = craft_state.green_checks(cwd)
    checkpoint = craft_state.checkpoint_command(cwd).strip()

    if not all_checks:
        evidence = "no command at all has been recorded for this session."
    elif not green:
        evidence = "every command recorded for this session exited non-zero."
    elif state == "stale":
        evidence = "the checkpoint is stale: files changed after its last green run. Run it again."
    elif state == "failed":
        evidence = "the newest run of the checkpoint command exited non-zero."
    else:
        evidence = "no recorded command that exited 0 matches the checkpoint command."

    return CORRECTION % {
        "evidence": evidence,
        "route": route or "not recorded",
        "check_count": len(all_checks),
        "green_count": len(green),
        "checkpoint": checkpoint or "not set. config/workflow.md section 6 names it",
        "bin": str(craft_state.PLUGIN_ROOT / "bin"),
    }


if __name__ == "__main__":
    sys.exit(craft_state.run_hook(decide))
