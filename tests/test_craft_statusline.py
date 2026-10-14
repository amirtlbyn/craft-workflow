"""Tests for bin/craft-statusline, one per acceptance criterion of the CSL spec."""

import importlib.machinery
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "bin" / "craft-statusline"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
NOW = 1_800_000_000.0


def load_statusline():
    loader = importlib.machinery.SourceFileLoader("craft_statusline", str(SCRIPT))
    spec = importlib.util.spec_from_loader("craft_statusline", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


statusline = load_statusline()


def plain_options(**overrides):
    options = statusline.parse_options([], {"NO_COLOR": "1"})
    return statusline.replace(options, **overrides)


def usage_data(**extra):
    data = {
        "model": {"display_name": "Opus"},
        "context_window": {"used_percentage": 42, "context_window_size": 200_000},
        "rate_limits": {"five_hour": {"used_percentage": 20, "resets_at": NOW + 4 * 3600}},
    }
    data.update(extra)
    return data


def test_craft_segment_shows_route_spec_gates_and_next_task():
    """CSL-1: Given an active session with mixed Gate A results, when rendered, then each check has its own glyph."""
    snapshot = {
        "session": {"active": True, "route": "task"},
        "spec": {
            "name": "2026-10-12-x",
            "key": "CSL",
            "state": "not approved",
            "tasks": [{"done": True}, {"done": True}, {"done": False}, {"done": False}, {"done": False}],
        },
        "gate_a": {
            "items": [
                {"name": "trace", "ok": True},
                {"name": "tests", "ok": False},
                {"name": "lint", "ok": None},
            ]
        },
        "gate_b": {"state": "changes requested"},
    }

    head = statusline.render(usage_data(), snapshot, plain_options(), NOW).splitlines()[0]

    assert "craft task" in head
    assert "CSL ● not approved" in head
    assert "A trace ✓ tests ✗ lint ○" in head
    assert "B ✗" in head
    assert head.endswith("3/5")


def test_window_shows_reset_pace_and_projection_only_when_the_limit_is_reached_first():
    """CSL-2: Given 60% used halfway through 5h, when rendered, then pace and the time to 100% show; 10% of 7d shows none."""
    data = usage_data(
        rate_limits={
            "five_hour": {"used_percentage": 60, "resets_at": NOW + 2.5 * 3600},
            "seven_day": {"used_percentage": 10, "resets_at": NOW + 3.5 * 86400},
        }
    )

    usage = statusline.render(data, None, plain_options(), NOW).splitlines()[1]
    _, five_hour, seven_day = usage.split(" │ ")

    assert "60% ↻2h30m pace 50% ⚠ full in 1h40m" in five_hour
    assert "10% ↻3d12h pace 50%" in seven_day
    assert "full" not in seven_day


def test_every_bar_style_is_exactly_the_requested_width_for_any_percentage():
    """CSL-3: Given every bar style and odd percentages, when drawn, then the bar is exactly the requested cells."""
    percents = [-20, 0, 0.4, 12.5, 33.3, 99.9, 100, 250, None, "x", float("nan")]
    for style in statusline.BARS:
        for color in (True, False):
            options = statusline.replace(statusline.parse_options([f"--bar={style}"], {}), color=color)
            painter = statusline.Painter(options)
            for width in (1, 8, 10):
                for percent in percents:
                    for marker in (None, 0, 71, 100):
                        drawn = ANSI.sub("", statusline.draw_bar(painter, percent, width, marker))
                        assert len(drawn) == width, (style, color, width, percent, marker, drawn)


def test_theme_and_bar_come_from_flag_then_environment_then_default():
    """CSL-4: Given a flag and a variable, when parsed, then the flag wins; an unknown name falls back and still prints."""
    env = {"CRAFT_STATUSLINE_THEME": "dracula", "CRAFT_STATUSLINE_BAR": "dots"}

    from_flag = statusline.parse_options(["--theme=nord", "--bar=braille"], env)
    from_env = statusline.parse_options([], env)
    unknown = statusline.parse_options(["--theme=nope", "--bar=bogus"], {})

    assert (from_flag.theme.name, from_flag.bar) == ("nord", "braille")
    assert (from_env.theme.name, from_env.bar) == ("dracula", "dots")
    assert (unknown.theme.name, unknown.bar) == ("craft", statusline.THEMES["craft"].bar)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--theme=nope", "--bar=bogus"],
        input=json.dumps(usage_data()),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0
    assert "Opus" in result.stdout


def test_no_craft_state_still_prints_model_context_and_usage(tmp_path, monkeypatch):
    """CSL-5: Given craft-ui-state fails or finds no session, when rendered, then the line has no craft part but the rest."""
    broken = tmp_path / "craft-ui-state"
    broken.write_text("import sys\nprint('Traceback: boom')\nsys.exit(1)\n", encoding="utf-8")
    monkeypatch.setattr(statusline, "UI_STATE", broken)
    idle = {"session": {"active": False}, "spec": {}}

    snapshot = statusline.craft_snapshot(str(tmp_path))

    assert snapshot is None
    for current in (snapshot, idle):
        lines = statusline.render(usage_data(), current, plain_options(), NOW).splitlines()
        assert "craft" not in lines[0]
        assert lines[0].startswith("🛠 Opus")
        assert "ctx" in lines[1]
        assert "5h" in lines[1]


def test_missing_or_broken_input_prints_what_it_has_and_exits_zero(tmp_path):
    """CSL-6: Given no rate limits, malformed fields, or input that is not JSON, when run, then it prints what it has and exits 0."""
    malformed = {
        "model": {"display_name": "Haiku"},
        "cost": {"total_cost_usd": "abc", "total_duration_ms": "long", "total_lines_added": [1]},
        "context_window": {"context_window_size": "big", "current_usage": {"input_tokens": "x"}},
        "rate_limits": {"five_hour": {"used_percentage": "most", "resets_at": 1e400}, "seven_day": [1, 2]},
    }
    inputs = [
        "not json at all",
        json.dumps({"model": {"display_name": "Sonnet"}}),
        json.dumps(["a", "list"]),
        "",
        json.dumps(malformed).replace("1e400", "1e999"),
        "[" * 100_000,
    ]
    outputs = []
    for text in inputs:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--detail"],
            input=text,
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={"NO_COLOR": "1", "PATH": "/usr/bin:/bin"},
            timeout=20,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert result.stderr == ""
        outputs.append(result.stdout)

    assert "usage after first reply" in outputs[0]
    assert "Sonnet" in outputs[1]
    assert "Haiku" in outputs[4]
    assert "status unavailable" not in outputs[4]
    assert all(output.strip() for output in outputs)


def test_detail_line_shows_cost_rate_time_lines_tokens_and_cache_share():
    """CSL-7: Given session cost data, when --detail renders, then the rates are right; zero duration and input give none."""
    data = usage_data(
        cost={
            "total_cost_usd": 1.5,
            "total_duration_ms": 30 * 60_000,
            "total_api_duration_ms": 10 * 60_000,
            "total_lines_added": 12,
            "total_lines_removed": 3,
        },
        context_window={
            "used_percentage": 42,
            "total_input_tokens": 1_200_000,
            "total_output_tokens": 45_000,
            "current_usage": {
                "input_tokens": 10,
                "cache_creation_input_tokens": 15,
                "cache_read_input_tokens": 75,
                "output_tokens": 900,
            },
        },
    )
    fresh = usage_data(
        cost={"total_cost_usd": 0, "total_duration_ms": 0}, context_window={"current_usage": {"input_tokens": 0}}
    )

    detail = statusline.render(data, None, plain_options(detail=True), NOW).splitlines()[2]
    first = statusline.render(fresh, None, plain_options(detail=True), NOW).splitlines()[2]

    assert detail == "💰 $1.50 · $3.00/h · 30m (api 10m) · +12 −3 · in 1.2M out 45k · cache 75%"
    assert first == "💰 $0.00"


def test_no_color_and_mono_print_no_escape_sequences():
    """CSL-8: Given NO_COLOR, or the mono theme, when every theme and bar renders, then no ANSI escape is printed."""
    data, snapshot = statusline.sample(NOW)
    for name in statusline.THEMES:
        for style in statusline.BARS:
            options = statusline.parse_options([f"--theme={name}", f"--bar={style}", "--detail"], {"NO_COLOR": "1"})
            assert "\x1b" not in statusline.render(data, snapshot, options, NOW, branch="main"), (name, style)
    mono = statusline.parse_options(["--theme=mono", "--bar=gradient-pill", "--detail"], {})
    assert "\x1b" not in statusline.render(data, snapshot, mono, NOW, branch="main")
    coloured = statusline.parse_options(["--theme=craft"], {})
    assert "\x1b" in statusline.render(data, snapshot, coloured, NOW)


@pytest.mark.parametrize(
    "scenarios, expected",
    [
        ({"state": "approved"}, "S ✓"),
        ({"state": "not approved"}, "S ●"),
        ({"state": "stale"}, "S !"),
        ({"state": "none"}, "S ○"),
        (None, "S ○"),
    ],
)
def test_scenarios_state_shows_as_s_glyph(scenarios, expected):
    """TSC-10: Given each scenarios state, when rendered, then S shows ✓ approved, ● not approved, ! stale, ○ none or absent."""
    snapshot = {"session": {"active": True, "route": "task"}, "scenarios": scenarios}

    head = statusline.render(usage_data(), snapshot, plain_options(), NOW).splitlines()[0]

    assert expected in head
