"""Tests for stale checks and the exact checkpoint match, one per acceptance criterion of the CRF spec."""

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import craft_state  # noqa: E402
import verify_gates  # noqa: E402

BIN = PLUGIN_ROOT / "bin"
CHECKPOINT = "pytest apps -q"
NEEDS_GIT = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def git(root, *arguments):
    """Run git in root."""
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"] + list(arguments), check=True)


def make_repo(root, checkpoint=CHECKPOINT):
    """Return a git repository with app/x.py committed, a .gitignore, and a quick-route session."""
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "app").mkdir()
    (root / "app" / "x.py").write_text("before\n", encoding="utf-8")
    (root / ".gitignore").write_text("*.log\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "init")
    craft_state.start_session("quick", session_id="sess-1", checkpoint=checkpoint, cwd=str(root))
    return root


def craft_check(root, command, run_in=None):
    """Run bin/craft-check on command in root, or in run_in with --cwd, and return its process."""
    flags = ["--cwd", str(run_in)] if run_in else []
    return subprocess.run(
        [sys.executable, str(BIN / "craft-check")] + flags + ["--", command],
        cwd=str(root), capture_output=True, text=True, check=False,
    )


def stored_checks(root):
    """Return the checks recorded in root's session.json."""
    return json.loads((root / ".claude" / "craft" / "session.json").read_text(encoding="utf-8"))["checks"]


def record(root, command, tree="", exit_code=0):
    """Record a check with tree as its fingerprint ('' for none)."""
    craft_state.record_check(command, exit_code, cwd=str(root), tree=tree or None)


def stop(root, message="Session 2 is `done`."):
    """Return a Stop payload for root."""
    return {"session_id": "sess-1", "cwd": str(root), "stop_hook_active": False, "last_assistant_message": message}


def run_ui_state(root):
    """Return the craft-ui-state snapshot of root."""
    result = subprocess.run(
        [sys.executable, str(BIN / "craft-ui-state"), "--cwd", str(root)],
        cwd=str(root), capture_output=True, text=True, check=False,
    )
    return json.loads(result.stdout)


@NEEDS_GIT
def test_check_records_a_fingerprint_of_the_tree(tmp_path):
    """CRF-8: Given a git repo with an active session, when craft-check records a check, then the record holds a tree fingerprint that ignores .claude/ and ignored files, and changes with an untracked file."""
    root = make_repo(tmp_path / "repo")
    craft_check(root, "true")
    (root / ".claude" / "notes.md").write_text("n\n", encoding="utf-8")
    (root / "debug.log").write_text("ignored\n", encoding="utf-8")
    craft_check(root, "true")
    (root / "app" / "new.py").write_text("new\n", encoding="utf-8")
    craft_check(root, "true")
    first, second, third = (check.get("tree") for check in stored_checks(root))
    before_commit = craft_state.tree_fingerprint(str(root))
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "tested code")

    assert first
    assert second == first
    assert third != first
    assert craft_state.tree_fingerprint(str(root)) == before_commit

    # Odd paths: none of them makes the fingerprint None, and a commit keeps it.
    (root / "app" / ".#x.py").symlink_to("missing-target")
    (root / "app" / "linked").symlink_to("x.py")
    (root / "app" / "dir link").symlink_to("..")
    (root / "app" / '"quoted".py').write_text("q\n", encoding="utf-8")
    (root / "app" / "line\nbreak.py").write_text("n\n", encoding="utf-8")
    (root / "app" / "carriage\r").write_text("c\n", encoding="utf-8")
    odd = craft_state.tree_fingerprint(str(root))
    (root / "app" / "x.py").write_text("edited\n", encoding="utf-8")
    edited = craft_state.tree_fingerprint(str(root))
    (root / "app" / "x.py").write_text("before\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "odd paths")

    assert odd
    assert edited and edited != odd
    assert craft_state.tree_fingerprint(str(root)) == odd


@NEEDS_GIT
def test_stop_refuses_done_on_a_stale_checkpoint(tmp_path):
    """CRF-9: Given a green checkpoint, when app/x.py is edited and the message claims done, then the Stop hook refuses and says stale; when nothing changed outside .claude/, then it allows."""
    root = make_repo(tmp_path / "repo", checkpoint="true")
    craft_check(root, "true")
    (root / ".claude" / "notes.md").write_text("n\n", encoding="utf-8")
    unchanged = verify_gates.decide(stop(root))
    (root / "app" / "x.py").write_text("after\n", encoding="utf-8")
    edited_action, edited_reason = verify_gates.decide(stop(root))

    assert unchanged[0] == "allow"
    assert edited_action == "block"
    assert "stale" in edited_reason

    # A red run of the checkpoint on the same tree comes after the green one.
    (root / "app" / "x.py").write_text("before\n", encoding="utf-8")
    craft_state.record_check("true", 1, cwd=str(root), tree=craft_state.tree_fingerprint(str(root)))

    assert verify_gates.decide(stop(root))[0] == "block"


@NEEDS_GIT
def test_a_check_without_a_fingerprint_stays_current(tmp_path):
    """CRF-10: Given a green checkpoint with no tree field, or a directory that is not a git work tree, then the check is current after edits."""
    old = make_repo(tmp_path / "old")
    record(old, CHECKPOINT)
    (old / "app" / "x.py").write_text("after\n", encoding="utf-8")
    plain = tmp_path / "plain"
    (plain / "app").mkdir(parents=True)
    craft_state.start_session("quick", session_id="sess-1", checkpoint="true", cwd=str(plain))
    craft_check(plain, "true")
    (plain / "app" / "x.py").write_text("after\n", encoding="utf-8")

    assert verify_gates.decide(stop(old))[0] == "allow"
    assert "tree" not in stored_checks(plain)[0]
    assert verify_gates.decide(stop(plain))[0] == "allow"


@NEEDS_GIT
def test_ui_state_reports_a_stale_check(tmp_path):
    """CRF-11: Given a green checkpoint and a tracked file edited afterwards, when craft-ui-state runs, then the tests item is not ok with detail stale and Gate A is not green."""
    root = make_repo(tmp_path / "repo", checkpoint="true")
    craft_check(root, "true")
    fresh = run_ui_state(root)["gate_a"]["items"][1]
    (root / "app" / "x.py").write_text("after\n", encoding="utf-8")
    data = run_ui_state(root)
    tests = data["gate_a"]["items"][1]

    assert fresh["ok"] is True
    assert (tests["name"], tests["ok"], tests["detail"]) == ("tests", False, "stale")
    assert data["gate_a"]["green"] is False

    # The board and the Stop hook answer the same: a narrower run is not the checkpoint,
    # and a red run after a green one on the same tree is not Gate A.
    narrow = make_repo(tmp_path / "narrow", checkpoint=CHECKPOINT)
    craft_state.record_check("pytest apps -q -k one", 0, cwd=str(narrow), label="tests")
    red = make_repo(tmp_path / "red", checkpoint="true")
    tree = craft_state.tree_fingerprint(str(red))
    craft_state.record_check("true", 0, cwd=str(red), label="tests", tree=tree)
    craft_state.record_check("true", 1, cwd=str(red), label="tests", tree=tree)

    for repo in (narrow, red):
        board = run_ui_state(repo)["gate_a"]["items"][1]
        assert board["ok"] is not True
        assert verify_gates.decide(stop(repo))[0] == "block"
    assert run_ui_state(narrow)["gate_a"]["items"][1]["detail"] == "not run"


@NEEDS_GIT
def test_checkpoint_matches_exactly_after_whitespace(tmp_path):
    """CRF-12: Given checkpoint `pytest apps -q`, when only `pytest apps -q -k one` is green, then the stop is refused; when `pytest  apps -q` (extra space) is green, then it is allowed."""
    narrower = make_repo(tmp_path / "narrower")
    record(narrower, "pytest apps -q -k one")
    spaced = make_repo(tmp_path / "spaced")
    record(spaced, "pytest  apps  -q")

    assert verify_gates.decide(stop(narrower))[0] == "block"
    assert verify_gates.decide(stop(spaced))[0] == "allow"

    # The full suite fails at the root, then the same text passes from a subdirectory.
    sub = make_repo(tmp_path / "sub", checkpoint="test -f flag")
    (sub / "app" / "flag").write_text("x\n", encoding="utf-8")
    root_run = craft_check(sub, "test -f flag")
    sub_run = craft_check(sub, "test -f flag", run_in=sub / "app")

    assert (root_run.returncode, sub_run.returncode) == (1, 0)
    assert verify_gates.decide(stop(sub))[0] == "block"
