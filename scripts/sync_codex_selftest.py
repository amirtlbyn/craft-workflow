#!/usr/bin/env python3
"""sync_codex_selftest - prove bin/craft-sync-codex behaves correctly.

Run it standalone, from anywhere:

    python3 scripts/sync_codex_selftest.py
    python3 scripts/sync_codex_selftest.py --verbose

Two layers run, in this order:

  1. fixture   - a synthetic plugin tree (throwaway skills/, commands/,
                 agents/ under a temp directory, with a copy of
                 bin/craft-sync-codex placed so PLUGIN_ROOT resolves to that
                 temp directory) exercised as a real subprocess, so behavior
                 is checked against controlled input rather than today's
                 exact skill/command count in this repository. That keeps
                 this test from breaking every time a skill is added.
  2. smoke     - one end-to-end run against this actual repository, checking
                 only that it succeeds and produces output, not exact counts.

Exit code 0 when every case passes, 1 otherwise.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

try:
    import tomllib
except ModuleNotFoundError:
    # tomllib joined the standard library in Python 3.11. Keep shell runners
    # on Python 3.10 compatible through the API-compatible backport, and when
    # that is not installed either (a runner with no pip), skip only the TOML
    # parse case instead of failing the whole self-test.
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
SYNC_SCRIPT = PLUGIN_ROOT / "bin" / "craft-sync-codex"

VERBOSE = "--verbose" in sys.argv

results = []
temporary_roots = []


def check(group, name, actual, expected):
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


def check_true(group, name, condition, detail=""):
    results.append(
        {
            "group": group,
            "name": name,
            "expected": "true",
            "actual": (
                "true" if condition else ("false: %s" % detail if detail else "false")
            ),
            "passed": bool(condition),
        }
    )
    return condition


# ---------------------------------------------------------------------------
# Fixture plumbing
# ---------------------------------------------------------------------------


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_fixture_root():
    """A throwaway plugin tree: bin/craft-sync-codex plus synthetic
    skills/, commands/, agents/. PLUGIN_ROOT inside the copied script
    resolves to this directory, since it is script.parent.parent."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="sync-codex-selftest-"))
    temporary_roots.append(root)
    bin_dir = root / "bin"
    bin_dir.mkdir()
    copy = bin_dir / "craft-sync-codex"
    shutil.copy2(SYNC_SCRIPT, copy)
    copy.chmod(0o755)

    write(
        root / "skills" / "alpha" / "SKILL.md",
        '---\nname: alpha\ndescription: "A single-line description."\n---\n\n'
        "# alpha\n\nBody text.\n",
    )
    write(
        root / "skills" / "beta" / "SKILL.md",
        "---\nname: beta\ndescription: >\n  A folded description\n"
        "  across two lines.\n---\n\n# beta\n\nBody text.\n",
    )
    write(root / "skills" / "beta" / "references" / "notes.md", "reference content\n")
    write(
        root / "commands" / "go.md",
        "---\ndescription: Run the thing\nargument-hint: <target>\n---\n\nDo the thing.\n",
    )
    write(
        root / "commands" / "alpha.md",
        "---\ndescription: Should be skipped, alpha is already a skill\n---\n\nUnused.\n",
    )
    write(
        root / "agents" / "writer.md",
        "---\nname: writer\ndescription: Writes files.\n"
        "tools: Read, Edit, Write, Bash\nmodel: sonnet\n---\n\nWrite things.\n",
    )
    write(
        root / "agents" / "reader.md",
        "---\nname: reader\ndescription: Reads files only.\n"
        "tools: Read, Grep, Glob, Bash\nmodel: haiku\n---\n\nRead things.\n",
    )
    return root


def run(root, *args):
    return subprocess.run(
        [str(root / "bin" / "craft-sync-codex")] + list(args),
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_write_produces_expected_files():
    group = "write"
    root = make_fixture_root()
    result = run(root, "--write")
    check(group, "exit code", result.returncode, 0)

    check_true(
        group,
        "skill alpha generated",
        (root / ".agents" / "skills" / "alpha" / "SKILL.md").is_file(),
    )
    check_true(
        group,
        "skill beta generated",
        (root / ".agents" / "skills" / "beta" / "SKILL.md").is_file(),
    )
    check_true(
        group,
        "beta's references/ copied alongside it",
        (root / ".agents" / "skills" / "beta" / "references" / "notes.md").is_file(),
    )

    beta_text = (root / ".agents" / "skills" / "beta" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    check_true(
        group,
        "folded 'description: >' is joined into one frontmatter line",
        "A folded description across two lines." in beta_text,
        beta_text,
    )

    check_true(
        group,
        "command go.md becomes a generated skill",
        (root / ".agents" / "skills" / "go" / "SKILL.md").is_file(),
    )
    go_text = (root / ".agents" / "skills" / "go" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    check_true(
        group,
        "argument-hint is folded into the description, not dropped",
        "<target>" in go_text,
        go_text,
    )

    check_true(
        group,
        "command alpha.md does NOT produce a duplicate (collision with skill alpha)",
        not (root / ".agents" / "skills" / "alpha" / "SKILL.md")
        .read_text(encoding="utf-8")
        .startswith("<!-- GENERATED by bin/craft-sync-codex from commands/"),
    )

    writer_toml = (root / ".codex" / "agents" / "writer.toml").read_text(
        encoding="utf-8"
    )
    check_true(
        group,
        "writer (has Edit+Write) is workspace-write",
        'sandbox_mode = "workspace-write"' in writer_toml,
    )
    check_true(group, "writer.toml has no model key", "model =" not in writer_toml)

    reader_toml = (root / ".codex" / "agents" / "reader.toml").read_text(
        encoding="utf-8"
    )
    check_true(
        group,
        "reader (no Edit/Write) is read-only",
        'sandbox_mode = "read-only"' in reader_toml,
    )

    check_true(group, "AGENTS.md generated", (root / "AGENTS.md").is_file())


def snapshot_all_outputs(root):
    """Every file under all three output roots -- .agents/, .codex/, and
    AGENTS.md -- not just .agents/. The read-only claim for --check covers
    all of them, and craft-doctor relies on that being true of all three."""
    snapshot = {}
    for base in (root / ".agents", root / ".codex"):
        snapshot.update({p: p.read_bytes() for p in base.rglob("*") if p.is_file()})
    agents_md = root / "AGENTS.md"
    if agents_md.is_file():
        snapshot[agents_md] = agents_md.read_bytes()
    return snapshot


def test_check_is_read_only_and_clean_after_write():
    group = "check"
    root = make_fixture_root()
    run(root, "--write")
    before = snapshot_all_outputs(root)
    result = run(root)  # default mode: --check
    check(group, "exit code on a freshly written tree", result.returncode, 0)
    after = snapshot_all_outputs(root)
    check_true(
        group,
        "check mode did not modify any file under .agents/, .codex/, or AGENTS.md",
        before == after,
    )


def test_check_reports_missing_before_write():
    group = "check"
    root = make_fixture_root()
    result = run(root)
    check(group, "exit code before any --write", result.returncode, 1)
    check_true(group, "missing files are named", "missing" in result.stdout)


def test_write_is_idempotent():
    group = "idempotent"
    root = make_fixture_root()
    run(root, "--write")
    first = snapshot_all_outputs(root)
    run(root, "--write")
    second = snapshot_all_outputs(root)
    check_true(
        group, "running --write twice produces byte-identical output", first == second
    )


def test_check_detects_hand_edit():
    group = "drift"
    root = make_fixture_root()
    run(root, "--write")
    target = root / ".agents" / "skills" / "alpha" / "SKILL.md"
    target.write_text(
        target.read_text(encoding="utf-8") + "\nhand-edited\n", encoding="utf-8"
    )
    result = run(root)
    check(group, "exit code with a hand-edited generated file", result.returncode, 1)
    check_true(
        group,
        "the stale file is named in the report",
        "skills/alpha/SKILL.md" in result.stdout and "stale" in result.stdout,
        result.stdout,
    )


def fail_lines(stdout):
    return [line for line in stdout.splitlines() if line.startswith("[FAIL]")]


def test_check_detects_orphan():
    group = "drift"
    root = make_fixture_root()
    run(root, "--write")
    shutil.rmtree(root / "skills" / "beta")
    result = run(root)
    check(group, "exit code after removing a skill's source", result.returncode, 1)
    check_true(
        group,
        "the orphaned generated file is reported",
        "beta" in result.stdout,
        result.stdout,
    )
    run(root, "--write")
    check_true(
        group,
        "--write removes the orphan",
        not (root / ".agents" / "skills" / "beta").exists(),
    )


def test_resource_subdir_orphan_detected_and_removed():
    group = "drift"
    root = make_fixture_root()
    run(root, "--write")
    check_true(
        group,
        "beta's references/ exists before its source is removed",
        (root / ".agents" / "skills" / "beta" / "references" / "notes.md").is_file(),
    )

    # Remove only the resource subdirectory's source, not the skill itself --
    # beta/SKILL.md's own source is untouched.
    shutil.rmtree(root / "skills" / "beta" / "references")
    result = run(root)
    check(
        group,
        "exit code after removing only a skill's resource subdirectory",
        result.returncode,
        1,
    )
    fails = fail_lines(result.stdout)
    check_true(
        group,
        "the orphaned resource directory is reported as a FAIL",
        any("beta/references" in line for line in fails),
        result.stdout,
    )
    check_true(
        group,
        "beta/SKILL.md itself is not flagged -- only its removed resource dir is",
        not any("beta/SKILL.md" in line for line in fails),
        result.stdout,
    )

    run(root, "--write")
    check_true(
        group,
        "--write removes only the orphaned resource directory, keeping SKILL.md",
        not (root / ".agents" / "skills" / "beta" / "references").exists()
        and (root / ".agents" / "skills" / "beta" / "SKILL.md").is_file(),
    )


def test_symlink_orphan_removed_without_crashing():
    group = "drift"
    root = make_fixture_root()
    run(root, "--write")
    target_dir = pathlib.Path(
        tempfile.mkdtemp(prefix="sync-codex-selftest-symlink-target-")
    )
    temporary_roots.append(target_dir)
    symlink_path = root / ".agents" / "skills" / "orphan-symlink"
    try:
        symlink_path.symlink_to(target_dir, target_is_directory=True)
    except OSError as error:
        # report() only prints PASS/FAIL, so a real skip must say so in its
        # own name -- otherwise it reads as a passing case that never ran.
        check_true(
            group,
            "symlink orphan case SKIPPED (filesystem has no symlink support: %s)"
            % error,
            True,
        )
        return

    result = run(root)
    check(group, "exit code with a symlinked orphan present", result.returncode, 1)

    write_result = run(root, "--write")
    check(group, "exit code removing a symlinked orphan", write_result.returncode, 0)
    check_true(
        group,
        "the symlink is gone -- shutil.rmtree would have raised on it -- and its"
        " target directory is untouched",
        not symlink_path.is_symlink() and target_dir.is_dir(),
        write_result.stdout + write_result.stderr,
    )


def test_malformed_skill_source_not_reported_as_orphan():
    group = "malformed source"
    root = make_fixture_root()
    run(root, "--write")

    # Break alpha's source without deleting it: drop its description field.
    (root / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\n---\n\n# alpha\n\nBody text.\n", encoding="utf-8"
    )
    result = run(root)
    check(
        group, "exit code with alpha's source broken, not deleted", result.returncode, 1
    )
    fails = fail_lines(result.stdout)
    check_true(
        group,
        "the real cause -- a parse failure -- is reported under the source group",
        any(line.startswith("[FAIL] source") and "alpha" in line for line in fails),
        result.stdout,
    )
    check_true(
        group,
        "alpha's still-valid output is NOT also reported as an orphan -- that"
        " advice ('remove it or run --write') cannot work while --write refuses"
        " to run at all until the source error is fixed",
        not any(line.startswith("[FAIL] orphan") and "alpha" in line for line in fails),
        result.stdout,
    )


def test_malformed_agent_source_with_readable_name_not_reported_as_orphan():
    group = "malformed source"
    root = make_fixture_root()
    run(root, "--write")

    # Break writer's source without deleting it: drop its description field,
    # but leave 'name' readable -- the common case, since a real edit is far
    # more likely to lose one field than the whole frontmatter block.
    (root / "agents" / "writer.md").write_text(
        "---\nname: writer\ntools: Read, Edit, Write\n---\n\nWrite things.\n",
        encoding="utf-8",
    )
    result = run(root)
    check(
        group,
        "exit code with writer's source broken, not deleted, name still readable",
        result.returncode,
        1,
    )
    fails = fail_lines(result.stdout)
    check_true(
        group,
        "the real cause is reported under the source group",
        any(line.startswith("[FAIL] source") and "writer.md" in line for line in fails),
        result.stdout,
    )
    check_true(
        group,
        "writer.toml's still-valid output is NOT also reported as an orphan,"
        " even though its generated name (writer) does not match its source"
        " file's own name",
        not any(
            line.startswith("[FAIL] orphan") and "writer" in line for line in fails
        ),
        result.stdout,
    )


def test_symlinked_resource_directory_replaced_without_crashing():
    group = "drift"
    root = make_fixture_root()
    run(root, "--write")
    generated_references = root / ".agents" / "skills" / "beta" / "references"
    shutil.rmtree(generated_references)
    target_dir = pathlib.Path(
        tempfile.mkdtemp(prefix="sync-codex-selftest-resource-symlink-target-")
    )
    temporary_roots.append(target_dir)
    try:
        generated_references.symlink_to(target_dir, target_is_directory=True)
    except OSError as error:
        check_true(
            group,
            "symlinked resource directory case SKIPPED (filesystem has no"
            " symlink support: %s)" % error,
            True,
        )
        return

    result = run(root, "--write")
    check(
        group,
        "exit code replacing a symlinked resource directory with a fresh copy",
        result.returncode,
        0,
    )
    check_true(
        group,
        "the symlink is replaced by a real directory holding the source's files",
        generated_references.is_dir()
        and not generated_references.is_symlink()
        and (generated_references / "notes.md").is_file(),
        result.stdout + result.stderr,
    )


def test_malformed_source_fails_loudly():
    group = "malformed source"
    root = make_fixture_root()
    write(
        root / "agents" / "broken.md",
        "---\nname: broken\ntools: Read\n---\n\nno description field.\n",
    )
    result = run(root, "--write")
    check(group, "exit code with a source missing 'description'", result.returncode, 1)
    check_true(
        group,
        "broken.md is named as the failing source, and nothing else was written",
        "broken.md" in result.stdout
        and "missing required frontmatter field" in result.stdout,
        result.stdout,
    )
    check_true(
        group,
        "a malformed source blocks the whole write, not just its own file",
        not (root / ".agents" / "skills" / "alpha").exists(),
    )


def test_duplicate_agent_name_fails_loudly():
    group = "malformed source"
    root = make_fixture_root()
    write(
        root / "agents" / "writer2.md",
        "---\nname: writer\ndescription: A second file declaring the same name.\n"
        "tools: Read, Edit, Write\nmodel: sonnet\n---\n\nAlso writes things.\n",
    )
    result = run(root, "--write")
    check(
        group,
        "exit code with two agent sources declaring the same frontmatter name",
        result.returncode,
        1,
    )
    check_true(
        group,
        "the collision names the second source and that a name was already planned",
        "writer2.md" in result.stdout and "already planned" in result.stdout,
        result.stdout,
    )
    check_true(
        group,
        "a name collision blocks the whole write -- nothing under .codex/ is written",
        not (root / ".codex").exists(),
    )


def test_toml_agent_body_with_backslash_round_trips():
    group = "toml escaping"
    root = make_fixture_root()
    write(
        root / "agents" / "grepper.md",
        "---\nname: grepper\ndescription: Uses regexes.\n"
        "tools: Read, Grep, Bash\nmodel: haiku\n---\n\n"
        'Run `rg -n "\\d+"` and read `C:\\Users\\dev\\notes.txt`.\n',
    )
    result = run(root, "--write")
    check(group, "exit code with a backslash in an agent body", result.returncode, 0)

    toml_path = root / ".codex" / "agents" / "grepper.toml"
    check_true(group, "grepper.toml was written", toml_path.is_file())
    if not toml_path.is_file():
        return

    if tomllib is None:
        check_true(
            group,
            "TOML parse case SKIPPED (Python %d.%d has no tomllib and tomli is"
            " not installed)" % sys.version_info[:2],
            True,
        )
        return

    try:
        parsed = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        parse_error = None
    except tomllib.TOMLDecodeError as error:
        parsed = None
        parse_error = str(error)
    check_true(
        group,
        "the generated TOML parses with tomllib",
        parsed is not None,
        parse_error or "",
    )
    if parsed is not None:
        check(
            group,
            "developer_instructions round-trips the backslashes and quote exactly",
            parsed.get("developer_instructions", "").strip(),
            'Run `rg -n "\\d+"` and read `C:\\Users\\dev\\notes.txt`.',
        )


def test_double_quoted_description_unescapes_correctly():
    group = "yaml unescape"
    root = make_fixture_root()
    write(
        root / "skills" / "gamma" / "SKILL.md",
        "---\nname: gamma\ndescription: "
        '"Trigger on \\"write a PRD\\" requests, or a literal backslash \\\\ in text."'
        "\n---\n\n# gamma\n\nBody text.\n",
    )
    result = run(root, "--write")
    check(
        group,
        "exit code with an escaped quote and an escaped backslash in a description",
        result.returncode,
        0,
    )
    gamma_text = (root / ".agents" / "skills" / "gamma" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    # The source is escaped once (valid YAML). Re-serializing an already-correct
    # description must also escape it exactly once, not re-escape the escape.
    check_true(
        group,
        "the escaped quote is re-escaped exactly once, not doubled",
        r"\"write a PRD\"" in gamma_text and r"\\\"write a PRD\\\"" not in gamma_text,
        gamma_text,
    )
    check_true(
        group,
        "the escaped backslash survives as exactly one backslash, not four",
        r"backslash \\ in text" in gamma_text
        and r"backslash \\\\ in text" not in gamma_text,
        gamma_text,
    )


def test_smoke_against_real_repository():
    group = "smoke (real repository)"
    # Whether this repository's own generated output happens to be up to
    # date right now is craft-doctor's job (its 'codex' check group), not
    # this self-test's. This case instead copies the two real skills whose
    # "description: >" folded scalar spans several real lines -- planner and
    # system-design -- into a fresh fixture and regenerates them there. That
    # exercises the actual parser against their actual source, rather than
    # reading a previously committed artifact (which proves nothing about
    # whether the parser still works) or a quoted phrase (which breaks on an
    # ordinary prose edit unrelated to the generator).
    root = pathlib.Path(tempfile.mkdtemp(prefix="sync-codex-selftest-realskills-"))
    temporary_roots.append(root)
    bin_dir = root / "bin"
    bin_dir.mkdir()
    copy = bin_dir / "craft-sync-codex"
    shutil.copy2(SYNC_SCRIPT, copy)
    copy.chmod(0o755)

    for skill_name in ("planner", "system-design"):
        source = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
        check_true(
            group,
            "%s/SKILL.md exists in this repository's real skills/" % skill_name,
            source.is_file(),
        )
        if source.is_file():
            write(
                root / "skills" / skill_name / "SKILL.md",
                source.read_text(encoding="utf-8"),
            )

    result = run(root, "--write")
    check(
        group,
        "exit code writing the two real folded-description skills",
        result.returncode,
        0,
    )

    for skill_name in ("planner", "system-design"):
        generated = root / ".agents" / "skills" / skill_name / "SKILL.md"
        check_true(group, "%s/SKILL.md was generated" % skill_name, generated.is_file())
        if not generated.is_file():
            continue
        text = generated.read_text(encoding="utf-8")
        description_lines = [
            line
            for line in text.split("---")[1].splitlines()
            if line.startswith("description:")
        ]
        check(
            group,
            "%s frontmatter has exactly one 'description:' line" % skill_name,
            len(description_lines),
            1,
        )
        source_text = (PLUGIN_ROOT / "skills" / skill_name / "SKILL.md").read_text(
            encoding="utf-8"
        )
        longest_source_line = max(
            (len(line) for line in source_text.splitlines()), default=0
        )
        joined_length = len(description_lines[0]) if description_lines else 0
        check_true(
            group,
            "%s's folded description is longer than any single source line --"
            " proof the fold actually joined several lines, not just copied"
            " one" % skill_name,
            bool(description_lines) and joined_length > longest_source_line,
            "joined length %d vs longest source line %d"
            % (joined_length, longest_source_line),
        )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def report():
    width = 4
    for result in results:
        width = max(width, len(result["name"]))
    width = min(width, 64)

    current = None
    for result in results:
        if result["group"] != current:
            current = result["group"]
            print("")
            print(current)
        if result["passed"]:
            print("  PASS  %-*s" % (width, result["name"]))
        else:
            print(
                "  FAIL  %-*s  got %s, expected %s"
                % (width, result["name"], result["actual"], result["expected"])
            )

    passed = sum(1 for result in results if result["passed"])
    failed = len(results) - passed
    print("")
    print("%d passed, %d failed" % (passed, failed))
    return failed


def main():
    print("sync_codex self-test")
    print("  sync script  %s" % SYNC_SCRIPT)
    print("  python       %s" % sys.version.split()[0])
    try:
        test_write_produces_expected_files()
        test_check_is_read_only_and_clean_after_write()
        test_check_reports_missing_before_write()
        test_write_is_idempotent()
        test_check_detects_hand_edit()
        test_check_detects_orphan()
        test_resource_subdir_orphan_detected_and_removed()
        test_symlink_orphan_removed_without_crashing()
        test_symlinked_resource_directory_replaced_without_crashing()
        test_malformed_skill_source_not_reported_as_orphan()
        test_malformed_agent_source_with_readable_name_not_reported_as_orphan()
        test_malformed_source_fails_loudly()
        test_duplicate_agent_name_fails_loudly()
        test_toml_agent_body_with_backslash_round_trips()
        test_double_quoted_description_unescapes_correctly()
        test_smoke_against_real_repository()
        failed = report()
    finally:
        for root in temporary_roots:
            shutil.rmtree(str(root), ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
