#!/usr/bin/env python3
"""craft_selftest - prove the hooks decide correctly, without a live session.

Run it standalone, from anywhere:

    python3 scripts/craft_selftest.py
    python3 scripts/craft_selftest.py --verbose

It builds throwaway repositories under the system temporary directory, feeds
each hook a synthetic payload, and asserts the decision. Nothing outside those
temporary directories is read or written, and no Claude session is involved.

Four layers run, in this order:

  1. decisions   - each hook's decide() against a table of payloads
  2. library     - the path matcher and the state file round trip
  3. end to end  - each hook as a real process, with real bytes on stdin,
                   asserting the exit code and the JSON on stdout
  4. commands    - bin/craft-spec, bin/craft-approve, and bin/craft-check as
                   real processes against a throwaway repository

Exit code 0 when every case passes, 1 otherwise.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import craft_state  # noqa: E402
import gate_spec  # noqa: E402
import protect_human_owned  # noqa: E402
import session_context  # noqa: E402
import verify_gates  # noqa: E402

BIN = SCRIPTS.parent / "bin"

VERBOSE = "--verbose" in sys.argv

results = []
temporary_roots = []


# ---------------------------------------------------------------------------
# Test plumbing
# ---------------------------------------------------------------------------


def check(group, name, actual, expected):
    """Record one case. actual and expected are the action word."""
    passed = actual == expected
    results.append(
        {
            "group": group,
            "name": name,
            "expected": expected,
            "actual": actual,
            "passed": passed,
        }
    )
    return passed


def make_repo(route=None, session_id=None, checkpoint=None):
    """Create a throwaway repository. Return its path.

    With route=None the repository has no .claude/craft/session.json, which is
    the "no craft session" case every hook except protect_human_owned must
    ignore.
    """
    root = pathlib.Path(tempfile.mkdtemp(prefix="craft-selftest-"))
    temporary_roots.append(root)
    (root / ".git").mkdir()
    if route is not None:
        craft_state.start_session(
            route, session_id=session_id, checkpoint=checkpoint, cwd=str(root)
        )
    return root


SPEC_TEXT = """# SPEC: Daily withdrawal limit

Key: WDL · Route: task · Risk: high

## Acceptance criteria

| ID | Criterion | Class | Failure it catches |
|---|---|---|---|
| WDL-1 | WHEN over the limit, THE service SHALL reject it. | BUSINESS RULE | not enforced |
| WDL-2 | WHEN equal to the limit, THE service SHALL accept it. | BUSINESS RULE | off by one |
"""

TASKS_TEXT = """# TASKS: Daily withdrawal limit

Spec: spec.md · Key: WDL · Route: task · State: in progress

- [x] T1 — add the check in `apps/wallet/services.py` — WDL-1
- [ ] T2 — test WDL-1 and WDL-2 in `apps/wallet/tests/test_limit.py`
"""


def make_spec(root, approved=True, name="2026-09-23-daily-limit"):
    """Give a repository an active spec, optionally approved. Return its directory."""
    directory = pathlib.Path(root) / ".claude" / "specs" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "spec.md").write_text(SPEC_TEXT, encoding="utf-8")
    (directory / "tasks.md").write_text(TASKS_TEXT, encoding="utf-8")
    (directory.parent / "ACTIVE").write_text(name + "\n", encoding="utf-8")
    if craft_state.is_active(str(root)):
        session = craft_state.read_session(str(root))
        craft_state.start_session(session.get("route") or "task", cwd=str(root), spec=name)
    if approved:
        craft_state.add_spec_approval(
            name, craft_state.file_digest(directory / "spec.md"), cwd=str(root)
        )
    return directory


def write_payload(path, cwd, session_id="sess-1", tool="Write"):
    """Build a PreToolUse payload for a Write or Edit call."""
    return {
        "session_id": session_id,
        "transcript_path": "/tmp/does-not-exist.jsonl",
        "cwd": str(cwd),
        "permission_mode": "default",
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_use_id": "toolu_selftest",
        "tool_input": {"file_path": path, "content": "placeholder"},
    }


def stop_payload(cwd, message, session_id="sess-1", stop_hook_active=False):
    """Build a Stop payload."""
    return {
        "session_id": session_id,
        "transcript_path": "/tmp/does-not-exist.jsonl",
        "cwd": str(cwd),
        "permission_mode": "default",
        "hook_event_name": "Stop",
        "stop_hook_active": stop_hook_active,
        "last_assistant_message": message,
    }


class kill_switch(object):
    """Set CRAFT_HOOKS=off for the body of a with-statement."""

    def __enter__(self):
        self.previous = os.environ.get("CRAFT_HOOKS")
        os.environ["CRAFT_HOOKS"] = "off"

    def __exit__(self, *_unused):
        if self.previous is None:
            os.environ.pop("CRAFT_HOOKS", None)
        else:
            os.environ["CRAFT_HOOKS"] = self.previous
        return False


# ---------------------------------------------------------------------------
# Layer 1 - decisions
# ---------------------------------------------------------------------------


def test_protect_human_owned():
    group = "protect_human_owned"
    bare = make_repo()
    active = make_repo(route="task")

    def action(payload):
        return protect_human_owned.decide(payload)[0]

    check(
        group,
        "human-owned standard, no craft session",
        action(write_payload("standards/python_code_style.human.md", bare)),
        "deny",
    )
    check(
        group,
        "human-owned host document, craft session active",
        action(write_payload("aidocs/INVARIANTS.human.md", active)),
        "deny",
    )
    check(
        group,
        "human-owned document, absolute path",
        action(write_payload(str(bare / "standards/django_standards.human.md"), bare)),
        "deny",
    )
    check(
        group,
        "human-owned document, Edit rather than Write",
        action(write_payload("standards/x.human.md", bare, tool="Edit")),
        "deny",
    )
    check(
        group,
        "ordinary source file",
        action(write_payload("apps/wallet/services.py", bare)),
        "allow",
    )
    check(
        group,
        "ordinary markdown, not human-owned",
        action(write_payload("docs/notes.md", bare)),
        "allow",
    )
    check(
        group,
        "an ai-owned standard is editable",
        action(write_payload("standards/technical_standards.ai.md", bare)),
        "allow",
    )
    check(
        group,
        "a tool that is not a write",
        action(write_payload("standards/x.human.md", bare, tool="Bash")),
        "allow",
    )
    check(group, "empty payload", action({}), "allow")
    check(group, "payload with no tool_input", action({"tool_name": "Write"}), "allow")
    with kill_switch():
        check(
            group,
            "CRAFT_HOOKS=off",
            action(write_payload("standards/python_code_style.human.md", bare)),
            "allow",
        )


def test_gate_spec():
    group = "gate_spec"
    bare = make_repo()
    no_spec = make_repo(route="task", session_id="sess-1")
    quick = make_repo(route="quick", session_id="sess-1")
    unapproved = make_repo(route="task", session_id="sess-1")
    make_spec(unapproved, approved=False)
    approved = make_repo(route="project", session_id="sess-1")
    make_spec(approved, approved=True)
    stale = make_repo(route="task", session_id="sess-1")
    stale_dir = make_spec(stale, approved=True)
    with open(str(stale_dir / "spec.md"), "a", encoding="utf-8") as handle:
        handle.write("| WDL-3 | WHEN a new row appears after approval. | BUSINESS RULE | drift |\n")

    def action(payload):
        return gate_spec.decide(payload)[0]

    check(group, "source, route task, no spec", action(write_payload("apps/wallet/services.py", no_spec)), "deny")
    check(group, "test, route task, no spec", action(write_payload("apps/wallet/tests/test_limit.py", no_spec)), "deny")
    check(group, "source, spec not approved", action(write_payload("apps/wallet/services.py", unapproved)), "deny")
    check(group, "source, spec approved", action(write_payload("apps/wallet/services.py", approved)), "allow")
    check(group, "test, spec approved, scenarios not approved", action(write_payload("tests/test_wallet.py", approved)), "deny")
    scenarios = make_repo(route="task", session_id="sess-1")
    scenarios_dir = make_spec(scenarios, approved=True)
    scenarios_file = scenarios_dir / "scenarios.md"
    scenarios_file.write_text("## WDL-1\n- Given a, when b, then c\n\n## WDL-2\n- Given d, when e, then f\n", encoding="utf-8")
    _state, detail = craft_state.scenarios_state(str(scenarios))
    craft_state.add_scenarios_approval(
        scenarios_dir.name, detail["sha256"], detail["spec_sha256"], detail["count"], cwd=str(scenarios)
    )
    check(group, "test, scenarios approved", action(write_payload("tests/test_wallet.py", scenarios)), "allow")
    scenarios_file.chmod(0)
    if not os.access(str(scenarios_file), os.R_OK):
        check(group, "test, scenarios.md unreadable -> error -> allow", action(write_payload("tests/test_wallet.py", scenarios)), "allow")
    scenarios_file.chmod(0o644)
    check(
        group,
        "approval survives a new Claude session id",
        action(write_payload("apps/wallet/services.py", approved, session_id="sess-after-reset")),
        "allow",
    )
    check(group, "source, spec changed after approval", action(write_payload("apps/wallet/services.py", stale)), "deny")
    check(group, "spec.md itself, spec not approved", action(write_payload(".claude/specs/x/spec.md", unapproved)), "allow")
    check(
        group,
        "absolute path under .claude/, no spec",
        action(write_payload(str(no_spec / ".claude" / "specs" / "a" / "spec.md"), no_spec)),
        "allow",
    )
    check(
        group,
        "absolute path in the repository, no spec",
        action(write_payload(str(no_spec / "apps" / "wallet" / "services.py"), no_spec)),
        "deny",
    )
    check(group, "path outside the repository", action(write_payload("/tmp/scratch/notes.py", no_spec)), "allow")
    check(group, "../ climbs out of the repository", action(write_payload("../elsewhere/x.py", no_spec)), "allow")
    check(group, "MultiEdit is gated too", action(write_payload("apps/a.py", no_spec, tool="MultiEdit")), "deny")
    check(group, "Read is not a write", action(write_payload("apps/a.py", no_spec, tool="Read")), "allow")
    check(group, "source, route quick", action(write_payload("apps/wallet/services.py", quick)), "allow")
    check(group, "source, no session.json", action(write_payload("apps/wallet/services.py", bare)), "allow")
    check(group, "empty payload", action({}), "allow")
    reason = gate_spec.decide(write_payload("apps/a.py", stale))[1]
    check(group, "stale reason says the spec changed", "yes" if "changed after it was approved" in reason else "no", "yes")
    reason = gate_spec.decide(write_payload("apps/a.py", no_spec))[1]
    check(group, "no-spec reason names craft-spec new", "yes" if "craft-spec\" new" in reason else "no", "yes")
    with kill_switch():
        check(group, "CRAFT_HOOKS=off", action(write_payload("apps/wallet/services.py", no_spec)), "allow")


def test_verify_gates():
    group = "verify_gates"
    bare = make_repo()
    task = make_repo(route="task", session_id="sess-1")

    green = make_repo(route="task", session_id="sess-1")
    craft_state.record_check("pytest apps/wallet -v", 0, cwd=str(green))
    craft_state.record_spawn("reviewer", cwd=str(green), at="2000-01-01T00:00:00+00:00")
    craft_state.add_review({"lenses": ["spec", "style"], "decision": "APPROVE", "reviewers": ["reviewer"]}, cwd=str(green))

    red = make_repo(route="task", session_id="sess-1")
    craft_state.record_check("pytest apps/wallet -v", 1, cwd=str(red))

    pinned = make_repo(
        route="task", session_id="sess-1", checkpoint="pytest apps/wallet -v"
    )
    craft_state.record_check("ruff check .", 0, cwd=str(pinned))

    pinned_green = make_repo(
        route="task", session_id="sess-1", checkpoint="pytest apps/wallet -v"
    )
    craft_state.record_check("pytest apps/wallet -v", 0, cwd=str(pinned_green))
    craft_state.record_spawn("reviewer", cwd=str(pinned_green), at="2000-01-01T00:00:00+00:00")
    craft_state.add_review({"lenses": ["spec", "style"], "decision": "APPROVE", "reviewers": ["reviewer"]}, cwd=str(pinned_green))

    def action(payload):
        return verify_gates.decide(payload)[0]

    check(
        group,
        "claims `done`, nothing recorded",
        action(stop_payload(task, "Session 2 is `done`.")),
        "block",
    )
    check(
        group,
        "claims Gate A passed, nothing recorded",
        action(stop_payload(task, "Gate A passed. Moving on.")),
        "block",
    )
    check(
        group,
        "claims `done`, a check exited 1",
        action(stop_payload(red, "All tests pass, so this is `done`.")),
        "block",
    )
    check(
        group,
        "claims `done`, checkpoint set, only another command is green",
        action(stop_payload(pinned, "Marked done.")),
        "block",
    )
    check(
        group,
        "claims `done`, a check exited 0",
        action(stop_payload(green, "Session 2 is `done`.")),
        "allow",
    )
    check(
        group,
        "claims `done`, checkpoint set and green",
        action(stop_payload(pinned_green, "Session 2 is `done`.")),
        "allow",
    )
    check(
        group,
        "reports `blocked` honestly",
        action(stop_payload(task, "The test command cannot run here. State: `blocked`.")),
        "allow",
    )
    check(
        group,
        "the word done inside an ordinary sentence",
        action(stop_payload(task, "I am done reading the diff and have questions.")),
        "allow",
    )
    for message, expected in (
        ("Gate A has not passed yet.", "allow"),
        ("It is not `done` until Gate B is green.", "allow"),
        ("The session is blocked, not `done`.", "allow"),
        (
            "Correction: I made no Gate A claim for this spec. "
            "Gate A has not run for any criterion.",
            "allow",
        ),
        ("Gate A passed.", "block"),
        ("Gate A passed. Gate B has not run.", "block"),
        ("Session 2 is `done`.", "block"),
        ("Tests pass, so this is `done`.", "block"),
        ("Gate A is green, and the state is `tests green`, not done.", "block"),
        ("I am done reading the diff.", "allow"),
    ):
        check(
            group,
            "negation-aware, nothing recorded: %s" % message,
            action(stop_payload(task, message)),
            expected,
        )
    check(
        group,
        "stop_hook_active is already set",
        action(stop_payload(make_repo(route="quick"), "It is `done`.", stop_hook_active=True)),
        "allow",
    )
    check(
        group,
        "no last_assistant_message",
        action({"hook_event_name": "Stop", "cwd": str(task)}),
        "allow",
    )
    check(
        group,
        "last_assistant_message is not a string",
        action({"hook_event_name": "Stop", "cwd": str(task), "last_assistant_message": 7}),
        "allow",
    )
    check(
        group,
        "claims `done`, no session.json",
        action(stop_payload(bare, "It is `done`.")),
        "allow",
    )

    spec_green = make_repo(route="task", session_id="sess-1", checkpoint="pytest apps/wallet -q")
    make_spec(spec_green, approved=True)
    craft_state.record_check("pytest apps/wallet -q", 0, cwd=str(spec_green))
    craft_state.record_check("craft-spec trace", 0, cwd=str(spec_green), label="trace")
    craft_state.record_spawn("reviewer", cwd=str(spec_green), at="2000-01-01T00:00:00+00:00")
    craft_state.add_review({"lenses": ["spec", "style", "logic", "security"], "decision": "APPROVE", "reviewers": ["reviewer"]}, cwd=str(spec_green))
    check(
        group,
        "spec approved, checkpoint green, trace green",
        action(stop_payload(spec_green, "Session 1 is `done`.")),
        "allow",
    )

    spec_no_trace = make_repo(route="task", session_id="sess-1", checkpoint="pytest apps/wallet -q")
    make_spec(spec_no_trace, approved=True)
    craft_state.record_check("pytest apps/wallet -q", 0, cwd=str(spec_no_trace))
    check(
        group,
        "spec approved, checkpoint green, no trace recorded",
        action(stop_payload(spec_no_trace, "Session 1 is `done`.")),
        "block",
    )

    spec_red_trace = make_repo(route="task", session_id="sess-1", checkpoint="pytest apps/wallet -q")
    make_spec(spec_red_trace, approved=True)
    craft_state.record_check("pytest apps/wallet -q", 0, cwd=str(spec_red_trace))
    craft_state.record_check("craft-spec trace", 1, cwd=str(spec_red_trace), label="trace")
    check(
        group,
        "spec approved, checkpoint green, last trace red",
        action(stop_payload(spec_red_trace, "Gate A passed.")),
        "block",
    )

    spec_stale = make_repo(route="task", session_id="sess-1", checkpoint="pytest apps/wallet -q")
    stale_dir = make_spec(spec_stale, approved=True)
    craft_state.record_check("pytest apps/wallet -q", 0, cwd=str(spec_stale))
    craft_state.record_check("craft-spec trace", 0, cwd=str(spec_stale), label="trace")
    (stale_dir / "spec.md").write_text(SPEC_TEXT + "\nchanged\n", encoding="utf-8")
    check(
        group,
        "checkpoint and trace green, spec changed after approval",
        action(stop_payload(spec_stale, "It is `done`.")),
        "block",
    )
    check(group, "empty payload", action({}), "allow")
    with kill_switch():
        check(
            group,
            "CRAFT_HOOKS=off",
            action(stop_payload(task, "It is `done`.")),
            "allow",
        )


def test_session_context():
    group = "session_context"
    bare = make_repo()
    check(group, "no session, no spec -> nothing", str(session_context.context_lines({"cwd": str(bare)})), "[]")
    resumed = make_repo(route="task", session_id="sess-1")
    make_spec(resumed, approved=True)
    craft_state.record_check("pytest -q", 0, cwd=str(resumed))
    lines = session_context.context_lines({"cwd": str(resumed), "source": "resume"})
    text = "\n".join(lines)
    check(group, "names the spec", "yes" if "Daily withdrawal limit" in text else "no", "yes")
    check(group, "names the next task", "yes" if "T2" in text else "no", "yes")
    check(group, "says the spec is approved", "yes" if "spec approved" in text else "no", "yes")
    check(group, "stays short", "yes" if len(lines) <= 8 else "no", "yes")
    with kill_switch():
        check(group, "CRAFT_HOOKS=off -> nothing", str(session_context.context_lines({"cwd": str(resumed)})), "[]")


# ---------------------------------------------------------------------------
# Layer 2 - the library
# ---------------------------------------------------------------------------


def test_library():
    group = "craft_state"

    tests = craft_state.globs_for("tests")
    human = craft_state.globs_for("human_owned")
    matches = [
        ("tests/test_a.py", tests, True),
        ("apps/wallet/tests/test_limit.py", tests, True),
        ("apps/wallet/test_service.py", tests, True),
        ("apps/wallet/conftest.py", tests, True),
        ("/abs/repo/apps/wallet/tests/test_x.py", tests, True),
        ("apps/wallet/services.py", tests, False),
        ("apps/contests/views.py", tests, False),
        ("standards/python_code_style.human.md", human, True),
        ("/abs/repo/aidocs/ISSUES.human.md", human, True),
        ("standards/technical_standards.ai.md", human, False),
        ("README.md", human, False),
    ]
    for path, globs, expected in matches:
        check(
            group,
            "path_matches %s" % path,
            "match" if craft_state.path_matches(path, globs) else "no match",
            "match" if expected else "no match",
        )

    check(group, "path_matches with no globs", str(craft_state.path_matches("a.py", [])), "False")
    check(group, "path_matches with no path", str(craft_state.path_matches("", ["*"])), "False")
    check(group, "globs_for an unknown key", str(craft_state.globs_for("nope")), "[]")

    root = make_repo()
    check(group, "is_active before any session", str(craft_state.is_active(str(root))), "False")
    check(group, "current_route before any session", craft_state.current_route(str(root)), "")
    check(
        group,
        "approvals_for before any session",
        str(craft_state.approvals_for("sess-1", str(root))),
        "[]",
    )
    check(
        group,
        "record_check with no session creates one",
        str(craft_state.record_check("pytest -q", 0, cwd=str(root))),
        "True",
    )
    check(group, "is_active after record_check", str(craft_state.is_active(str(root))), "True")
    check(group, "green_checks after record_check", str(len(craft_state.green_checks(str(root)))), "1")
    check(
        group,
        "start_session keeps the recorded checks",
        str(
            craft_state.start_session("task", session_id="sess-9", cwd=str(root))
            and len(craft_state.green_checks(str(root))) == 1
        ),
        "True",
    )
    check(group, "current_route after start_session", craft_state.current_route(str(root)), "task")
    check(group, "current_session_id", str(craft_state.current_session_id(str(root))), "sess-9")
    check(
        group,
        "add_approval then approvals_for",
        str(
            craft_state.add_approval("1. a scenario", session_id="sess-9", cwd=str(root))
            and len(craft_state.approvals_for("sess-9", str(root))) == 1
        ),
        "True",
    )
    check(
        group,
        "an approval does not cover another session",
        str(len(craft_state.approvals_for("sess-other", str(root)))),
        "0",
    )
    check(
        group,
        "add_finding then open_findings",
        str(
            craft_state.add_finding({"title": "x", "severity": "Medium"}, cwd=str(root))
            and len(craft_state.open_findings(str(root))) == 1
        ),
        "True",
    )

    broken = make_repo(route="task")
    (broken / ".claude" / "craft" / "session.json").write_text("{not json", encoding="utf-8")
    check(group, "unparsable session.json: route", craft_state.current_route(str(broken)), "")
    check(
        group,
        "unparsable session.json: is_active stays True",
        str(craft_state.is_active(str(broken))),
        "True",
    )
    check(
        group,
        "unparsable session.json: no green checks",
        str(craft_state.green_checks(str(broken))),
        "[]",
    )
    check(
        group,
        "unparsable session.json: route unknown, gate allows",
        gate_spec.decide(write_payload("tests/test_a.py", broken))[0],
        "allow",
    )

    spec_root = make_repo(route="task")
    check(group, "spec_state with no spec", craft_state.spec_state(str(spec_root))[0], "none")
    spec_dir = make_spec(spec_root, approved=False)
    check(group, "spec_state before approval", craft_state.spec_state(str(spec_root))[0], "not approved")
    craft_state.add_spec_approval(spec_dir.name, craft_state.file_digest(spec_dir / "spec.md"), cwd=str(spec_root))
    check(group, "spec_state after approval", craft_state.spec_state(str(spec_root))[0], "approved")
    (spec_dir / "spec.md").write_text(SPEC_TEXT.replace("reject", "refuse"), encoding="utf-8")
    check(group, "spec_state after an edit", craft_state.spec_state(str(spec_root))[0], "stale")
    (spec_dir.parent / "ACTIVE").write_text("../../etc\n", encoding="utf-8")
    check(group, "ACTIVE that climbs out is ignored", craft_state.active_spec_name(str(spec_root)), "")
    (spec_dir.parent / "ACTIVE").write_text(spec_dir.name + "\n", encoding="utf-8")
    progress = craft_state.spec_progress(str(spec_root))
    check(
        group,
        "spec_progress counts tasks",
        "%s/%s" % (progress.get("done"), progress.get("total")),
        "1/2",
    )
    check(group, "spec_progress reads the risk", progress.get("risk", ""), "high")
    check(
        group,
        "spec_progress finds the next task",
        "yes" if progress.get("next_task", "").startswith("T2") else "no",
        "yes",
    )

    check(group, "read_payload on malformed JSON", str(craft_state.read_payload(FakeStdin("{oops"))), "{}")
    check(group, "read_payload on an empty body", str(craft_state.read_payload(FakeStdin(""))), "{}")
    check(group, "read_payload on a JSON list", str(craft_state.read_payload(FakeStdin("[1,2]"))), "{}")
    check(
        group,
        "read_payload on a valid object",
        str(craft_state.read_payload(FakeStdin('{"a": 1}'))),
        "{'a': 1}",
    )


class FakeStdin(object):
    """A stdin stand-in that hands back a fixed string."""

    def __init__(self, text):
        self.text = text

    def read(self):
        return self.text


# ---------------------------------------------------------------------------
# Layer 3 - the hooks as real processes
# ---------------------------------------------------------------------------


def run_hook_process(script, stdin_text, environment=None):
    """Run one hook as a process. Return (exit code, stdout, stderr, seconds).

    The process runs in a bare throwaway repository, so a payload with no cwd
    never reads the craft state of the repository that runs the self-test.
    """
    env = dict(os.environ)
    env.pop("CRAFT_HOOKS", None)
    if environment:
        env.update(environment)
    started = time.time()
    finished = subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        cwd=str(make_repo()),
        input=stdin_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        timeout=30,
    )
    return (
        finished.returncode,
        finished.stdout,
        finished.stderr,
        time.time() - started,
    )


def test_processes():
    group = "end to end"
    scripts = (
        "protect_human_owned.py",
        "protect_approval.py",
        "gate_spec.py",
        "gate_bash_after.py",
        "verify_gates.py",
        "session_context.py",
    )
    timings = []

    for script in scripts:
        for label, body in (
            ("malformed JSON on stdin", "{ this is not json"),
            ("an empty body on stdin", ""),
            ("a JSON list on stdin", "[1, 2, 3]"),
            ("JSON null on stdin", "null"),
        ):
            code, out, _, seconds = run_hook_process(script, body)
            timings.append((script, label, seconds))
            check(group, "%s: %s -> exit 0" % (script, label), str(code), "0")
            check(group, "%s: %s -> silent" % (script, label), out.strip(), "")

    bare = make_repo()
    task = make_repo(route="task", session_id="sess-1")

    code, out, err, seconds = run_hook_process(
        "protect_human_owned.py",
        json.dumps(write_payload("standards/python_code_style.human.md", bare)),
    )
    timings.append(("protect_human_owned.py", "deny", seconds))
    check(group, "protect_human_owned: human-owned -> exit 2", str(code), "2")
    check(
        group,
        "protect_human_owned: deny decision on stdout",
        json.loads(out)["hookSpecificOutput"]["permissionDecision"],
        "deny",
    )
    check(
        group,
        "protect_human_owned: the reason names the next step",
        "yes" if "Give that to the developer" in err else "no",
        "yes",
    )

    code, out, _, seconds = run_hook_process(
        "protect_human_owned.py",
        json.dumps(write_payload("apps/wallet/services.py", bare)),
    )
    timings.append(("protect_human_owned.py", "allow", seconds))
    check(group, "protect_human_owned: ordinary source -> exit 0", str(code), "0")
    check(group, "protect_human_owned: ordinary source -> silent", out.strip(), "")

    code, out, err, seconds = run_hook_process(
        "gate_spec.py",
        json.dumps(write_payload("apps/wallet/services.py", task)),
    )
    timings.append(("gate_spec.py", "deny", seconds))
    check(group, "gate_spec: source before a spec -> exit 2", str(code), "2")
    check(
        group,
        "gate_spec: deny decision on stdout",
        json.loads(out)["hookSpecificOutput"]["permissionDecision"],
        "deny",
    )
    check(
        group,
        "gate_spec: the reason names craft-approve",
        "yes" if "craft-approve" in err else "no",
        "yes",
    )

    code, out, _, seconds = run_hook_process(
        "gate_spec.py",
        json.dumps(write_payload("apps/wallet/services.py", task)),
        environment={"CRAFT_HOOKS": "off"},
    )
    timings.append(("gate_spec.py", "kill switch", seconds))
    check(group, "gate_spec: CRAFT_HOOKS=off -> exit 0", str(code), "0")
    check(group, "gate_spec: CRAFT_HOOKS=off -> silent", out.strip(), "")

    resumed = make_repo(route="task", session_id="sess-1")
    make_spec(resumed, approved=True)
    code, out, _, seconds = run_hook_process(
        "session_context.py", json.dumps({"cwd": str(resumed), "hook_event_name": "SessionStart"})
    )
    timings.append(("session_context.py", "context", seconds))
    check(group, "session_context: active spec -> exit 0", str(code), "0")
    check(
        group,
        "session_context: prints the spec status",
        "yes" if "Daily withdrawal limit" in out else "no",
        "yes",
    )

    code, out, err, seconds = run_hook_process(
        "verify_gates.py", json.dumps(stop_payload(task, "Session 2 is `done`."))
    )
    timings.append(("verify_gates.py", "block", seconds))
    check(group, "verify_gates: unproven `done` -> exit 2", str(code), "2")
    check(
        group,
        "verify_gates: block decision on stdout",
        json.loads(out)["hookSpecificOutput"]["decision"],
        "block",
    )
    check(
        group,
        "verify_gates: the correction names craft-check",
        "yes" if "craft-check" in err else "no",
        "yes",
    )

    code, out, _, seconds = run_hook_process(
        "verify_gates.py", json.dumps(stop_payload(bare, "Session 2 is `done`."))
    )
    timings.append(("verify_gates.py", "no session", seconds))
    check(group, "verify_gates: no craft session -> exit 0", str(code), "0")
    check(group, "verify_gates: no craft session -> silent", out.strip(), "")

    approve = {"cwd": str(bare), "tool_name": "Bash", "tool_input": {"command": "bin/craft-approve"}}
    code, out, _, seconds = run_hook_process("protect_approval.py", json.dumps(approve))
    timings.append(("protect_approval.py", "deny", seconds))
    check(group, "protect_approval: craft-approve -> exit 2", str(code), "2")
    code, out, _, seconds = run_hook_process(
        "protect_approval.py", json.dumps(approve), environment={"CRAFT_HOOKS": "off"}
    )
    check(group, "protect_approval: CRAFT_HOOKS=off -> exit 0", str(code), "0")

    if shutil.which("git") is None:
        return timings
    shut = make_repo()
    subprocess.run(["git", "init", "-q", str(shut)], check=False)
    craft_state.start_session("task", session_id="sess-1", cwd=str(shut))
    for number in range(20):
        (shut / ("dirty_%d.py" % number)).write_text("work %d\n" % number, encoding="utf-8")
    call = {"cwd": str(shut), "tool_name": "Bash", "tool_use_id": "toolu_e2e", "tool_input": {"command": "python3 gen.py"}}
    code, out, _, seconds = run_hook_process("gate_spec.py", json.dumps(call))
    timings.append(("gate_spec.py", "Bash, gate shut, 20 dirty files", seconds))
    check(group, "gate_spec: Bash with no write form, gate shut -> exit 0", str(code), "0")
    (shut / "generated.py").write_text("x\n", encoding="utf-8")
    code, out, err, seconds = run_hook_process("gate_bash_after.py", json.dumps(call))
    timings.append(("gate_bash_after.py", "report", seconds))
    check(group, "gate_bash_after: a new file while shut -> exit 2", str(code), "2")
    check(group, "gate_bash_after: the report names it", "yes" if "generated.py" in err else "no", "yes")
    failing = dict(call, tool_use_id="toolu_e2e_failed", hook_event_name="PostToolUseFailure")
    run_hook_process("gate_spec.py", json.dumps(failing))
    (shut / "half_written.py").write_text("x\n", encoding="utf-8")
    code, out, err, seconds = run_hook_process("gate_bash_after.py", json.dumps(failing))
    timings.append(("gate_bash_after.py", "report after a failed call", seconds))
    check(group, "gate_bash_after: a failed call is checked too -> exit 2", str(code), "2")
    code, out, err, seconds = run_hook_process("verify_gates.py", json.dumps(stop_payload(shut, "Paused.")))
    timings.append(("verify_gates.py", "unreverted file", seconds))
    check(group, "verify_gates: unreverted file -> exit 2", str(code), "2")

    return timings


# ---------------------------------------------------------------------------
# Layer 4 - the commands
# ---------------------------------------------------------------------------


def run_command(name, arguments, cwd):
    """Run one bin/ command. Return (exit code, stdout, stderr)."""
    env = dict(os.environ)
    env.pop("CRAFT_HOOKS", None)
    finished = subprocess.run(
        [sys.executable, str(BIN / name)] + list(arguments),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        timeout=60,
    )
    return finished.returncode, finished.stdout, finished.stderr


def test_commands():
    group = "commands"
    root = make_repo()
    code, out, err = run_command(
        "craft-spec",
        ["new", "--route", "task", "--title", "Daily withdrawal limit", "--key", "WDL",
         "--checkpoint", "python3 -c pass"],
        root,
    )
    check(group, "craft-spec new -> exit 0", str(code), "0")
    name = craft_state.active_spec_name(str(root))
    check(group, "craft-spec new sets ACTIVE", "yes" if name.endswith("daily-withdrawal-limit") else "no", "yes")
    check(group, "craft-spec new starts the session", craft_state.current_route(str(root)), "task")
    check(group, "craft-spec new leaves the spec unapproved", craft_state.spec_state(str(root))[0], "not approved")
    code, _, _ = run_command("craft-spec", ["new", "--route", "nope", "--title", "x"], root)
    check(group, "craft-spec new with a bad route -> exit 2", str(code), "2")

    spec_md = craft_state.active_spec_dir(str(root)) / "spec.md"
    spec_md.write_text(SPEC_TEXT, encoding="utf-8")
    code, _, _ = run_command("craft-approve", ["--note", "approve"], root)
    check(group, "craft-approve -> exit 0", str(code), "0")
    check(group, "craft-approve opens the gate", craft_state.spec_state(str(root))[0], "approved")
    log_text = (spec_md.parent / "log.md").read_text(encoding="utf-8")
    check(group, "craft-approve appends to log.md", "yes" if "spec approved" in log_text else "no", "yes")

    tests_dir = root / "apps" / "wallet" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_limit.py").write_text(
        "def test_over():\n    \"\"\"WDL-1: over the limit.\"\"\"\n", encoding="utf-8"
    )
    code, out, _ = run_command("craft-spec", ["trace"], root)
    check(group, "craft-spec trace with WDL-2 missing -> exit 1", str(code), "1")
    check(group, "craft-spec trace names the missing ID", "yes" if "MISSING  WDL-2" in out else "no", "yes")
    (spec_md.parent / "tasks.md").write_text(
        "# TASKS: x\n\n## Session 1 — limit\n\nState: in progress · Covers: WDL-1\n\n"
        "## Session 2 — boundary\n\nState: pending · Covers: WDL-2\n",
        encoding="utf-8",
    )
    code, out, _ = run_command("craft-spec", ["trace", "--session", "1"], root)
    check(group, "craft-spec trace --session 1 ignores session 2 -> exit 0", str(code), "0")
    code, out, _ = run_command("craft-spec", ["trace", "--session", "2"], root)
    check(group, "craft-spec trace --session 2 still misses WDL-2 -> exit 1", str(code), "1")
    code, _, _ = run_command("craft-spec", ["trace", "--session", "9"], root)
    check(group, "craft-spec trace --session with no such block -> exit 2", str(code), "2")
    (tests_dir / "test_limit.py").write_text(
        "def test_over():\n    \"\"\"WDL-1: over the limit.\"\"\"\n\n"
        "def test_equal():\n    \"\"\"WDL-2: at the limit.\"\"\"\n",
        encoding="utf-8",
    )
    code, out, _ = run_command("craft-spec", ["trace"], root)
    check(group, "craft-spec trace with every ID covered -> exit 0", str(code), "0")
    traces = [c for c in craft_state.checks(str(root)) if c.get("label") == "trace"]
    check(group, "craft-spec trace records its result", str([c.get("exit_code") for c in traces]), "[1, 0, 1, 0]")

    code, out, _ = run_command("craft-check", ["--", "python3 -c 'import sys; sys.exit(3)'"], root)
    check(group, "craft-check passes the exit code through", str(code), "3")
    last = craft_state.checks(str(root))[-1]
    check(group, "craft-check records the real exit code", str(last.get("exit_code")), "3")
    code, out, _ = run_command(
        "craft-check", ["--", sys.executable, "-c", "for i in range(500): print(i)"], root
    )
    check(group, "craft-check exit 0 on success", str(code), "0")
    check(group, "craft-check prints a short summary", "yes" if len(out.splitlines()) < 25 else "no", "yes")
    check(group, "craft-check keeps the full log", "yes" if "full log:" in out else "no", "yes")
    code, _, _ = run_command("craft-check", ["pytest"], root)
    check(group, "craft-check without -- -> exit 2", str(code), "2")

    code, out, _ = run_command("craft-spec", ["status"], root)
    check(group, "craft-spec status -> exit 0", str(code), "0")
    check(group, "craft-spec status shows approval", "yes" if "approved — the gate is open" in out else "no", "yes")
    code, _, _ = run_command("craft-spec", ["close"], root)
    check(group, "craft-spec close -> exit 0", str(code), "0")
    check(group, "craft-spec close clears ACTIVE", craft_state.active_spec_name(str(root)), "")
    check(group, "craft-spec close ends the session", str(craft_state.is_active(str(root))), "False")

    code, out, _ = run_command("craft-std", ["technical", "TS-1"], root)
    check(group, "craft-std prints one section", "yes" if code == 0 and out.count("\n## ") <= 1 and "TS-1" in out else "no", "yes")
    code, _, _ = run_command("craft-std", ["technical", "no such section"], root)
    check(group, "craft-std unknown section -> exit 1", str(code), "1")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def report(timings):
    width = 4
    for result in results:
        width = max(width, len(result["name"]))
    width = min(width, 56)

    current = None
    for result in results:
        if result["group"] != current:
            current = result["group"]
            print("")
            print(current)
        if result["passed"] and not VERBOSE:
            print("  PASS  %-*s  %s" % (width, result["name"], result["actual"]))
        elif result["passed"]:
            print(
                "  PASS  %-*s  %s (expected %s)"
                % (width, result["name"], result["actual"], result["expected"])
            )
        else:
            print(
                "  FAIL  %-*s  got %s, expected %s"
                % (width, result["name"], result["actual"], result["expected"])
            )

    print("")
    print("hook process time (includes Python start up)")
    slowest = 0.0
    for script, label, seconds in sorted(timings, key=lambda row: -row[2])[:4]:
        slowest = max(slowest, seconds)
        print("  %6.1f ms  %s  %s" % (seconds * 1000, script, label))
    if slowest > 0.25:
        print("  NOTE: a hook took longer than 250 ms. Look for a slow import.")

    passed = sum(1 for result in results if result["passed"])
    failed = len(results) - passed
    print("")
    print("%d passed, %d failed" % (passed, failed))
    return failed


def main():
    print("craft self-test")
    print("  scripts  %s" % SCRIPTS)
    print("  python   %s" % sys.version.split()[0])
    try:
        test_protect_human_owned()
        test_gate_spec()
        test_verify_gates()
        test_session_context()
        test_library()
        timings = test_processes()
        test_commands()
        failed = report(timings)
    finally:
        for root in temporary_roots:
            shutil.rmtree(str(root), ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
