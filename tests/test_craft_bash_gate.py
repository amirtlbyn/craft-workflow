"""Tests for the Bash write gate and the approval protection, one per acceptance criterion of the CRF spec."""

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import craft_state  # noqa: E402
import gate_bash_after  # noqa: E402
import gate_spec  # noqa: E402
import protect_approval  # noqa: E402
import verify_gates  # noqa: E402

BIN = PLUGIN_ROOT / "bin"
APPROVE_LINE = '! "%s/craft-approve"' % BIN
SPEC_NAME = "2026-10-30-limit"
SPEC_TEXT = """# SPEC: Limit

Key: LIM · Route: task · Risk: high

## Acceptance criteria

| ID | Criterion | Class | Failure it catches |
|---|---|---|---|
| LIM-1 | WHEN over the limit, THE service SHALL reject it. | BUSINESS RULE | not enforced |
"""
NEEDS_GIT = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
DEV_WORK = "the developer's uncommitted work\n"
DEV_WORK_SHA = "e6ba26b3749dc9d6e8c7848f460d7a0ba79162d3e8f0438b31d12671495d3374"


def make_repo(root, route, approved):
    """Return a repository with a craft session on route and an active spec, approved or not."""
    (root / ".git").mkdir(parents=True)
    directory = root / ".claude" / "specs" / SPEC_NAME
    directory.mkdir(parents=True)
    (directory / "spec.md").write_text(SPEC_TEXT, encoding="utf-8")
    (directory.parent / "ACTIVE").write_text(SPEC_NAME + "\n", encoding="utf-8")
    craft_state.start_session(route, session_id="sess-1", cwd=str(root), spec=SPEC_NAME)
    if approved:
        approve_spec(root)
    return root


def make_git_repo(root):
    """Return a real git repository with app/x.py committed, a .gitignore, and an unapproved task spec."""
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "app").mkdir()
    (root / "app" / "x.py").write_text("before\n", encoding="utf-8")
    (root / ".gitignore").write_text("*.log\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"], check=True
    )
    directory = root / ".claude" / "specs" / SPEC_NAME
    directory.mkdir(parents=True)
    (directory / "spec.md").write_text(SPEC_TEXT, encoding="utf-8")
    (directory.parent / "ACTIVE").write_text(SPEC_NAME + "\n", encoding="utf-8")
    craft_state.start_session("task", session_id="sess-1", cwd=str(root), spec=SPEC_NAME)
    return root


def commit_then_change(root, count, size):
    """Commit count files of size bytes under app/, then change each one, so git sees count dirty tracked files."""
    paths = [root / "app" / ("big_%02d.py" % number) for number in range(count)]
    for number, path in enumerate(paths):
        path.write_text(chr(97 + number) * size, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "big"], check=True)
    for number, path in enumerate(paths):
        path.write_text(chr(65 + number) * size, encoding="utf-8")


def approve_spec(root):
    """Record the developer's approval of the active spec.md."""
    spec_md = root / ".claude" / "specs" / SPEC_NAME / "spec.md"
    craft_state.add_spec_approval(SPEC_NAME, craft_state.file_digest(spec_md), cwd=str(root))


def bash(command, root, tool_use_id="toolu_1"):
    """Return a Bash tool payload for command in root."""
    return {
        "session_id": "sess-1",
        "cwd": str(root),
        "tool_name": "Bash",
        "tool_use_id": tool_use_id,
        "tool_input": {"command": command},
    }


def write(path, root, tool="Write", content="x"):
    """Return a Write or Edit tool payload for path in root."""
    return {
        "session_id": "sess-1",
        "cwd": str(root),
        "tool_name": tool,
        "tool_input": {"file_path": str(path), "content": content, "new_string": content},
    }


def stop(root, message, again=False):
    """Return a Stop payload for root with message as the final message."""
    return {"session_id": "sess-1", "cwd": str(root), "stop_hook_active": again, "last_assistant_message": message}


def test_bash_write_forms_are_denied_while_the_spec_gate_is_shut(tmp_path):
    """CRF-1: Given the gate is shut on task, when Bash writes app/x.py by a recognised form, then it is denied and the reason names the state and the way through; approved and quick allow it."""
    shut = make_repo(tmp_path / "shut", "task", approved=False)
    approved = make_repo(tmp_path / "approved", "task", approved=True)
    quick = make_repo(tmp_path / "quick", "quick", approved=False)
    (shut / "app").mkdir()
    os.symlink(str(shut / "app"), str(tmp_path / "applink"))

    action, reason = gate_spec.decide(bash("cat > app/x.py <<EOF\nprint('x')\nEOF", shut))
    forms = (
        gate_spec.decide(bash("sed -i s/a/b/ app/x.py", shut))[0],
        gate_spec.decide(bash("tee app/x.py", shut))[0],
        gate_spec.decide(bash("cp a app/x.py", shut))[0],
        gate_spec.decide(bash("rm app/x.py", shut))[0],
        gate_spec.decide(bash("python3 - <<EOF\nwith open('app/x.py','w') as f:\n    f.write('x')\nEOF", shut))[0],
    )
    bypasses = (
        gate_spec.decide(bash("echo x > app/x.py # it's done", shut))[0],
        gate_spec.decide(bash("eval 'echo x > app/x.py'", shut))[0],
        gate_spec.decide(bash("echo 'echo x > app/x.py' | sh", shut))[0],
        gate_spec.decide(bash("if true; then echo x > app/x.py; fi", shut))[0],
        gate_spec.decide(bash("{ echo x > app/x.py; }", shut))[0],
        gate_spec.decide(bash("ls | xargs rm", shut))[0],
        gate_spec.decide(bash("find app -name '*.py' -delete", shut))[0],
        gate_spec.decide(bash("(cd /tmp); echo a > app/x.py", shut))[0],
        gate_spec.decide(bash("cd /nonexistent; echo a > app/x.py", shut))[0],
        gate_spec.decide(bash("cd /tmp || true; echo a > app/x.py", shut))[0],
        gate_spec.decide(bash("python3 -c 'import os; os.system(\"gen\")'", shut))[0],
        gate_spec.decide(bash("node -e \"require('child_process').execSync('gen')\"", shut))[0],
        gate_spec.decide(bash("echo x > %s/y.py" % (tmp_path / "applink"), shut))[0],
        gate_spec.decide(bash("echo 'x > app/x.py", shut))[0],
    )

    assert action == "deny"
    assert "blocked path   app/x.py" in reason
    assert "spec state     not approved" in reason
    assert APPROVE_LINE in reason
    assert forms == ("deny", "deny", "deny", "deny", "deny")
    assert bypasses == ("deny",) * 14
    assert gate_spec.decide(bash("cat > app/x.py", approved))[0] == "allow"
    assert gate_spec.decide(bash("echo x > app/x.py", quick))[0] == "allow"


def test_bash_reads_and_writes_outside_the_gated_area_are_allowed(tmp_path):
    """CRF-2: Given the gate is shut, when Bash only reads, or writes under .claude/, /dev/null, or outside the repository, then it is allowed."""
    shut = make_repo(tmp_path, "task", approved=False)

    actions = (
        gate_spec.decide(bash("rg foo", shut))[0],
        gate_spec.decide(bash("git status", shut))[0],
        gate_spec.decide(bash("git diff", shut))[0],
        gate_spec.decide(bash("ls > /dev/null", shut))[0],
        gate_spec.decide(bash("echo x > .claude/specs/s/notes.md", shut))[0],
        gate_spec.decide(bash("echo x > /tmp/out.txt", shut))[0],
        gate_spec.decide(bash('"%s/craft-spec" new --route task --title "A > B"' % BIN, shut))[0],
        gate_spec.decide(bash('"%s/craft-scenarios" add LIM-1 "Given a > b, when c, then d"' % BIN, shut))[0],
        gate_spec.decide(bash("rg foo # it's only a read", shut))[0],
        gate_spec.decide(bash("git restore --staged app/x.py", shut))[0],
        gate_spec.decide(bash("touch -d 2020-01-01 /tmp/stamp", shut))[0],
        gate_spec.decide(bash("perl -i.bak -pe 's/a/b/' /tmp/notes.txt", shut))[0],
        gate_spec.decide(bash("cd .claude/specs/s && cat > notes.md <<EOF\nx\nEOF", shut))[0],
        gate_spec.decide(bash("cd /tmp && echo x > out.txt", shut))[0],
        gate_spec.decide(bash('echo x > "$CRAFT_TEST_UNSET_DIR/x"', shut))[0],
        gate_spec.decide(bash("git commit -m 'document craft-approve'", shut))[0],
    )
    no_session = tmp_path / "no-session"
    no_session.mkdir()
    app_files = (
        protect_approval.decide(bash("cp fixtures/session.json /tmp/s.json", no_session))[0],
        protect_approval.decide(bash("git add config/session.json", no_session))[0],
        protect_approval.decide(bash("python3 manage.py loaddata fixtures/session.json", no_session))[0],
        protect_approval.decide(bash("cp fixtures/session.json /tmp/s.json", shut))[0],
        protect_approval.decide(bash("git add config/session.json", shut))[0],
        protect_approval.decide(bash("python3 manage.py loaddata fixtures/session.json", shut))[0],
        protect_approval.decide(bash("git add .claude/specs/ACTIVE .claude/specs/x/spec.md", shut))[0],
        protect_approval.decide(bash("cat .claude/specs/ACTIVE; python3 -m pytest -q", shut))[0],
    )
    messages = (
        protect_approval.decide(bash("git commit -m 'document craft-approve'", shut))[0],
        protect_approval.decide(bash("git commit -m one -m 'craft-approve two' && git tag -m craft-approve v1", shut))[0],
        protect_approval.decide(bash("python3 -m pytest tests -k craft_approve", shut))[0],
        protect_approval.decide(bash("python3 -m pytest tests -k craft-approve", shut))[0],
    )

    assert actions == ("allow",) * 16
    assert messages == ("allow",) * 4
    assert app_files == ("allow",) * 8


@NEEDS_GIT
def test_a_bash_call_that_changed_a_gated_file_is_reported(tmp_path):
    """CRF-3: Given the gate is shut in a git repository, when a Bash call creates app/new.py, then the after-hook names it and says to restore it; .claude/, ignored files, and an approved spec stay silent."""
    root = make_git_repo(tmp_path / "repo")

    assert gate_spec.decide(bash("python3 gen.py", root, "toolu_1"))[0] == "allow"
    assert gate_spec.decide(bash("python3 other.py", root, "toolu_2"))[0] == "allow"
    (root / "app" / "new.py").write_text("generated\n", encoding="utf-8")
    action, reason = gate_bash_after.decide(bash("python3 gen.py", root, "toolu_1"))
    parallel = gate_bash_after.decide(bash("python3 other.py", root, "toolu_2"))[0]

    assert gate_spec.decide(bash("python3 notes.py", root, "toolu_3"))[0] == "allow"
    (root / ".claude" / "notes.md").write_text("notes\n", encoding="utf-8")
    (root / "run.log").write_text("log\n", encoding="utf-8")
    quiet = gate_bash_after.decide(bash("python3 notes.py", root, "toolu_3"))

    assert gate_spec.decide(bash("python3 gen.py; false", root, "toolu_5"))[0] == "allow"
    (root / "app" / "x.py").write_text("half written\n", encoding="utf-8")
    failed = dict(bash("python3 gen.py; false", root, "toolu_5"), hook_event_name="PostToolUseFailure")
    failed_action, failed_reason = gate_bash_after.decide(failed)
    second_event = gate_bash_after.decide(dict(failed, hook_event_name="PostToolUse"))

    approve_spec(root)
    assert gate_spec.decide(bash("python3 edit.py", root, "toolu_4"))[0] == "allow"
    (root / "app" / "x.py").write_text("after\n", encoding="utf-8")
    approved = gate_bash_after.decide(bash("python3 edit.py", root, "toolu_4"))

    assert action == "report"
    assert "  app/new.py\n      rm %s/app/new.py" % root in reason
    assert "Restore each file now" in reason
    assert parallel == "report"
    assert failed_action == "report"
    assert "  app/x.py" in failed_reason
    assert second_event == ("allow", "")
    assert quiet == ("allow", "")
    assert approved == ("allow", "")


@NEEDS_GIT
def test_stop_is_refused_while_a_reported_file_still_differs(tmp_path):
    """CRF-4: Given a reported file still differs and the gate is shut, when Claude stops, then the stop is refused three times and names it; only a restoring write is allowed; uncommitted work is restored from a backup; a restore or an approval clears it."""
    new_file = make_git_repo(tmp_path / "new")
    gate_spec.decide(bash("python3 gen.py", new_file, "toolu_1"))
    (new_file / "app" / "new.py").write_text("generated\n", encoding="utf-8")
    gate_bash_after.decide(bash("python3 gen.py", new_file, "toolu_1"))
    first_action, first_reason = verify_gates.decide(stop(new_file, "I generated the file."))
    second = verify_gates.decide(stop(new_file, "I generated the file.", again=True))[0]
    third = verify_gates.decide(stop(new_file, "I generated the file.", again=True))[0]
    fourth_action, fourth_warning = verify_gates.decide(stop(new_file, "I generated the file.", again=True))
    other_content = gate_spec.decide(write(new_file / "app" / "new.py", new_file, content="other\n"))[0]
    removed = gate_spec.decide(bash("rm app/new.py", new_file, "toolu_2"))[0]

    restored = make_git_repo(tmp_path / "restored")
    gate_spec.decide(bash("python3 edit.py", restored, "toolu_1"))
    (restored / "app" / "x.py").write_text("after\n", encoding="utf-8")
    restored_report = gate_bash_after.decide(bash("python3 edit.py", restored, "toolu_1"))[1]
    restore_clean = "git restore --source=HEAD --staged --worktree -- %s/app/x.py" % restored
    restore_allowed = gate_spec.decide(bash(restore_clean, restored, "toolu_4"))[0]
    cat_over = gate_spec.decide(bash("cat > app/x.py <<EOF\nother\nEOF", restored, "toolu_2"))[0]
    edit_over = gate_spec.decide(write(restored / "app" / "x.py", restored, tool="Edit", content="before\n"))[0]
    write_back = gate_spec.decide(write(restored / "app" / "x.py", restored, content="before\n"))[0]
    checkout = gate_spec.decide(bash("git checkout -- app/x.py", restored, "toolu_3"))[0]
    (restored / "app" / "x.py").write_text("before\n", encoding="utf-8")

    dirty = make_git_repo(tmp_path / "dirty")
    (dirty / "app" / "x.py").write_text(DEV_WORK, encoding="utf-8")
    gate_spec.decide(bash("python3 edit.py", dirty, "toolu_1"))
    (dirty / "app" / "x.py").write_text("after\n", encoding="utf-8")
    dirty_action, dirty_report = gate_bash_after.decide(bash("python3 edit.py", dirty, "toolu_1"))
    backup = dirty / ".claude" / "craft" / "backups" / DEV_WORK_SHA
    copy_back = gate_spec.decide(bash("cp %s %s/app/x.py" % (backup, dirty), dirty, "toolu_2"))[0]
    checkout_dirty = gate_spec.decide(bash("git checkout -- app/x.py", dirty, "toolu_3"))[0]
    dirty_stop = verify_gates.decide(stop(dirty, "I changed the file."))[0]
    restore_dirty = "cp %s %s/app/x.py" % (backup, dirty)
    restore_absent = "rm %s/app/new.py" % new_file
    printed_restores = (
        protect_approval.decide(bash(restore_dirty, dirty, "toolu_5"))[0],
        gate_spec.decide(bash(restore_dirty, dirty, "toolu_5"))[0],
        protect_approval.decide(bash(restore_absent, new_file, "toolu_6"))[0],
        gate_spec.decide(bash(restore_absent, new_file, "toolu_6"))[0],
        protect_approval.decide(bash(restore_clean, restored, "toolu_7"))[0],
    )
    (dirty / "app" / "x.py").write_text(DEV_WORK, encoding="utf-8")

    big = make_git_repo(tmp_path / "big")
    (big / "app" / "x.py").write_text("y" * 1_100_000, encoding="utf-8")
    gate_spec.decide(bash("python3 edit.py", big, "toolu_1"))
    (big / "app" / "x.py").write_text("z" * 1_100_000, encoding="utf-8")
    big_report = gate_bash_after.decide(bash("python3 edit.py", big, "toolu_1"))[1]

    dollar = make_git_repo(tmp_path / "dollar")
    gate_spec.decide(bash("python3 gen.py", dollar, "toolu_1"))
    (dollar / "app" / "q$x.py").write_text("generated\n", encoding="utf-8")
    dollar_report = gate_bash_after.decide(bash("python3 gen.py", dollar, "toolu_1"))[1]
    dollar_restore = gate_spec.decide(bash("rm '%s/app/q$x.py'" % dollar, dollar, "toolu_2"))[0]

    many = make_git_repo(tmp_path / "many")
    commit_then_change(many, count=21, size=1_000_000)
    (many / "secret.env").write_text("TOKEN=untracked\n", encoding="utf-8")
    gate_spec.decide(bash("python3 gen.py", many, "toolu_1"))
    many_backups = sorted(path.name for path in (many / ".claude" / "craft" / "backups").iterdir())

    approved = make_git_repo(tmp_path / "approved")
    gate_spec.decide(bash("python3 edit.py", approved, "toolu_1"))
    (approved / "app" / "x.py").write_text("after\n", encoding="utf-8")
    gate_bash_after.decide(bash("python3 edit.py", approved, "toolu_1"))
    approve_spec(approved)
    after_approval = verify_gates.decide(stop(approved, "I edited the file."))[0]
    with open(str(approved / ".claude" / "specs" / SPEC_NAME / "spec.md"), "a", encoding="utf-8") as handle:
        handle.write("| LIM-2 | WHEN a delta is added. | BUSINESS RULE | x |\n")
    after_delta = verify_gates.decide(stop(approved, "I edited the file."))[0]

    assert first_action == "block"
    assert "  app/new.py\n      rm %s/app/new.py" % new_file in first_reason
    assert (second, third, fourth_action) == ("block", "block", "warn")
    assert "app/new.py" in fourth_warning
    assert (other_content, removed) == ("deny", "allow")
    assert (cat_over, edit_over, write_back, checkout) == ("deny", "deny", "allow", "allow")
    assert restore_clean in restored_report
    assert restore_allowed == "allow"
    assert verify_gates.decide(stop(restored, "I restored the file."))[0] == "allow"
    assert craft_state.read_session(str(restored)).get("gated_writes") == {}
    assert dirty_action == "report"
    assert restore_dirty in dirty_report
    assert restore_absent in first_reason
    assert printed_restores == ("allow",) * 5
    assert "git checkout" not in dirty_report
    assert backup.read_text(encoding="utf-8") == DEV_WORK
    assert (copy_back, checkout_dirty, dirty_stop) == ("allow", "deny", "block")
    assert verify_gates.decide(stop(dirty, "I restored the file."))[0] == "allow"
    assert list((dirty / ".claude" / "craft" / "backups").iterdir()) == []
    assert "no backup: an untracked file, a file over 1 MB" in big_report
    assert "rm '%s/app/q$x.py'" % dollar in dollar_report
    assert dollar_restore == "allow"
    assert len(many_backups) == 20
    assert "1f5d917226c75661574e7a66b9136cb72d0c673294edb6b8752a3c46b0d8c88e" not in many_backups
    assert verify_gates.decide(stop(big, "I edited the file."))[0] == "allow"
    assert (after_approval, after_delta) == ("allow", "allow")


def test_running_craft_approve_or_turning_hooks_off_is_denied_in_any_repository(tmp_path):
    """CRF-5: Given any repository, when Bash runs craft-approve, sets CRAFT_HOOKS, or a call turns hooks off another way, then it is denied with the developer's ! line; reading craft-approve is allowed."""
    bare = tmp_path / "bare"
    bare.mkdir()
    session = make_repo(tmp_path / "session", "task", approved=False)

    action, reason = protect_approval.decide(bash("/abs/bin/craft-approve", bare))
    denied = (
        protect_approval.decide(bash("python3 bin/craft-approve --scenarios", session))[0],
        protect_approval.decide(bash("cd x && craft-approve", bare))[0],
        protect_approval.decide(bash("CRAFT_HOOKS=off pytest", bare))[0],
        protect_approval.decide(bash("export CRAFT_HOOKS=off", session))[0],
        protect_approval.decide(bash("env CRAFT_HOOKS=off sh -c x", bare))[0],
        protect_approval.decide(bash("bin/craft-approve  # don't skip", bare))[0],
        protect_approval.decide(bash("eval 'bin/craft-approve'", bare))[0],
        protect_approval.decide(bash("echo bin/craft-approve | sh", bare))[0],
        protect_approval.decide(bash("if true; then bin/craft-approve; fi", bare))[0],
        protect_approval.decide(bash("{ bin/craft-approve; }", bare))[0],
        protect_approval.decide(bash("echo bin/craft-approve | xargs sh", bare))[0],
        protect_approval.decide(bash("sudo -u root bin/craft-approve", bare))[0],
        protect_approval.decide(bash("bin/craft-approve 'open quote", bare))[0],
    )
    allowed = (
        protect_approval.decide(bash("rg craft-approve skills/", bare))[0],
        protect_approval.decide(bash("cat bin/craft-approve", session))[0],
    )
    off_switches = (
        protect_approval.decide(write(".claude/settings.json", session, content='{"disableAllHooks": true}'))[0],
        protect_approval.decide(
            write(".claude/settings.local.json", session, tool="Edit", content='"env": {"CRAFT_HOOKS": "off"}')
        )[0],
        protect_approval.decide(bash("""echo '{"env": {"CRAFT_HOOKS": "off"}}' > .claude/settings.json""", session))[0],
        protect_approval.decide(bash("claude plugin disable craft-workflow", bare))[0],
        protect_approval.decide(bash("claude plugin uninstall craft-workflow", bare))[0],
        protect_approval.decide(write(PLUGIN_ROOT / "scripts" / "gate_spec.py", session))[0],
        protect_approval.decide(
            write(".claude/settings.json", session, content='{"enabledPlugins": {"craft-workflow@x": false}}')
        )[0],
        protect_approval.decide(bash("cp /tmp/s.json .claude/settings.local.json", session))[0],
        protect_approval.decide(write(".claude/settings.json", session, content='{"env": {"\\u0043RAFT_HOOKS": "off"}}'))[0],
        protect_approval.decide(bash("env X=1 claude plugin disable craft-workflow", bare))[0],
        protect_approval.decide(bash("claude plugin marketplace remove craft", bare))[0],
    )
    settings_without_keys = protect_approval.decide(write(".claude/settings.json", session, content='{"model": "opus"}'))[0]
    plugin_development = protect_approval.decide(write(PLUGIN_ROOT / "scripts" / "gate_spec.py", PLUGIN_ROOT))[0]

    assert action == "deny"
    assert APPROVE_LINE + "\n" in reason
    assert APPROVE_LINE + " --scenarios" in reason
    assert denied == ("deny",) * 13
    assert allowed == ("allow", "allow")
    assert off_switches == ("deny",) * 11
    assert (settings_without_keys, plugin_development) == ("allow", "allow")


def test_writes_to_the_approval_record_are_denied_and_undone(tmp_path):
    """CRF-6: Given an active session, when a tool call targets .claude/craft/approval.json, directly, as a directory, or through a symlink, then it is denied; a change by any other route is restored after the call."""
    root = make_repo(tmp_path / "repo", "task", approved=True)
    os.symlink(str(root / ".claude" / "craft"), str(tmp_path / "cc"))
    approval = root / ".claude" / "craft" / "approval.json"
    prior = approval.read_text(encoding="utf-8")
    prior_mode = approval.stat().st_mode & 0o777

    denied = (
        protect_approval.decide(write(".claude/craft/approval.json", root))[0],
        protect_approval.decide(write(root / ".claude" / "craft" / "approval.json", root, tool="Edit"))[0],
        protect_approval.decide(bash("echo {} > .claude/craft/approval.json", root))[0],
        protect_approval.decide(bash("cp x .claude/craft/approval.json", root))[0],
        protect_approval.decide(bash("cp /tmp/approval.json .claude/craft/", root))[0],
        protect_approval.decide(bash("mv /tmp/a .claude/craft", root))[0],
        protect_approval.decide(bash("cp -t .claude/craft /tmp/approval.json", root))[0],
        protect_approval.decide(write(tmp_path / "cc" / "approval.json", root))[0],
        protect_approval.decide(bash("echo {} > %s/approval.json" % (tmp_path / "cc"), root))[0],
    )
    allowed = protect_approval.decide(write(".claude/specs/s/spec.md", root))[0]
    gate_spec.decide(bash("cp /tmp/t .claude/craft/approval.*", root, "toolu_1"))
    approval.write_text('{"approvals": [{"kind": "spec", "spec": "forged"}]}', encoding="utf-8")
    action, reason = gate_bash_after.decide(bash("cp /tmp/t .claude/craft/approval.*", root, "toolu_1"))

    gate_spec.decide(bash("python3 forge.py; false", root, "toolu_2"))
    approval.write_text('{"approvals": []}', encoding="utf-8")
    failed = dict(bash("python3 forge.py; false", root, "toolu_2"), hook_event_name="PostToolUseFailure")
    failed_action = gate_bash_after.decide(failed)[0]
    failed_restored = approval.read_text(encoding="utf-8")

    gate_spec.decide(bash("chmod 0 x", root, "toolu_3"))
    approval.chmod(0)
    gate_bash_after.decide(bash("chmod 0 x", root, "toolu_3"))
    chmod_mode = approval.stat().st_mode & 0o777
    chmod_restored = approval.read_text(encoding="utf-8")
    gate_spec.decide(bash("python3 bytes.py", root, "toolu_4"))
    approval.write_bytes(b"\xff\xfe not utf-8")
    gate_bash_after.decide(bash("python3 bytes.py", root, "toolu_4"))
    bytes_restored = approval.read_text(encoding="utf-8")

    unreadable = make_repo(tmp_path / "unreadable", "task", approved=False)
    blocked = unreadable / ".claude" / "craft" / "approval.json"
    blocked.mkdir()
    gate_spec.decide(bash("python3 forge.py", unreadable, "toolu_1"))
    blocked.rmdir()
    blocked.write_text('{"approvals": [{"kind": "spec", "spec": "forged"}]}', encoding="utf-8")
    unreadable_action = gate_bash_after.decide(bash("python3 forge.py", unreadable, "toolu_1"))[0]

    created = make_repo(tmp_path / "created", "task", approved=False)
    gate_spec.decide(bash("python3 forge.py", created, "toolu_1"))
    (created / ".claude" / "craft" / "approval.json").write_text("{}", encoding="utf-8")
    gate_bash_after.decide(bash("python3 forge.py", created, "toolu_1"))

    assert denied == ("deny",) * 9
    assert allowed == "allow"
    assert action == "report"
    assert "forged approval reverted" in reason
    assert approval.read_text(encoding="utf-8") == prior
    assert not (created / ".claude" / "craft" / "approval.json").exists()
    assert (failed_action, failed_restored) == ("report", prior)
    assert (chmod_mode, chmod_restored) == (prior_mode, prior)
    assert bytes_restored == prior
    assert unreadable_action == "report"
    assert not blocked.exists()


def test_gate_denials_ask_the_developer_to_approve(tmp_path):
    """CRF-7: Given an unapproved spec or unapproved scenarios, when gate_spec denies, then the reason gives the developer's ! line or the board, and never tells Claude to run craft-approve."""
    spec = make_repo(tmp_path / "spec", "task", approved=False)
    scenarios = make_repo(tmp_path / "scenarios", "task", approved=True)

    spec_action, spec_reason = gate_spec.decide(write("app/x.py", spec))
    test_action, test_reason = gate_spec.decide(write("tests/test_limit.py", scenarios))

    assert (spec_action, test_action) == ("deny", "deny")
    assert APPROVE_LINE + "\n" in spec_reason
    assert "press `a` on the board" in spec_reason
    assert spec_reason.count("craft-approve") == spec_reason.count(APPROVE_LINE)
    assert APPROVE_LINE + " --scenarios" in test_reason
    assert test_reason.count("craft-approve") == test_reason.count(APPROVE_LINE)


def test_tool_writes_to_craft_state_files_are_denied(tmp_path):
    """CRF-24: Given an active session, when a tool call writes a .claude/craft state file or ACTIVE, or runs a bin subcommand that changes trusted state for Claude, then it is denied; the bin/ commands as programs are allowed."""
    root = make_repo(tmp_path / "repo", "task", approved=True)
    (root / ".claude" / "craft" / "findings.json").write_text(json.dumps({"findings": []}), encoding="utf-8")
    blocked = make_git_repo(tmp_path / "blocked")
    gate_spec.decide(bash("python3 gen.py", blocked, "toolu_1"))
    (blocked / "app" / "new.py").write_text("generated\n", encoding="utf-8")
    gate_bash_after.decide(bash("python3 gen.py", blocked, "toolu_1"))

    denied = (
        protect_approval.decide(write(".claude/craft/session.json", root))[0],
        protect_approval.decide(write(".claude/craft/findings.json", root, tool="Edit"))[0],
        protect_approval.decide(write(".claude/craft/reviews.json", root))[0],
        protect_approval.decide(bash("echo {} > .claude/craft/session.json", root))[0],
        protect_approval.decide(bash("sed -i s/task/quick/ .claude/craft/session.json", root))[0],
        protect_approval.decide(write(".claude/specs/ACTIVE", root))[0],
        protect_approval.decide(bash("echo old-spec > .claude/specs/ACTIVE", root))[0],
        protect_approval.decide(bash('"%s/craft-session" start --route quick' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-session" end' % BIN, blocked))[0],
        protect_approval.decide(bash('"%s/craft-spec" new --route task --title Other' % BIN, blocked))[0],
        protect_approval.decide(bash('"%s/craft-session" record-check --command pytest --exit-code 0' % BIN, root))[0],
        protect_approval.decide(bash("python3 scripts/craft_state.py record-check --command pytest --exit-code 0", root))[0],
        protect_approval.decide(bash('"%s/craft-session" finding F1 --state rejected' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-session" finding F1 --state confirmed' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-session" finding F1 --state plausible' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-session" finding F1 --state=proposed' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-session" finding F1 --state open' % BIN, root))[0],
        protect_approval.decide(bash("echo '{}' | python3 scripts/agent_gate.py", root))[0],
        protect_approval.decide(bash("python3 -c \"import craft_state; craft_state.record_spawn('reviewer')\"", root))[0],
        protect_approval.decide(bash(
            "python3 -c \"import json;p='.claude/craft/session.json';d=json.load(open(p));d['route']='quick';"
            "json.dump(d,open(p,'w'))\"", root))[0],
        protect_approval.decide(bash(
            "python3 -c \"import pathlib;pathlib.Path('.claude/craft/'+'session.json').write_text('{}')\"", root))[0],
        protect_approval.decide(bash("F=.claude/craft/session.json; sed -i s/task/quick/ $F", root))[0],
        protect_approval.decide(bash("F=.claude/craft/session.json; echo '{}' > $F", root))[0],
    )
    allowed = (
        protect_approval.decide(bash('"%s/craft-check" -- pytest' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-session" record-finding --id F1 --severity High' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-spec" new --route task --title Other' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-session" start --route task' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-session" end' % BIN, root))[0],
        protect_approval.decide(bash('"%s/craft-session" finding F1 --state fixed' % BIN, root))[0],
        protect_approval.decide(bash("jq . .claude/craft/session.json", root))[0],
        protect_approval.decide(bash("git commit -m 'explain the session.json route field'", root))[0],
    )

    assert denied == ("deny",) * 23
    assert allowed == ("allow",) * 8
