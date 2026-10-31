"""Tests for Gate B at Stop and the lens floor, one per acceptance criterion of the CRF spec."""

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import craft_state  # noqa: E402
import agent_gate  # noqa: E402
import verify_gates  # noqa: E402

BIN = PLUGIN_ROOT / "bin"
CHECKPOINT = "pytest apps -q"
NEEDS_GIT = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def git(root, *arguments):
    """Run git in root."""
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"] + list(arguments), check=True)


def head(root):
    """Return the HEAD commit of root."""
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def write(root, path, text="x = 1\n"):
    """Write a file under root, creating its directory."""
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def make_repo(root, route="task"):
    """Return a git repository with one commit and a session on route whose base is HEAD."""
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write(root, "README.md", "readme\n")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "init")
    craft_state.start_session(route, session_id="sess-1", checkpoint=CHECKPOINT, cwd=str(root), base=head(root))
    return root


def green_checkpoint(root):
    """Record a green checkpoint run against the tree as it is now."""
    craft_state.record_check(CHECKPOINT, 0, cwd=str(root), tree=craft_state.tree_fingerprint(str(root)))


def at(second):
    """Return a timestamp `second` seconds after a fixed minute."""
    return "2026-01-01T00:00:%02d+00:00" % second


def spawn(root, agent, second):
    """Record a reviewer spawn at the given second."""
    craft_state.record_spawn(agent, cwd=str(root), at=at(second))


def review(root, lenses, second, reviewers=("reviewer",)):
    """Record one review round that ran lenses, naming reviewers, at the given second."""
    craft_state.add_review(
        {"lenses": lenses, "decision": "APPROVE", "reviewers": list(reviewers), "at": at(second)}, cwd=str(root)
    )


def reviewed(root, lenses, spawned_at, recorded_at):
    """Spawn a reviewer and record its round."""
    spawn(root, "reviewer", spawned_at)
    review(root, lenses, recorded_at)


def activate_spec(root, risk="low"):
    """Make a spec with the given Risk the active spec of root, and return its name."""
    name = "2026-01-01-demo"
    write(root, ".claude/specs/%s/spec.md" % name, "# SPEC: Demo\n\nKey: DM · Route: task · Risk: %s\n" % risk)
    write(root, ".claude/specs/ACTIVE", name + "\n")
    craft_state.start_session("task", spec=name, cwd=str(root))
    return name


def stop(root, message="Session 3 is `done`.", active=False):
    """Return the Stop hook's decision for root."""
    payload = {"session_id": "sess-1", "cwd": str(root), "stop_hook_active": active, "last_assistant_message": message}
    return verify_gates.decide(payload)


def lenses(root, *flags):
    """Run `craft-spec lenses --json` in root and return the process."""
    return subprocess.run(
        [sys.executable, str(BIN / "craft-spec"), "lenses", "--json", "--cwd", str(root)] + list(flags),
        capture_output=True, text=True, check=False,
    )


def floor_of(root, *flags):
    """Return {lens: reason} from `craft-spec lenses --json` in root."""
    return {entry["lens"]: entry["reason"] for entry in json.loads(lenses(root, *flags).stdout)["lenses"]}


def board_gate_b(root):
    """Return the gate_b block of craft-ui-state for root."""
    result = subprocess.run(
        [sys.executable, str(BIN / "craft-ui-state"), "--cwd", str(root)],
        cwd=str(root), capture_output=True, text=True, check=False,
    )
    return json.loads(result.stdout)["gate_b"]


@NEEDS_GIT
def test_done_needs_a_review_round_by_a_spawned_reviewer(tmp_path):
    """CRF-13: Given a task session, when the final message claims done without a review round, with a round no reviewer was spawned for, with a stale Gate A repeated under stop_hook_active, or with done phrased another way, then the Stop hook refuses and says Gate B has not run; a real spawn plus a round allows it; quick is allowed."""
    root = make_repo(tmp_path / "task")
    green_checkpoint(root)
    action, reason = stop(root)
    assert action == "block"
    assert "Gate B has not run" in reason
    assert "craft-spec lenses" in reason
    assert stop(root, "Session 3 is tests green; Gate A passed.")[0] == "allow"

    quick = make_repo(tmp_path / "quick", route="quick")
    green_checkpoint(quick)
    assert stop(quick)[0] == "allow"

    # A round that names a reviewer nobody spawned does not count.
    review(root, ["spec", "style"], 5)
    action, reason = stop(root)
    assert action == "block"
    assert "no reviewer was spawned" in reason
    refused = subprocess.run(
        [sys.executable, str(BIN / "craft-session"), "record-review", "--lenses", "spec", "--decision", "APPROVE",
         "--cwd", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert refused.returncode != 0
    assert "--reviewers" in refused.stderr

    # The Agent hook records the spawn, and then the round counts.
    agent_gate.decide({"cwd": str(root), "tool_input": {"subagent_type": "craft-workflow:reviewer"}})
    agent_gate.decide({"cwd": str(root), "tool_input": {"subagent_type": "Explore"}})
    assert [item["agent"] for item in craft_state.reviewer_spawns(str(root))] == ["reviewer"]
    subprocess.run(
        [sys.executable, str(BIN / "craft-session"), "record-review", "--lenses", "spec,style", "--reviewers",
         "reviewer", "--decision", "APPROVE", "--cwd", str(root)],
        capture_output=True, text=True, check=True,
    )
    assert stop(root)[0] == "allow"

    # An earlier refusal in the turn (stale Gate A) does not excuse Gate B.
    again = make_repo(tmp_path / "again")
    first = stop(again)
    assert first[0] == "block"
    assert "Gate B has not run" in first[1] and "checkpoint" in first[1]
    green_checkpoint(again)
    assert [stop(again, active=True)[0] for _ in range(4)] == ["block", "block", "block", "allow"]

    # Other ways to say done.
    phrases = make_repo(tmp_path / "phrases")
    green_checkpoint(phrases)
    for message in (
        "Session 3 is `done` with no open findings.", "State: done", "Session 3: done",
        "Everything is complete.", "Gate B is green.", "Session 3 done.",
    ):
        assert stop(phrases, message)[0] == "block", message
    assert stop(phrases, "it is not `done` yet")[0] == "allow"
    for message in ("Session 3 is complete.", "The task is finished.", "All tasks are complete.", "State: done",
        "Session 3 is `done`. Next is Session 4.", "Session 3 is complete. Next step: Session 4 starts on sonnet.",
    ):
        assert stop(phrases, message)[0] == "block", message
    for message in (
        "The spec is complete. Reply approve, or tell me what to change.",
        "The scenarios draft is complete; please approve them.",
        "The plan is ready; reply go to start Session 1.",
        "Progress:\n- Session 1 — State: done\n- Session 2 — State: in progress",
        "Session 1 done, Session 2 done, Session 3 in progress.",
        "Sessions 1 and 2 are `done`; Session 3 is next.",
        "The plan is done: tasks.md holds 5 sessions. Approve to start Session 1.",
        "Planning is done.", "The delta review is done.", "The fix is done; re-running the reviewer…",
        "Implementation is complete; next step is the review.", "Is Session 3 done?",
    ):
        assert stop(phrases, message)[0] == "allow", message

    # A round recorded while no spec was active does not count for a later spec.
    late = make_repo(tmp_path / "late")
    green_checkpoint(late)
    reviewed(late, ["spec", "style"], 1, 2)
    assert stop(late)[0] == "allow"
    activate_spec(late)
    assert "Gate B has not run" in stop(late)[1]


@NEEDS_GIT
def test_unfinished_high_findings_block_done(tmp_path):
    """CRF-14: Given a review round counted, when the final message claims done with a High finding confirmed or proposed, then the Stop hook names it; once it is fixed or rejected it does not block."""
    root = make_repo(tmp_path / "repo")
    green_checkpoint(root)
    reviewed(root, ["spec", "style"], 1, 2)
    craft_state.add_finding({"id": "F1", "severity": "High", "state": "confirmed"}, cwd=str(root))
    action, reason = stop(root)
    assert action == "block"
    assert "F1" in reason

    craft_state.update_finding("F1", {"state": "fixed"}, cwd=str(root))
    assert stop(root)[0] == "allow"
    craft_state.update_finding("F1", {"state": "rejected"}, cwd=str(root))
    assert stop(root)[0] == "allow"

    craft_state.update_finding("F1", {"state": "proposed"}, cwd=str(root))
    action, reason = stop(root)
    assert action == "block"
    assert "F1" in reason and "proposed" in reason and "developer" in reason


@NEEDS_GIT
def test_missing_lenses_block_done_and_the_board_agrees(tmp_path):
    """CRF-15: Given a diff that adds a migration and one round with spec,style, when the final message claims done, then the Stop hook names logic and query; with a second round logic,query it allows, the board reports the same missing lenses, and craft-spec new records base equal to HEAD; under Risk: high a neutral path still misses logic and security."""
    root = make_repo(tmp_path / "repo")
    write(root, "app/migrations/0002_x.py")
    green_checkpoint(root)
    reviewed(root, ["spec", "style"], 1, 2)
    action, reason = stop(root)
    assert action == "block"
    assert "logic, query" in reason
    assert board_gate_b(root)["missing"] == ["logic", "query"]

    reviewed(root, ["logic", "query"], 3, 4)
    assert stop(root)[0] == "allow"
    assert board_gate_b(root)["missing"] == []

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    subprocess.run(["git", "init", "-q", str(fresh)], check=True)
    write(fresh, "README.md", "readme\n")
    git(fresh, "add", ".")
    git(fresh, "commit", "-q", "-m", "init")
    subprocess.run(
        [sys.executable, str(BIN / "craft-spec"), "new", "--route", "task", "--title", "Base spec", "--cwd", str(fresh)],
        capture_output=True, text=True, check=True,
    )
    session = json.loads((fresh / ".claude" / "craft" / "session.json").read_text(encoding="utf-8"))
    assert session["base"] == head(fresh)

    risky = make_repo(tmp_path / "risky")
    activate_spec(risky, "high")
    write(risky, "apps/exchange/matching.py")
    green_checkpoint(risky)
    craft_state.add_review({"lenses": ["spec", "style"], "decision": "APPROVE", "reviewers": ["reviewer"],
                            "at": at(2), "spec": "2026-01-01-demo"}, cwd=str(risky))
    spawn(risky, "reviewer", 1)
    assert "logic, security" in stop(risky)[1]


@NEEDS_GIT
def test_lens_floor_follows_the_diff(tmp_path):
    """CRF-16: Given diffs of different shapes, when craft-spec lenses runs, then the floor holds the lenses each path, added line, or Risk: high earns, each with its cause; --base widens it to committed changes; a missing base falls back to HEAD with a reason; a bad --base fails and writes nothing."""
    readme = make_repo(tmp_path / "readme")
    write(readme, "README.md", "changed\n")
    assert list(floor_of(readme)) == ["spec", "style"]

    money = make_repo(tmp_path / "money")
    write(money, "wallet/ledger.py")
    write(money, "app/migrations/0002_x.py")
    found = floor_of(money)
    assert "wallet/ledger.py" in found["logic"]
    assert "app/migrations/0002_x.py" in found["query"]

    go = make_repo(tmp_path / "go")
    write(go, "cmd/run.go", "package main\nfunc main() {\n\tgo func() {}()\n}\n")
    assert "cmd/run.go" in floor_of(go)["concurrency"]

    web = make_repo(tmp_path / "web")
    write(web, "app/views.py")
    assert "app/views.py" in floor_of(web)["security"]
    auth = make_repo(tmp_path / "auth")
    write(auth, "app/permissions.py")
    assert "app/permissions.py" in floor_of(auth)["security"]

    branch = make_repo(tmp_path / "branch")
    git(branch, "branch", "start")
    write(branch, "wallet/ledger.py")
    git(branch, "add", ".")
    git(branch, "commit", "-q", "-m", "ledger")
    write(branch, "app/models.py")
    assert list(floor_of(branch, "--base", "HEAD")) == ["spec", "style", "query"]
    assert list(floor_of(branch, "--base", "start")) == ["spec", "style", "logic", "query"]

    risky = make_repo(tmp_path / "risky")
    activate_spec(risky, "high")
    write(risky, "docs/notes.txt")
    found = floor_of(risky)
    assert found["logic"] == "Risk: high"
    assert found["security"] == "Risk: high"

    renamed = make_repo(tmp_path / "renamed")
    write(renamed, "apps/wallet/ledger.py", "balance = 1\nmore = 2\n")
    git(renamed, "add", ".")
    git(renamed, "commit", "-q", "-m", "ledger")
    craft_state.start_session("task", cwd=str(renamed), base=head(renamed))
    (renamed / "apps" / "core").mkdir()
    git(renamed, "mv", "apps/wallet/ledger.py", "apps/core/ledger.py")
    assert "apps/wallet/ledger.py" in floor_of(renamed)["logic"]

    gone = make_repo(tmp_path / "gone")
    craft_state.start_session("task", cwd=str(gone), base="deadbeef" * 5)
    write(gone, "wallet/ledger.py", "x = 2\n")
    found = floor_of(gone)
    assert "logic" in found
    assert "not found" in found["spec"]

    injected = lenses(gone, "--base", "--output=.claude/craft/session.json")
    assert injected.returncode != 0
    assert "--output=.claude/craft/session.json" in injected.stderr
    assert not (gone / "--output=.claude").exists()

    for number, line in enumerate((
        "await client.get(url)", "async function h() {}", "Thread(target=f).start()",
        "pool = ProcessPoolExecutor()", "var lock sync.Mutex", "launch { work() }",
    )):
        repo = make_repo(tmp_path / ("c%d" % number))
        write(repo, "app/work.txt.src", line + "\n")
        assert "concurrency" in floor_of(repo), line
    docs = make_repo(tmp_path / "docs")
    write(docs, "README.md", "use async def in handlers\n")
    assert "concurrency" not in floor_of(docs)
