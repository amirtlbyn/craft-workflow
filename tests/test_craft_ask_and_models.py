"""Tests for ask-first specs and model by difficulty, one per acceptance criterion of the CRF spec."""

import pathlib
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import agent_gate  # noqa: E402

BIN = PLUGIN_ROOT / "bin"
SPEC_NAME = "2026-01-01-x"
HEADER = "| Question | Options | Decision |\n|---|---|---|\n"


def make_repo(root, risk="low", questions="", tasks=None):
    """Return a repository whose active spec has the given risk, Open questions rows, and tasks.md."""
    directory = root / ".claude" / "specs" / SPEC_NAME
    directory.mkdir(parents=True)
    (root / ".git").mkdir()
    (directory.parent / "ACTIVE").write_text(SPEC_NAME + "\n", encoding="utf-8")
    (directory / "spec.md").write_text(
        "# SPEC: x\n\nKey: X · Route: task · Risk: %s\n\n## Acceptance criteria\n\n| ID | R |\n|---|---|\n"
        "| X-1 | a |\n\n## Open questions\n\n%s" % (risk, questions),
        encoding="utf-8",
    )
    if tasks is not None:
        (directory / "tasks.md").write_text(tasks, encoding="utf-8")
    return root


def approve(root):
    """Run craft-approve against root and return the completed process."""
    return subprocess.run(
        [sys.executable, str(BIN / "craft-approve"), "--cwd", str(root)], capture_output=True, text=True, check=False
    )


def spawn(root, subagent_type, model=None):
    """Return the hook action for a spawn of subagent_type with model."""
    tool_input = {"subagent_type": subagent_type}
    if model:
        tool_input["model"] = model
    return agent_gate.decide({"cwd": str(root), "tool_input": tool_input})


def test_crf_17_approve_refuses_unanswered_questions(tmp_path):
    """CRF-17: Given Open questions rows without the developer's attribution, when craft-approve runs, then it refuses and lists them."""
    attributed = "| Sync? | a, b | a (developer, 2026-10-31) |\n"
    refused = {
        "empty": HEADER + "| Sync or async? | sync, async | |\n",
        "assumed": HEADER + "| Sync? | a, b | Assume sync is fine |\n",
        "assumed-in-parens": HEADER + "| Sync? | a, b | sync (assumed) |\n",
        "tbd": HEADER + "| Sync? | a, b | TBD |\n",
        "bare-answer": HEADER + "| Sync? | a, b | Sonnet |\n",
        "no-decision-cell": HEADER + "| Sync? | a, b |\n",
        "owner-column-after": "| Question | Decision | Owner |\n|---|---|---|\n| Sync? | TBD | amir |\n",
        "escaped-pipe": HEADER + "| Sync? | a \\| b | TBD \\| (later) |\n",
        "second-table": HEADER + attributed + "\ntext\n\n| Question | Decision |\n|---|---|\n| Q2 | none |\n",
        "no-decision-header": "| Question | Options |\n|---|---|\n| Sync? | a (developer) |\n",
    }
    accepted = {
        "dated": HEADER + attributed,
        "short": HEADER + "| Sync? | a, b | a (developer) |\n",
        "bold": HEADER + "| Sync? | a, b | **a (Developer, 2026-10-31)** |\n",
        "header-only": HEADER,
        "owner-column-after": "| Question | Decision | Owner |\n|---|---|---|\n| Sync? | a (developer) | amir |\n",
        "escaped-pipe": HEADER + "| Sync? | a | a \\| b (developer) |\n",
        "no-section": None,
    }

    for name, table in refused.items():
        result = approve(make_repo(tmp_path / ("r-" + name), questions=table))
        assert result.returncode != 0, name
        assert "Q2" in result.stderr or "Sync" in result.stderr, name
    for name, table in accepted.items():
        root = make_repo(tmp_path / ("a-" + name), questions=table or "")
        if table is None:
            spec = root / ".claude" / "specs" / SPEC_NAME / "spec.md"
            spec.write_text(spec.read_text().split("## Open questions")[0], encoding="utf-8")
        assert approve(root).returncode == 0, name


def test_crf_18_haiku_floor_for_coder_on_high_risk(tmp_path):
    """CRF-18: Given Risk: high, when coder is spawned with haiku, then the hook denies with the floor sonnet; other spawns pass."""
    high = make_repo(tmp_path / "high", risk="high")
    low = make_repo(tmp_path / "low", risk="low")

    action, reason = spawn(high, "craft-workflow:coder", "haiku")
    assert action == "deny" and "sonnet" in reason
    assert spawn(high, "coder", "haiku")[0] == "deny"
    assert spawn(high, "coder", "sonnet")[0] == "allow"
    assert spawn(high, "coder", "opus")[0] == "allow"
    assert spawn(high, "coder")[0] == "allow"
    assert spawn(low, "coder", "haiku")[0] == "allow"
    assert spawn(high, "reviewer", "haiku")[0] == "allow"
    assert spawn(high, "Explore", "haiku")[0] == "allow"


def test_crf_19_status_shows_session_models(tmp_path):
    """CRF-19: Given tasks.md where session 1 has a Model line and session 2 has none, when status runs, then both show."""
    tasks = (
        "# TASKS: x\n\n## Session 1 — a\n\nState: pending · Covers: X-1\nModel: opus — cross-cutting gate logic\n\n"
        "- [ ] T1 — a — X-1\n\n## Session 2 — b\n\nState: pending · Covers: X-1\n\n- [ ] T2 — b — X-1\n"
    )
    root = make_repo(tmp_path, tasks=tasks)

    result = subprocess.run(
        [sys.executable, str(BIN / "craft-spec"), "status", "--cwd", str(root)], capture_output=True, text=True, check=True
    )

    assert "opus — cross-cutting gate logic" in result.stdout
    assert "model: not chosen" in result.stdout
