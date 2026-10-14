"""Tests for the scenarios state and commands, one per acceptance criterion of the TSC spec."""

import json
import os
import pathlib
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import craft_state  # noqa: E402
import gate_spec  # noqa: E402

SCENARIOS = PLUGIN_ROOT / "bin" / "craft-scenarios"
APPROVE = PLUGIN_ROOT / "bin" / "craft-approve"

SPEC_TEXT = """# SPEC: Daily withdrawal limit

Key: WDL

## Acceptance criteria

| ID | Criterion | Class | Failure it catches |
|---|---|---|---|
| WDL-1 | WHEN over the limit, THE service SHALL reject it. | BUSINESS RULE | not enforced |
| WDL-2 | WHEN equal to the limit, THE service SHALL accept it. | BUSINESS RULE | off by one |
| WDL-3 | WHEN under the limit, THE service SHALL accept it. | BUSINESS RULE | blocked |

## Invariants

| WDL-9 | not a criterion |
"""

SCENARIO_1 = "Given a limit of 100, when 101 is sent, then it is rejected"
SCENARIO_2 = "Given a limit of 100, when 100 is sent, then it is accepted"


def make_repo(tmp_path):
    """Return a throwaway repository whose active spec is approved."""
    (tmp_path / ".git").mkdir()
    directory = tmp_path / ".claude" / "specs" / "2026-10-12-daily-limit"
    directory.mkdir(parents=True)
    (directory / "spec.md").write_text(SPEC_TEXT, encoding="utf-8")
    (directory.parent / "ACTIVE").write_text("2026-10-12-daily-limit\n", encoding="utf-8")
    craft_state.add_spec_approval(directory.name, craft_state.file_digest(directory / "spec.md"), cwd=str(tmp_path))
    return directory


def run(script, root, *arguments):
    """Run one bin script against the throwaway repository."""
    return subprocess.run(
        [sys.executable, str(script), *arguments, "--cwd", str(root)], capture_output=True, text=True, check=False
    )


def approved_scenarios_repo(tmp_path):
    """Return a repository whose scenarios.md is complete and approved."""
    directory = make_repo(tmp_path)
    (directory / "scenarios.md").write_text(
        "## WDL-1\n- %s\n\n## WDL-2\n- %s\n\n## WDL-3\n- Given a, when b, then c\n" % (SCENARIO_1, SCENARIO_2),
        encoding="utf-8",
    )
    assert run(APPROVE, tmp_path, "--scenarios").returncode == 0
    return directory


def test_draft_keeps_written_lines_and_adds_none(tmp_path):
    """TSC-1: Given an approved spec and a scenarios.md out of order, when draft runs, then sections follow spec order and no line is added."""
    directory = make_repo(tmp_path)
    (directory / "scenarios.md").write_text(
        "Notes for me\n\n## WDL-2\n- %s\n<!-- keep -->\n\n## WDL-7\n- Given old, when x, then y\n\n## WDL-1\n- %s\n### Sub\n\n## Retired\nold note\n"
        % (SCENARIO_2, SCENARIO_1),
        encoding="utf-8",
    )

    result = run(SCENARIOS, tmp_path, "draft")

    assert result.returncode == 0
    assert (directory / "scenarios.md").read_text(encoding="utf-8") == (
        "Notes for me\n"
        "\n## WDL-1\n- %s\n### Sub\n"
        "\n## WDL-2\n- %s\n<!-- keep -->\n"
        "\n## WDL-3\n"
        "\n## Retired\nold note\n"
        "\n### WDL-7\n- Given old, when x, then y\n" % (SCENARIO_1, SCENARIO_2)
    )
    drafted = (directory / "scenarios.md").read_text(encoding="utf-8")
    for text in ("one\ntwo", "one\u2028two"):
        refused = run(SCENARIOS, tmp_path, "add", "WDL-3", text)
        assert refused.returncode == 2
        assert (directory / "scenarios.md").read_text(encoding="utf-8") == drafted


def test_edit_after_approval_makes_scenarios_stale(tmp_path):
    """TSC-3: Given approved scenarios, when scenarios.md is edited, then the state is stale."""
    directory = approved_scenarios_repo(tmp_path)
    before, _detail = craft_state.scenarios_state(str(tmp_path))

    (directory / "scenarios.md").write_text(
        (directory / "scenarios.md").read_text(encoding="utf-8") + "- Given more, when x, then y\n", encoding="utf-8"
    )
    after, _detail = craft_state.scenarios_state(str(tmp_path))

    assert (before, after) == ("approved", "stale")


def test_spec_change_after_approval_makes_scenarios_stale(tmp_path):
    """TSC-4: Given approved scenarios, when spec.md changes, then the state is stale."""
    directory = approved_scenarios_repo(tmp_path)

    (directory / "spec.md").write_text(SPEC_TEXT + "\nA delta.\n", encoding="utf-8")
    state, detail = craft_state.scenarios_state(str(tmp_path))

    assert state == "stale"
    assert detail["sha256"] == detail["approved_sha256"]
    assert detail["spec_sha256"] != detail["approved_spec_sha256"]


def test_approve_refuses_and_records_nothing_when_a_criterion_has_no_scenario(tmp_path):
    """TSC-5: Given WDL-2 and WDL-3 without a scenario, when approve --scenarios runs, then it exits 1, names both, and records nothing."""
    directory = make_repo(tmp_path)
    (directory / "scenarios.md").write_text("## WDL-1\n- %s\n" % SCENARIO_1, encoding="utf-8")

    result = run(APPROVE, tmp_path, "--scenarios")

    assert result.returncode == 1
    assert "WDL-2" in result.stderr and "WDL-3" in result.stderr and "WDL-1" not in result.stderr
    assert craft_state.scenario_approvals(directory.name, str(tmp_path)) == []
    assert json.loads(run(SCENARIOS, tmp_path, "status", "--json").stdout)["state"] == "not approved"

    (directory / "spec.md").write_text("# SPEC: x\n\n## Acceptance criteria\n\nnone yet\n", encoding="utf-8")
    craft_state.add_spec_approval(directory.name, craft_state.file_digest(directory / "spec.md"), cwd=str(tmp_path))
    empty = run(APPROVE, tmp_path, "--scenarios")
    assert empty.returncode == 1
    assert craft_state.scenario_approvals(directory.name, str(tmp_path)) == []


def write_payload(path, root):
    """Return a PreToolUse Write payload for path in the throwaway repository."""
    return {
        "session_id": "sess-1",
        "cwd": str(root),
        "tool_name": "Write",
        "tool_input": {"file_path": path, "content": "x"},
    }


def start_task_session(root, spec_name):
    """Record a craft session on the task route in the throwaway repository."""
    craft_state.start_session("task", cwd=str(root), spec=spec_name)


def test_gate_denies_test_files_until_scenarios_are_approved(tmp_path):
    """TSC-2: Given an approved spec, when a test file is written, then it is denied until the scenarios are approved; source and unreadable scenarios.md are allowed."""
    directory = make_repo(tmp_path)
    start_task_session(tmp_path, directory.name)
    (directory / "scenarios.md").write_text("## WDL-1\n- %s\n" % SCENARIO_1, encoding="utf-8")

    source = gate_spec.decide(write_payload("apps/wallet/services.py", tmp_path))[0]
    denied = gate_spec.decide(write_payload("tests/test_wallet.py", tmp_path))[0]
    denied_absolute = gate_spec.decide(write_payload(str(tmp_path / "tests" / "test_wallet.py"), tmp_path))[0]
    (directory / "scenarios.md").write_text(
        "## WDL-1\n- %s\n\n## WDL-2\n- %s\n\n## WDL-3\n- Given a, when b, then c\n" % (SCENARIO_1, SCENARIO_2),
        encoding="utf-8",
    )
    assert run(APPROVE, tmp_path, "--scenarios").returncode == 0
    approved = gate_spec.decide(write_payload("tests/test_wallet.py", tmp_path))[0]

    assert (source, denied, denied_absolute, approved) == ("allow", "deny", "deny", "allow")
    if os.geteuid() != 0:
        (directory / "scenarios.md").chmod(0)
        try:
            assert gate_spec.decide(write_payload("tests/test_wallet.py", tmp_path))[0] == "allow"
        finally:
            (directory / "scenarios.md").chmod(0o644)


def test_deny_reason_names_the_state_and_the_next_step(tmp_path):
    """TSC-6: Given scenarios that are not approved, when a test file is written, then the reason names the state, craft-scenarios draft, and the missing criterion."""
    directory = make_repo(tmp_path)
    start_task_session(tmp_path, directory.name)
    (directory / "scenarios.md").write_text("## WDL-1\n- %s\n" % SCENARIO_1, encoding="utf-8")

    action, reason = gate_spec.decide(write_payload("tests/test_wallet.py", tmp_path))

    assert action == "deny"
    assert "scenarios state   not approved" in reason
    assert 'craft-scenarios" draft' in reason
    assert 'craft-approve" --scenarios' in reason
    assert "WDL-2, WDL-3" in reason

    (directory / "scenarios.md").write_text(
        "## WDL-1\n- %s\n\n## WDL-2\n- %s\n\n## WDL-3\n- Given a, when b, then c\n" % (SCENARIO_1, SCENARIO_2),
        encoding="utf-8",
    )
    assert run(APPROVE, tmp_path, "--scenarios").returncode == 0
    (directory / "scenarios.md").write_text(
        "## WDL-1\n- %s\n\n## WDL-2\n- %s\n\n## WDL-3\n- Given a, when b, then d\n" % (SCENARIO_1, SCENARIO_2),
        encoding="utf-8",
    )

    action, reason = gate_spec.decide(write_payload("tests/test_wallet.py", tmp_path))

    assert action == "deny"
    assert "scenarios state   stale" in reason
    assert 'craft-scenarios" draft' in reason
    assert "one `- Given ..., when ..., then ...` line per case" in reason
