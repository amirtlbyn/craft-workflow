#!/usr/bin/env python3
"""validate_evals - check the eval suite without running it, and without a network.

Running the suite costs money and needs a credential. This does neither. It reads
every case and every grader on disk and reports the mistakes that would otherwise
only appear after a paid run: an unknown frontmatter key, a pattern that does not
compile, a grader whose body will be ignored, a negative Skill grader that is
silently excluded from the score.

    python3 scripts/validate_evals.py
    python3 scripts/validate_evals.py --json

Exit code 0 when nothing fails, 1 otherwise.

Standard library only, so it runs in a bare python image with no package index
reachable. That rules out PyYAML, so the frontmatter parser below understands one
small, strict subset of YAML and refuses anything outside it. That is deliberate:
it keeps the suite inside a subset that is easy to read, and a file it cannot
parse is reported rather than skipped.

One limit worth knowing. Graders use JavaScript regular expressions, and this
checks them with Python's `re`. The two agree on everything this suite uses, but
a JavaScript-only construct such as a lookbehind with a quantifier would pass
here and fail there.
"""

import json
import os
import pathlib
import re
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
EVAL_DIR = PLUGIN_ROOT / "evals"

# From the prompt.md frontmatter reference. An unknown key is an error there too.
PROMPT_KEYS = {
    "schema_version",
    "name",
    "description",
    "tags",
    "plugins",
    "runs",
    "expected_outcome",
    "model",
    "max_turns",
    "timeout_seconds",
    "allowed_tools",
    "append_system_prompt",
    "env",
}

GRADER_COMMON_KEYS = {"type", "weight", "arm"}
GRADER_TYPE_KEYS = {
    "regex": {"pattern", "flags", "match", "target"},
    "tool_used": {"tool", "input_match", "min", "max"},
    "tool_order": {"before", "after"},
    "file_exists": {"path", "exists"},
    "llm": {"criteria", "focus"},
    "baseline": {"baseline_file", "criteria"},
}
BODY_TYPES = ("llm", "baseline")
ARM_VALUES = ("with-only", "both")

# Tools a case may list in allowed_tools. Write, Edit and Bash are listed here
# because a case may ask for them, but the run only grants them from the command
# line with --allow-tools.
KNOWN_TOOLS = {
    "Read", "Glob", "Grep", "NotebookRead", "Skill", "Agent", "TodoWrite",
    "TaskCreate", "TaskGet", "TaskList", "TaskUpdate", "TaskStop", "TaskOutput",
    "Write", "Edit", "Bash", "WebFetch", "WebSearch", "NotebookEdit",
}


# ---------------------------------------------------------------------------
# A very small YAML subset
# ---------------------------------------------------------------------------


class YamlError(Exception):
    """The frontmatter is outside the subset this parser accepts."""


def split_flow(text):
    """Split a flow list or map body on commas, ignoring commas inside quotes."""
    parts = []
    current = ""
    quote = None
    depth = 0
    for character in text:
        if quote:
            current += character
            if character == quote:
                quote = None
            continue
        if character in "'\"":
            quote = character
            current += character
            continue
        if character in "[{":
            depth += 1
        elif character in "]}":
            depth -= 1
        if character == "," and depth == 0:
            parts.append(current.strip())
            current = ""
            continue
        current += character
    if current.strip():
        parts.append(current.strip())
    return parts


def parse_scalar(text):
    """Turn one YAML scalar into a Python value."""
    text = text.strip()
    if not text:
        return ""
    if text[0] == "'" and text[-1] == "'" and len(text) >= 2:
        return text[1:-1].replace("''", "'")
    if text[0] == '"' and text[-1] == '"' and len(text) >= 2:
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        return [parse_scalar(part) for part in split_flow(text[1:-1])]
    if text.startswith("{") and text.endswith("}"):
        mapping = {}
        for part in split_flow(text[1:-1]):
            if ":" not in part:
                raise YamlError("flow map entry has no colon: %s" % part)
            key, _, value = part.partition(":")
            mapping[key.strip()] = parse_scalar(value)
        return mapping
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if text in ("null", "~"):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    return text


def parse_yaml(text):
    """Parse the subset: key: value at the left margin, one level of nesting."""
    result = {}
    parent = None
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if ":" not in line:
            raise YamlError("line %d is not 'key: value': %s" % (number, line))
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if indent == 0:
            if value == "":
                parent = {}
                result[key] = parent
            else:
                result[key] = parse_scalar(value)
                parent = None
        else:
            if parent is None:
                raise YamlError("line %d is indented under nothing: %s" % (number, line))
            if value == "":
                raise YamlError("line %d nests two levels deep: %s" % (number, line))
            parent[key] = parse_scalar(value)
    return result


def read_frontmatter(path):
    """Return (frontmatter dict, body string) for a markdown file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise YamlError("no frontmatter: the file must start with ---")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise YamlError("the frontmatter is never closed with ---")
    return parse_yaml(text[4 : end + 1]), text[end + 5 :]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


class Report:
    def __init__(self):
        self.results = []

    def ok(self, case, message):
        self.results.append({"case": case, "status": "PASS", "detail": message})

    def fail(self, case, message):
        self.results.append({"case": case, "status": "FAIL", "detail": message})

    def note(self, case, message):
        self.results.append({"case": case, "status": "INFO", "detail": message})

    def failed(self):
        return any(result["status"] == "FAIL" for result in self.results)


def compiles(pattern):
    """Return an error string when the pattern does not compile, else ''."""
    try:
        re.compile(pattern)
        return ""
    except re.error as error:
        return str(error)


def check_prompt(report, case, path):
    """Check one prompt.md."""
    try:
        front, body = read_frontmatter(path)
    except (YamlError, OSError) as error:
        report.fail(case, "prompt.md: %s" % error)
        return

    unknown = sorted(set(front) - PROMPT_KEYS)
    if unknown:
        report.fail(case, "prompt.md: unknown frontmatter key(s): %s" % ", ".join(unknown))

    if not body.strip():
        report.fail(case, "prompt.md: the body is empty, so the case sends no prompt")

    plugins = front.get("plugins")
    if plugins is None:
        report.note(case, "prompt.md: no plugins key. Auto-detection must find the plugin")
    else:
        if not isinstance(plugins, list):
            plugins = [plugins]
        for entry in plugins:
            target = (path.parent / str(entry)).resolve()
            manifest = target / ".claude-plugin" / "plugin.json"
            if not manifest.is_file() and not (target / "plugin.json").is_file():
                report.fail(case, "prompt.md: plugins entry %r has no plugin manifest" % entry)

    tools = front.get("allowed_tools") or []
    if not isinstance(tools, list):
        report.fail(case, "prompt.md: allowed_tools must be a list")
    else:
        for tool in tools:
            if tool not in KNOWN_TOOLS:
                report.fail(case, "prompt.md: allowed_tools names an unknown tool %r" % tool)

    for key in ("max_turns", "timeout_seconds", "runs"):
        if key in front and not isinstance(front[key], int):
            report.fail(case, "prompt.md: %s must be a whole number" % key)

    report.ok(case, "prompt.md: %d frontmatter key(s), %d character prompt" % (len(front), len(body.strip())))


def check_grader(report, case, path):
    """Check one grader file."""
    name = path.name
    try:
        front, body = read_frontmatter(path)
    except (YamlError, OSError) as error:
        report.fail(case, "%s: %s" % (name, error))
        return

    kind = front.get("type")
    if kind not in GRADER_TYPE_KEYS:
        report.fail(case, "%s: type is %r, which is not a grader type" % (name, kind))
        return

    allowed = GRADER_COMMON_KEYS | GRADER_TYPE_KEYS[kind]
    unknown = sorted(set(front) - allowed)
    if unknown:
        report.fail(case, "%s: key(s) %s do not belong to a %s grader" % (name, ", ".join(unknown), kind))

    if "arm" in front and front["arm"] not in ARM_VALUES:
        report.fail(case, "%s: arm is %r, not one of %s" % (name, front["arm"], ", ".join(ARM_VALUES)))

    if body.strip() and kind not in BODY_TYPES:
        report.fail(case, "%s: a %s grader ignores its body, so this text does nothing" % (name, kind))
    if not body.strip() and kind in BODY_TYPES:
        report.fail(case, "%s: an %s grader reads its body as the rubric, and the body is empty" % (name, kind))

    if kind == "regex":
        pattern = front.get("pattern")
        if not pattern:
            report.fail(case, "%s: a regex grader needs a pattern" % name)
        else:
            error = compiles(str(pattern))
            if error:
                report.fail(case, "%s: pattern does not compile: %s" % (name, error))
        match = front.get("match")
        if match is not None and match != "not_contains" and not str(match).startswith("count:"):
            report.fail(case, "%s: match is %r, not not_contains or count:N" % (name, match))
        flags = front.get("flags")
        if flags is not None and not re.fullmatch(r"[imsu]+", str(flags)):
            report.fail(case, "%s: flags is %r. Put i in flags, never (?i) in the pattern" % (name, flags))

    if kind == "tool_used":
        if not front.get("tool"):
            report.fail(case, "%s: a tool_used grader needs a tool" % name)
        for key in ("min", "max"):
            if key in front and not isinstance(front[key], int):
                report.fail(case, "%s: %s must be a whole number" % (name, key))
        if front.get("input_match"):
            error = compiles(str(front["input_match"]))
            if error:
                report.fail(case, "%s: input_match does not compile: %s" % (name, error))
        negative = front.get("min") == 0 and front.get("max") == 0
        if front.get("tool") == "Skill" and negative and front.get("arm") != "both":
            report.fail(
                case,
                "%s: a negative Skill grader is excluded from the score unless it "
                "carries arm: both, so as written it proves nothing" % name,
            )
        if negative and front.get("arm") != "both":
            report.note(
                case,
                "%s: min 0 max 0 without arm: both. Confirm it should be scored in "
                "the baseline arm" % name,
            )

    if kind == "tool_order":
        for key in ("before", "after"):
            value = front.get(key)
            if value is None:
                report.fail(case, "%s: a tool_order grader needs %s" % (name, key))
                continue
            if isinstance(value, dict):
                if not value.get("tool"):
                    report.fail(case, "%s: %s is a map with no tool" % (name, key))
                if value.get("input_match"):
                    error = compiles(str(value["input_match"]))
                    if error:
                        report.fail(case, "%s: %s input_match does not compile: %s" % (name, key, error))
            elif not isinstance(value, str):
                report.fail(case, "%s: %s must be a tool name or a map" % (name, key))

    if kind == "file_exists" and not front.get("path"):
        report.fail(case, "%s: a file_exists grader needs a path" % name)

    report.ok(case, "%s: %s" % (name, kind))


def check_case_yaml(report, case, path):
    """Check one case.yaml."""
    try:
        data = parse_yaml(path.read_text(encoding="utf-8"))
    except (YamlError, OSError) as error:
        report.fail(case, "case.yaml: %s" % error)
        return
    for key in ("schema_version", "name"):
        if key not in data:
            report.fail(case, "case.yaml: %s is required" % key)
    context = data.get("context")
    if isinstance(context, dict):
        script = context.get("scaffold_script")
        if script:
            target = path.parent / str(script)
            if not target.is_file():
                report.fail(case, "case.yaml: scaffold_script %r is not on disk" % script)
            elif not os.access(str(target), os.X_OK):
                report.fail(case, "case.yaml: %s is not executable. Run chmod +x on it" % script)
            else:
                report.note(case, "case.yaml: scaffold_script %s. The run needs --scaffold" % script)
    report.ok(case, "case.yaml: %s" % data.get("name", ""))


def check_suite(report):
    """Walk every case directory."""
    if not EVAL_DIR.is_dir():
        report.fail("evals/", "the eval directory does not exist")
        return

    cases = sorted(
        path for path in EVAL_DIR.iterdir()
        if path.is_dir() and path.name != "results"
    )
    if not cases:
        report.fail("evals/", "no case directory found")
        return

    for directory in cases:
        case = directory.name
        prompt = directory / "prompt.md"
        case_yaml = directory / "case.yaml"

        if not prompt.is_file() and not case_yaml.is_file():
            report.fail(case, "neither prompt.md nor case.yaml, so this is not a case")
            continue
        if prompt.is_file():
            check_prompt(report, case, prompt)
        if case_yaml.is_file():
            check_case_yaml(report, case, case_yaml)

        graders = directory / "graders"
        if not graders.is_dir():
            report.fail(case, "no graders/ directory, so the case is never scored")
            continue
        files = sorted(graders.glob("*.md"))
        if not files:
            report.fail(case, "graders/ holds no .md file, so the case is never scored")
            continue
        for path in files:
            check_grader(report, case, path)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def main(argv):
    if "-h" in argv or "--help" in argv:
        print((__doc__ or "").strip())
        return 0

    report = Report()
    check_suite(report)

    passed = sum(1 for r in report.results if r["status"] == "PASS")
    failed = sum(1 for r in report.results if r["status"] == "FAIL")
    notes = sum(1 for r in report.results if r["status"] == "INFO")

    if "--json" in argv:
        print(json.dumps(
            {
                "eval_dir": str(EVAL_DIR),
                "results": report.results,
                "summary": {"PASS": passed, "FAIL": failed, "INFO": notes},
                "exit_code": 1 if failed else 0,
            },
            indent=2,
        ))
        return 1 if failed else 0

    print("validate-evals - %s" % EVAL_DIR)
    current = None
    for result in report.results:
        if result["case"] != current:
            current = result["case"]
            print("")
            print(current)
        print("  %-4s  %s" % (result["status"], result["detail"]))

    cases = len({result["case"] for result in report.results})
    print("")
    print("%d case(s)  %d PASS  %d FAIL  %d INFO" % (cases, passed, failed, notes))
    if failed:
        print("Fix every FAIL. A broken case is only discovered after a paid run.")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as error:
        sys.stderr.write("validate_evals could not finish: %s: %s\n" % (type(error).__name__, error))
        sys.exit(1)
