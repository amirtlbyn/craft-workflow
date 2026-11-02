"""Tests for the layered standards of bin/craft-std, one per acceptance criterion of the STD spec."""

import json
import pathlib
import re
import shutil
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
STD = PLUGIN_ROOT / "bin" / "craft-std"
DOCTOR = PLUGIN_ROOT / "bin" / "craft-doctor"


def run(script, args, cwd, tmp_path, xdg=None):
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "config") if xdg is None else xdg,
    }
    return subprocess.run(
        [sys.executable, str(script)] + args,
        cwd=str(cwd), env=env, capture_output=True, text=True,
    )


def std(args, cwd, tmp_path, xdg=None):
    return run(STD, args, cwd, tmp_path, xdg)


def make_repo(tmp_path, remote=None):
    repo = tmp_path / "work" / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
    if remote:
        subprocess.run(["git", "remote", "add", "origin", remote], cwd=str(repo), check=True)
    return repo


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def standard(title, body):
    return "# Doc\n\n## %s\n\n%s\n" % (title, body)


def profile_dir(tmp_path, name):
    return tmp_path / "config" / "craft-workflow" / "profiles" / name


def profiles_json(tmp_path, rules):
    write(tmp_path / "config" / "craft-workflow" / "profiles.json", json.dumps({"rules": rules}))


def test_project_file_replaces_the_plugin_file(tmp_path):
    """STD-1: Given a project and a plugin standard of one name, when a section is read, then only the project file answers."""
    repo = make_repo(tmp_path)
    write(repo / "aidocs" / "django_standards.human.md", standard("Views", "PROJECT-VIEWS-RULE"))
    result = std(["django", "Views"], repo, tmp_path)
    assert result.returncode == 0 and "PROJECT-VIEWS-RULE" in result.stdout
    assert "Django logic" not in result.stdout
    (repo / "sub").mkdir()
    assert "PROJECT-VIEWS-RULE" in std(["django", "Views"], repo / "sub", tmp_path).stdout
    missing = std(["django", "Django logic"], repo, tmp_path)
    assert missing.returncode == 1 and "Views" in missing.stdout
    plain = tmp_path / "plain"
    write(plain / "aidocs" / "django_standards.md", standard("Views", "PLAIN-DIR-RULE"))
    assert "PLAIN-DIR-RULE" in std(["django", "Views"], plain, tmp_path).stdout


def test_profile_then_plugin_fill_missing_names(tmp_path):
    """STD-2: Given a profile, when the project lacks a name, then the profile answers, else the plugin."""
    repo = make_repo(tmp_path)
    write(repo / "aidocs" / "craft.json", '{"profile": "tabdeal"}')
    write(profile_dir(tmp_path, "tabdeal") / "python_code_style.human.md", standard("Naming", "PROFILE-NAMING"))
    assert "PROFILE-NAMING" in std(["python_code_style", "Naming"], repo, tmp_path).stdout
    listing = std(["go_standards", "--list"], repo, tmp_path)
    assert listing.returncode == 0 and "plugin" in listing.stdout
    write(profile_dir(tmp_path, "tabdeal") / "django_standards.human.md", standard("Views", "PROFILE-VIEWS"))
    write(repo / "aidocs" / "django_standards.human.md", standard("Views", "PROJECT-VIEWS"))
    assert "PROJECT-VIEWS" in std(["django", "Views"], repo, tmp_path).stdout


def test_human_file_beats_ai_file_within_a_layer(tmp_path):
    """STD-3: Given .human.md and .ai.md in one layer, when listed, then .human.md wins; across layers the closer layer wins."""
    repo = make_repo(tmp_path)
    write(repo / "aidocs" / "django_standards.ai.md", standard("Bot", "x"))
    write(repo / "aidocs" / "django_standards.human.md", standard("Team", "x"))
    listing = std(["django", "--list"], repo, tmp_path).stdout
    assert "django_standards.human.md" in listing and "django_standards.ai.md" not in listing
    fake_plugin = tmp_path / "plugin"
    (fake_plugin / "bin").mkdir(parents=True)
    shutil.copy(str(STD), str(fake_plugin / "bin" / "craft-std"))
    write(fake_plugin / "standards" / "x.human.md", standard("PluginHuman", "x"))
    other = make_repo(tmp_path / "o")
    write(other / "aidocs" / "craft.json", '{"profile": "p"}')
    write(profile_dir(tmp_path, "p") / "x.ai.md", standard("ProfileBot", "x"))
    layered = run(fake_plugin / "bin" / "craft-std", ["x", "--list"], other, tmp_path).stdout
    assert "ProfileBot" in layered and "PluginHuman" not in layered


def test_project_only_standard_is_listed_and_readable(tmp_path):
    """STD-4: Given aidocs/INVARIANTS.human.md, when listed and read, then it appears; README and subdirectories do not."""
    repo = make_repo(tmp_path)
    write(repo / "aidocs" / "INVARIANTS.human.md", standard("Money", "INVARIANT-MONEY"))
    write(repo / "aidocs" / "README.md", standard("Readme", "x"))
    write(repo / "aidocs" / "sub" / "deep.md", standard("Deep", "x"))
    listing = std(["--list"], repo, tmp_path).stdout
    assert "INVARIANTS  (INVARIANTS.human.md" in listing and "project" in listing
    assert "README" not in listing and "deep" not in listing
    assert "INVARIANT-MONEY" in std(["INVARIANTS", "Money"], repo, tmp_path).stdout
    write(repo / "aidocs" / "django_models.md", standard("Fields", "MODELS-FIELDS"))
    base = std(["django", "Django logic"], repo, tmp_path)
    assert base.returncode == 0 and "django_standards" in base.stdout
    assert "MODELS-FIELDS" in std(["django_m", "Fields"], repo, tmp_path).stdout


def test_profiles_json_rules_pick_the_first_match(tmp_path):
    """STD-5: Given profiles.json rules, when --where runs, then the first matching remote or path rule selects the profile."""
    repo = make_repo(tmp_path, "git@gitlab.tabdeal.ir:core/exchange.git")
    profile_dir(tmp_path, "tabdeal").mkdir(parents=True)
    profile_dir(tmp_path, "personal").mkdir(parents=True)
    profiles_json(tmp_path, [{"remote": "*gitlab.tabdeal*", "profile": "tabdeal"}])
    where = std(["--where"], repo, tmp_path).stdout
    assert "profile: tabdeal" in where and "rule 1" in where
    profiles_json(tmp_path, [{"path": str(tmp_path / "work") + "/*", "profile": "personal"},
                             {"remote": "*gitlab.tabdeal*", "profile": "tabdeal"}])
    assert "profile: personal" in std(["--where"], repo, tmp_path).stdout
    bare = make_repo(tmp_path / "b")
    profiles_json(tmp_path, [{"remote": "*gitlab.tabdeal*", "profile": "tabdeal"}])
    quiet = std(["--where"], bare, tmp_path)
    assert "profile: none" in quiet.stdout and quiet.stderr == ""
    home_config = tmp_path / "home" / ".config" / "craft-workflow"
    (home_config / "profiles" / "home").mkdir(parents=True)
    write(home_config / "profiles.json", json.dumps({"rules": [{"path": "*", "profile": "home"}]}))
    relative = std(["--where"], repo, tmp_path, xdg="relative/dir")
    assert "profile: home" in relative.stdout


def test_craft_json_overrides_profiles_json(tmp_path):
    """STD-6: Given aidocs/craft.json naming a profile, when it runs, then that profile wins over profiles.json."""
    repo = make_repo(tmp_path, "git@gitlab.tabdeal.ir:core/exchange.git")
    profile_dir(tmp_path, "tabdeal").mkdir(parents=True)
    profile_dir(tmp_path, "personal").mkdir(parents=True)
    profiles_json(tmp_path, [{"remote": "*tabdeal*", "profile": "tabdeal"}])
    write(repo / "aidocs" / "craft.json", '{"profile": "personal"}')
    where = std(["--where"], repo, tmp_path).stdout
    assert "profile: personal" in where and "source: aidocs/craft.json" in where
    write(repo / "aidocs" / "craft.json", "{}")
    assert "profile: tabdeal" in std(["--where"], repo, tmp_path).stdout
    write(repo / "aidocs" / "craft.json", '{"profile": null}')
    nulled = std(["--where"], repo, tmp_path)
    assert "profile: tabdeal" in nulled.stdout and nulled.stderr == ""


def test_profile_problems_warn_once_and_keep_answering(tmp_path):
    """STD-7: Given a bad profile name, missing directory, or broken JSON, when it runs, then one warning and the other layers answer."""
    repo = make_repo(tmp_path)
    write(repo / "aidocs" / "INVARIANTS.md", standard("Money", "x"))
    for bad in ("../../etc", "Upper", "a/b", "tabdeal\n"):
        write(repo / "aidocs" / "craft.json", json.dumps({"profile": bad}))
        result = std(["--list"], repo, tmp_path)
        assert result.returncode == 0 and result.stderr.count("warning") == 1
        assert "INVARIANTS" in result.stdout and "django_standards" in result.stdout
    outside = tmp_path / "outside.md"
    write(outside, standard("Secret", "OUTSIDE-SECRET"))
    (repo / "aidocs" / "evil.md").symlink_to(outside)
    linked = std(["--list"], repo, tmp_path)
    assert "evil" not in linked.stdout and "OUTSIDE-SECRET" not in linked.stdout
    assert "OUTSIDE-SECRET" not in std(["evil", "Secret"], repo, tmp_path).stdout
    write(repo / "aidocs" / "craft.json", '{"profile": "ghost"}')
    ghost = std(["--list"], repo, tmp_path)
    assert ghost.stderr.count("warning") == 1 and "ghost" in ghost.stderr and ghost.returncode == 0
    write(repo / "aidocs" / "craft.json", "{not json")
    profile_dir(tmp_path, "tabdeal").mkdir(parents=True)
    profiles_json(tmp_path, [{"path": "*", "profile": "tabdeal"}])
    fallback = std(["--where"], repo, tmp_path)
    assert fallback.stderr.count("warning") == 1 and "profile: tabdeal" in fallback.stdout
    (repo / "aidocs" / "craft.json").unlink()
    write(tmp_path / "config" / "craft-workflow" / "profiles.json", "{broken")
    broken = std(["--list"], repo, tmp_path)
    assert broken.stderr.count("warning") == 1 and "profiles.json" in broken.stderr and broken.returncode == 0
    profiles_json(tmp_path, [{"remote": "a", "path": "b", "profile": "tabdeal"},
                             {"path": "*", "profile": 3}, {"path": "*", "profile": "tabdeal"}])
    skipped = std(["--where"], repo, tmp_path)
    assert skipped.stderr.count("warning") == 2 and "profile: tabdeal" in skipped.stdout


def test_where_and_list_name_the_layers(tmp_path):
    """STD-8: Given files in all layers, when --where and --list run, then layers, profile, source, and file layers are printed."""
    repo = make_repo(tmp_path, "git@gitlab.tabdeal.ir:core/exchange.git")
    profile_dir(tmp_path, "tabdeal").mkdir(parents=True)
    profiles_json(tmp_path, [{"remote": "*tabdeal*", "profile": "tabdeal"}])
    write(repo / "aidocs" / "django_standards.human.md", standard("Views", "x"))
    write(profile_dir(tmp_path, "tabdeal") / "go_standards.human.md", standard("Errors", "x"))
    where = std(["--where"], repo, tmp_path).stdout
    assert "(exists)" in where and "profile: tabdeal" in where and "remote *tabdeal*" in where
    listing = std(["--list"], repo, tmp_path).stdout
    assert "django_standards.human.md, " in listing and ", project)" in listing
    assert ", profile tabdeal)" in listing and ", plugin)" in listing
    assert "django_standards.ai.md" not in listing
    none = std(["--where"], make_repo(tmp_path / "n"), tmp_path).stdout
    assert "profile: none" in none and "not selected" in none


def test_init_copies_without_overwriting(tmp_path):
    """STD-9: Given a Django repo, when init runs, then it writes .ai.md copies, skips held names, and is idempotent."""
    repo = make_repo(tmp_path)
    write(repo / "manage.py", "")
    write(repo / "requirements.txt", "django\n")
    write(repo / "aidocs" / "django_standards.human.md", "TEAM\n")
    profile_dir(tmp_path, "p").mkdir(parents=True)
    write(profile_dir(tmp_path, "p") / "python_code_style.human.md", "PROFILE-PY\n")
    write(repo / "aidocs" / "craft.json", '{"profile": "p"}')
    first = std(["init"], repo, tmp_path)
    assert first.returncode == 0
    assert (repo / "aidocs" / "python_code_style.ai.md").read_text() == "PROFILE-PY\n"
    assert not (repo / "aidocs" / "django_standards.ai.md").exists()
    assert (repo / "aidocs" / "django_standards.human.md").read_text() == "TEAM\n"
    assert "skipped  django_standards" in first.stdout and "wrote" in first.stdout
    assert (repo / "aidocs" / "implementation_standards.ai.md").read_bytes() == (
        PLUGIN_ROOT / "standards" / "implementation_standards.ai.md").read_bytes()
    again = std(["init"], repo, tmp_path).stdout
    written = first.stdout.count("wrote")
    assert "wrote" not in again and again.count("skipped") == written + 1
    empty = std(["init"], make_repo(tmp_path / "e"), tmp_path)
    assert empty.stdout.count("\n") == 1 and "no stack standards were found" in empty.stdout
    fresh = make_repo(tmp_path / "f")
    write(fresh / "manage.py", "")
    write(fresh / "package.json", '{"dependencies": {"express": "4"}}')
    both = std(["init"], fresh, tmp_path).stdout
    assert "django_standards.ai.md" in both and "node_standards.ai.md" in both
    assert both.count("python_code_style") == 1


def test_doctor_reports_profile_and_warns_on_problems(tmp_path):
    """STD-10: Given a profile, valid or broken, when craft-doctor runs, then it reports PASS or WARN without failing."""
    repo = make_repo(tmp_path)
    profile_dir(tmp_path, "tabdeal").mkdir(parents=True)
    write(repo / "aidocs" / "craft.json", '{"profile": "tabdeal"}')
    ok = run(DOCTOR, ["--skip", "commands"], repo, tmp_path)
    assert "PASS  profile" in ok.stdout and "tabdeal (source: aidocs/craft.json)" in ok.stdout
    assert "PASS  project layer" in ok.stdout and "PASS  profile layer" in ok.stdout
    write(tmp_path / "config" / "craft-workflow" / "profiles.json", "{broken")
    write(repo / "aidocs" / "craft.json", '{"profile": "ghost"}')
    bad = run(DOCTOR, ["--skip", "commands"], repo, tmp_path)
    assert "WARN" in bad.stdout and "ghost" in bad.stdout
    (repo / "aidocs" / "craft.json").unlink()
    broken = run(DOCTOR, ["--skip", "commands"], repo, tmp_path)
    assert "WARN" in broken.stdout and "profiles.json" in broken.stdout
    assert broken.returncode == 0 and re.search(r"\b0 FAIL\b", broken.stdout)
