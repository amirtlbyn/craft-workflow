"""Tests for the PHP stacks, one per acceptance criterion of the PHP spec."""

import json
import pathlib
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import craft_stack  # noqa: E402
import craft_state  # noqa: E402
import gate_spec  # noqa: E402

CRAFT_SPEC = PLUGIN_ROOT / "bin" / "craft-spec"

LARAVEL = '{"require": {"laravel/framework": "^11"}}'
SYMFONY = '{"require": {"symfony/framework-bundle": "^7"}}'

PAY_SPEC = """# SPEC: Payments

Key: PAY

## Acceptance criteria

| ID | Criterion | Class | Failure it catches |
|---|---|---|---|
| PAY-3 | WHEN over the limit, THE service SHALL refuse. | BUSINESS RULE | x |
| PAY-4 | WHEN cancelled, THE service SHALL refuse. | BUSINESS RULE | x |
| PAY-5 | WHEN refunded, THE service SHALL refund. | BUSINESS RULE | x |
"""

PEST_FILE = "<?php\n\nit('PAY-3: refuses over the limit', function () {\n    expect(true)->toBeTrue();\n});\n"
PHPUNIT_FILE = """<?php

final class PaymentTest extends TestCase
{
    #[TestDox('PAY-4: refuses a cancelled payment')]
    public function test_refuses(): void
    {
    }

    // PAY-5
    public function testCancelled(): void
    {
    }
}
"""


def make_repo(tmp_path, files):
    """Return a throwaway repository holding files, a {relative path: text} dict."""
    (tmp_path / ".git").mkdir(parents=True, exist_ok=True)
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def detected(root):
    """Return the detected stacks as 'id@dir' strings."""
    return [item["id"] + "@" + item["dir"] for item in craft_stack.detect(str(root))]


def composer(require=None, require_dev=None, scripts=None):
    """Return a composer.json text."""
    return json.dumps({"require": require or {}, "require-dev": require_dev or {}, "scripts": scripts or {}})


def test_detection_picks_one_php_pack_by_priority(tmp_path):
    """PHP-1: Given composer.json files, when detection runs, then laravel, symfony, or php wins by priority and other stacks are unchanged."""
    laravel = make_repo(tmp_path / "laravel", {"artisan": "", "composer.json": LARAVEL})
    symfony = make_repo(tmp_path / "symfony", {"composer.json": SYMFONY})
    slim = make_repo(tmp_path / "slim", {"composer.json": '{"require": {"slim/slim": "^4"}}'})
    monorepo = make_repo(tmp_path / "mono", {"api/composer.json": LARAVEL, "api/artisan": "", "web/package.json": "{}"})
    plain = make_repo(tmp_path / "plain", {"README.md": "# nothing"})

    assert detected(laravel) == ["laravel@"]
    assert detected(symfony) == ["symfony@"]
    assert detected(slim) == ["php@"]
    assert detected(monorepo) == ["laravel@api", "node@web"]
    assert detected(plain) == []
    assert craft_stack.primary(str(plain)) == craft_stack.DEFAULT_STACK


def test_checks_follow_composer_json(tmp_path):
    """PHP-2: Given composer.json files, when checks are chosen, then tests, types, and format follow the dependencies and scripts."""
    full = make_repo(
        tmp_path / "full",
        {
            "artisan": "",
            "composer.json": composer(
                require={"laravel/framework": "^11"},
                require_dev={"pestphp/pest": "^3", "larastan/larastan": "^3", "laravel/pint": "^1"},
                scripts={"test": "pest"},
            ),
        },
    )
    bare = make_repo(tmp_path / "bare", {"artisan": "", "composer.json": LARAVEL})
    symfony = make_repo(
        tmp_path / "symfony",
        {
            "composer.json": composer(
                require={"symfony/framework-bundle": "^7"},
                require_dev={"phpunit/phpunit": "^11", "vimeo/psalm": "^6", "friendsofphp/php-cs-fixer": "^3"},
            )
        },
    )
    slim = make_repo(tmp_path / "slim", {"composer.json": '{"require": {"slim/slim": "^4"}}'})
    mixed = make_repo(
        tmp_path / "mixed",
        {
            "api/composer.json": LARAVEL,
            "web/package.json": '{"scripts": {"test": "vitest run"}, "devDependencies": {"prettier": "3"}}',
        },
    )

    vite_beside = make_repo(
        tmp_path / "vite_beside",
        {"artisan": "", "composer.json": LARAVEL, "package.json": '{"scripts": {"test": "vitest run"}}'},
    )
    node_beside = make_repo(
        tmp_path / "node_beside",
        {
            "package.json": '{"devDependencies": {"vitest": "2"}}',
            "composer.json": '{"scripts": {"test": "phpunit"}}',
        },
    )

    assert craft_stack.checks_for("laravel", str(full)) == {
        "tests": "composer test",
        "types": "vendor/bin/phpstan analyse",
        "format": "vendor/bin/pint --test",
    }
    assert craft_stack.checks_for("laravel", str(bare)) == {"tests": "php artisan test"}
    assert craft_stack.checks_for("symfony", str(symfony)) == {
        "tests": "vendor/bin/phpunit",
        "types": "vendor/bin/psalm",
        "format": "vendor/bin/php-cs-fixer fix --dry-run --diff",
    }
    assert craft_stack.checks_for("laravel", str(vite_beside)) == {"tests": "php artisan test"}
    assert craft_stack.checks_for("node", str(node_beside)) == {"tests": "npx vitest run"}
    assert craft_stack.checks_for("php", str(slim)) == {"tests": "vendor/bin/phpunit"}
    assert craft_stack.checks_for("node", str(mixed), directory="web") == {
        "tests": "cd web && npm test",
        "format": "cd web && npx prettier --check .",
    }


def test_trace_maps_pest_testdox_and_comment_ids(tmp_path):
    """PHP-3: Given Pest, TestDox, and comment references, when trace runs, then each ID maps to its file and test name."""
    root = make_repo(
        tmp_path,
        {
            "composer.json": LARAVEL,
            "tests/Feature/PestTest.php": PEST_FILE,
            "tests/Unit/PaymentTest.php": PHPUNIT_FILE,
        },
    )
    spec = root / ".claude" / "specs" / "2026-10-14-pay"
    spec.mkdir(parents=True)
    (spec / "spec.md").write_text(PAY_SPEC, encoding="utf-8")
    (spec.parent / "ACTIVE").write_text(spec.name + "\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CRAFT_SPEC), "trace", "--json", "--cwd", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert json.loads(result.stdout)["criteria"] == {
        "PAY-3": ["tests/Feature/PestTest.php::PAY-3: refuses over the limit"],
        "PAY-4": ["tests/Unit/PaymentTest.php::test_refuses"],
        "PAY-5": ["tests/Unit/PaymentTest.php::testCancelled"],
    }


def test_gate_denies_php_tests_and_allows_source(tmp_path):
    """PHP-4: Given an approved spec and unapproved scenarios, when a PHP test is written, then the gate denies it and allows PHP source."""
    root = make_repo(tmp_path, {"composer.json": LARAVEL, "artisan": ""})
    spec = root / ".claude" / "specs" / "2026-10-14-pay"
    spec.mkdir(parents=True)
    (spec / "spec.md").write_text(PAY_SPEC, encoding="utf-8")
    (spec.parent / "ACTIVE").write_text(spec.name + "\n", encoding="utf-8")
    craft_state.add_spec_approval(spec.name, craft_state.file_digest(spec / "spec.md"), cwd=str(root))
    craft_state.start_session("task", cwd=str(root), spec=spec.name)
    (spec / "scenarios.md").write_text("## PAY-3\n- Given a, when b, then c\n", encoding="utf-8")

    def write(path):
        payload = {
            "session_id": "sess-1",
            "cwd": str(root),
            "tool_name": "Write",
            "tool_input": {"file_path": path, "content": "x"},
        }
        return gate_spec.decide(payload)[0]

    assert write("tests/Feature/WithdrawTest.php") == "deny"
    assert write("tests/Unit/WithdrawTest.php") == "deny"
    assert write("app/Services/WithdrawService.php") == "allow"
    assert write("src/WithdrawService.php") == "allow"


def test_paths_are_classified(tmp_path):
    """PHP-5: Given Laravel and Symfony paths, when classified, then migrations, models, views, and auth are marked."""
    laravel = make_repo(tmp_path / "laravel", {"artisan": "", "composer.json": LARAVEL})
    symfony = make_repo(tmp_path / "symfony", {"composer.json": SYMFONY})

    def marked(root, key, path):
        return craft_state.path_matches(path, craft_stack.globs_for(key, str(root)))

    assert marked(laravel, "migrations", "database/migrations/x.php")
    assert marked(laravel, "models", "app/Models/Order.php")
    assert marked(laravel, "views", "app/Http/Controllers/PayController.php")
    assert marked(laravel, "views", "routes/api.php")
    assert marked(laravel, "auth", "app/Policies/OrderPolicy.php")
    assert marked(symfony, "migrations", "migrations/Version1.php")
    assert marked(symfony, "models", "src/Entity/Order.php")
    assert marked(symfony, "views", "src/Controller/PayController.php")
    assert marked(symfony, "auth", "src/Security/Voter/OrderVoter.php")


def report_for(tmp_path, composer_text):
    """Return the concurrency report of a Laravel repository holding composer_text."""
    root = make_repo(tmp_path, {"artisan": "", "composer.json": composer_text})
    return craft_stack.concurrency(str(root))


def test_concurrency_report_follows_composer_json(tmp_path):
    """PHP-6: Given composer.json files, when the concurrency report runs, then the model, verdict, and avoid list follow the dependencies and a broken file is not-ready."""
    fpm = report_for(tmp_path / "fpm", LARAVEL)
    octane = report_for(tmp_path / "octane", composer({"laravel/framework": "^11", "laravel/octane": "^2"}))
    react = report_for(tmp_path / "react", composer({"laravel/framework": "^11", "react/event-loop": "^1"}))
    amp = report_for(tmp_path / "amp", composer({"laravel/framework": "^11", "amphp/amp": "^3"}))
    broken = report_for(tmp_path / "broken", '{"require": ')
    list_root = report_for(tmp_path / "list_root", "[]")
    list_require = report_for(tmp_path / "list_require", '{"require": []}')
    promise_only = report_for(tmp_path / "promise", composer({"laravel/framework": "^11", "react/promise": "^3"}))
    octane_promise = report_for(
        tmp_path / "octane_promise",
        composer({"laravel/framework": "^11", "laravel/octane": "^2", "react/promise": "^3"}),
    )
    no_composer = craft_stack.concurrency(str(make_repo(tmp_path / "none", {"artisan": ""})))

    assert (fpm["model"], fpm["verdict"]) == ("process per request", "limited")
    assert (octane["model"], octane["verdict"]) == ("long-lived workers", "limited")
    assert "static properties that hold request data" in octane["avoid"]
    assert (react["model"], react["verdict"]) == ("event loop", "ready")
    assert (amp["model"], amp["verdict"]) == ("event loop", "ready")
    assert broken["verdict"] == "not-ready"
    assert list_root["verdict"] == "not-ready"
    assert (list_require["model"], list_require["verdict"]) == ("process per request", "limited")
    assert (promise_only["model"], promise_only["verdict"]) == ("process per request", "limited")
    assert (octane_promise["model"], octane_promise["verdict"]) == ("long-lived workers", "limited")
    assert "static properties that hold request data" in octane_promise["avoid"]
    assert (no_composer["model"], no_composer["verdict"]) == ("process per request", "limited")
    for package in ("spiral/roadrunner-laravel", "openswoole/core", "runtime/frankenphp-symfony"):
        with_worker = report_for(
            tmp_path / package.replace("/", "_"), composer({"laravel/framework": "^11", package: "*"})
        )
        assert (with_worker["model"], with_worker["verdict"]) == ("long-lived workers", "limited"), package
        assert "static properties that hold request data" in with_worker["avoid"], package
        assert "between requests" in with_worker["summary"], package


def test_toolchain_lists_php_and_composer_required():
    """PHP-7: Given a laravel stack, when the toolchain is listed, then php and composer are required and the static analyzer is optional."""
    tools = {tool["id"]: tool for tool in craft_stack.toolchain_for("laravel")}

    assert tools["php"]["required"] is True
    assert tools["composer"]["required"] is True
    assert tools["phpstan"]["required"] is False


def test_lens_notes_exist_for_every_php_pack(tmp_path):
    """PHP-8: Given each of laravel, symfony and php, when craft-stack lens runs for each lens, then each prints a non-empty section of that pack."""
    roots = {
        "laravel": make_repo(tmp_path / "laravel", {"artisan": "", "composer.json": LARAVEL}),
        "symfony": make_repo(tmp_path / "symfony", {"composer.json": SYMFONY}),
        "php": make_repo(tmp_path / "php", {"composer.json": '{"require": {"slim/slim": "^4"}}'}),
    }

    for stack_id, root in roots.items():
        for lens in ("style", "logic", "security", "query", "concurrency"):
            with_stack = subprocess.run(
                [sys.executable, str(PLUGIN_ROOT / "bin" / "craft-stack"), "lens", lens, "--paths", "src/A.php"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            assert with_stack.returncode == 0
            assert "No stack-specific notes" not in with_stack.stdout
            assert len(craft_stack.lens_addendum(lens, stack_id)) > 40


def test_php_skill_and_standard_are_listed(tmp_path):
    """PHP-9: Given a Laravel path and the php_standards standard, when skills are listed and a section is printed, then php-practices is listed and the section prints with exit 0."""
    root = make_repo(tmp_path, {"artisan": "", "composer.json": LARAVEL})

    skills = craft_stack.skills_for(str(root), ["app/Http/Controllers/PayController.php"])
    printed = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "bin" / "craft-std"), "php_standards", "Money"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert "php-practices" in skills
    assert printed.returncode == 0
    assert "brick/money" in printed.stdout
