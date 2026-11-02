#!/usr/bin/env python3
"""craft_state - the one place the craft hooks read and write workflow state.

State lives in the host repository, never in this plugin:

    <repo>/.claude/craft/
    |-- session.json    the active craft session: route, spec, id, checks run, gated writes
    |-- approval.json   the spec approvals the developer gave, bound by SHA-256
    |-- findings.json   adjudicated review findings
    |-- logs/           full output of every bin/craft-check run
    |-- snapshots/      the state before one Bash call, one file per tool call
    `-- backups/        copies of files with uncommitted work, named by SHA-256

    <repo>/.claude/specs/
    |-- ACTIVE          one line: the active spec directory name
    `-- <dir>/spec.md   the spec the approval digest covers

Two rules govern every line below.

1. **Nothing here raises.** A hook that cannot read its state must let the tool
   call through, so "I do not know" and "allow" have to be the same answer. Every
   public function returns a safe default instead of failing.
2. **Nothing here writes outside .claude/craft/.** No network. git runs
   read-only, through _git(): status, ls-files, and cat-file.

Only the standard library is used, and only these modules: json, os, sys, re,
pathlib, fnmatch, datetime, hashlib, shlex, subprocess.

This module is also a small command line, so a developer or the model can create
a session and record a check without a hook:

    python3 scripts/craft_state.py status
    python3 scripts/craft_state.py start --route task
    python3 scripts/craft_state.py record-check --command "pytest -q" --exit-code 0

bin/craft-session and bin/craft-approve are the friendlier front doors.
"""

import base64
import datetime
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
PATHS_CONFIG = PLUGIN_ROOT / "config" / "paths.json"

SESSION_FILE = "session.json"
APPROVAL_FILE = "approval.json"
FINDINGS_FILE = "findings.json"
REVIEWS_FILE = "reviews.json"
TRACE_FILE = "trace.json"

MAX_CHECKS = 200
MAX_APPROVALS = 100
MAX_FINDINGS = 500

WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")

_paths_cache = None


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------


def now():
    """Return the current UTC time as an ISO-8601 string, to the second."""
    try:
        stamp = datetime.datetime.now(datetime.timezone.utc)
        return stamp.replace(microsecond=0).isoformat()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Where the state lives
# ---------------------------------------------------------------------------


def host_root(cwd=None):
    """Return the host repository root: the closest .git at or above cwd.

    Falls back to cwd itself when no .git is found, so a repository that is not
    under Git still gets a usable state directory.
    """
    try:
        start = pathlib.Path(cwd or os.getcwd()).resolve()
    except Exception:
        try:
            return pathlib.Path(os.getcwd())
        except Exception:
            return pathlib.Path(".")
    try:
        for candidate in [start] + list(start.parents):
            if (candidate / ".git").exists():
                return candidate
    except Exception:
        pass
    return start


def craft_dir(cwd=None):
    """Return <host repository>/.claude/craft."""
    return host_root(cwd) / ".claude" / "craft"


def state_path(filename, cwd=None):
    """Return the full path of one state file."""
    return craft_dir(cwd) / filename


# ---------------------------------------------------------------------------
# Reading and writing, safely
# ---------------------------------------------------------------------------


def _read_json(path, default):
    """Return the parsed JSON at path, or default on any problem at all."""
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except Exception:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def _write_json_atomic(path, data):
    """Replace path with data in one step. Return True on success.

    The write goes to a temporary file beside the target, then os.replace swaps
    it in. A reader never sees a half-written file, and a crash never leaves one.
    """
    temporary = None
    try:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name("%s.%d.tmp" % (path.name, os.getpid()))
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(str(temporary), str(path))
        return True
    except Exception:
        if temporary is not None:
            try:
                temporary.unlink()
            except Exception:
                pass
        return False


def text_digest(text):
    """Return the SHA-256 of a string, or '' when it cannot be computed."""
    try:
        return hashlib.sha256(str(text).encode("utf-8")).hexdigest()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# session.json
# ---------------------------------------------------------------------------


def read_session(cwd=None):
    """Return the session record, or {} when there is none."""
    data = _read_json(state_path(SESSION_FILE, cwd), {})
    return data if isinstance(data, dict) else {}


def is_active(cwd=None):
    """Return True when a craft session is recorded for this repository.

    Every hook except protect_human_owned and protect_approval is inert when this is False.
    """
    try:
        return state_path(SESSION_FILE, cwd).is_file()
    except Exception:
        return False


def current_route(cwd=None):
    """Return the active route in lower case: quick, task, project, or ''."""
    route = read_session(cwd).get("route")
    if not isinstance(route, str):
        return ""
    return route.strip().lower()


def current_session_id(cwd=None):
    """Return the Claude session id recorded for the active session, or None."""
    session_id = read_session(cwd).get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None


def checkpoint_command(cwd=None):
    """Return the checkpoint command recorded for the active session, or ''."""
    command = read_session(cwd).get("checkpoint_command")
    return command if isinstance(command, str) else ""


def start_session(route, session_id=None, checkpoint=None, cwd=None, spec=None, base=None):
    """Create or update session.json. Return True on success.

    An existing session keeps its start time, its checks and any field this call
    does not name.
    """
    try:
        session = read_session(cwd)
        session.setdefault("started_at", now())
        session.setdefault("checks", [])
        session["route"] = str(route or "").strip().lower()
        if session_id:
            session["session_id"] = str(session_id)
        if checkpoint:
            session["checkpoint_command"] = str(checkpoint)
        if spec:
            session["spec"] = str(spec)
        if base:
            session["base"] = str(base)
        session["updated_at"] = now()
        return _write_json_atomic(state_path(SESSION_FILE, cwd), session)
    except Exception:
        return False


def remember_session_id(session_id, cwd=None):
    """Record the Claude session id on an active session. Return True on success.

    A hook calls this once, so that bin/craft-approve can bind an approval to the
    session that is actually running. It writes nothing when no session exists,
    and nothing when the id is already the one on record.
    """
    try:
        if not session_id or not is_active(cwd):
            return False
        session = read_session(cwd)
        if session.get("session_id") == session_id:
            return False
        session["session_id"] = str(session_id)
        session["updated_at"] = now()
        return _write_json_atomic(state_path(SESSION_FILE, cwd), session)
    except Exception:
        return False


def record_check(command, exit_code, cwd=None, session_id=None, label=None, log=None, summary=None, tree=None,
                 run_in=None):
    """Append a command and its exit code to session.json. Return True on success.

    This is the evidence Gate A needs. A claim of `done` with no check that
    exited 0 behind it is a claim with nothing under it.
    """
    try:
        session = read_session(cwd)
        session.setdefault("started_at", now())
        session.setdefault("route", "")
        checks = session.get("checks")
        if not isinstance(checks, list):
            checks = []
        checks.append(
            {
                "command": str(command),
                "exit_code": int(exit_code),
                "at": now(),
                "session_id": str(session_id) if session_id else session.get("session_id"),
            }
        )
        if label:
            checks[-1]["label"] = str(label)
        if log:
            checks[-1]["log"] = str(log)
        if tree:
            checks[-1]["tree"] = str(tree)
        if run_in:
            checks[-1]["cwd"] = str(run_in)
        if isinstance(summary, dict) and summary:
            checks[-1]["summary"] = {
                str(key): value for key, value in summary.items()
                if isinstance(value, (int, float, str)) or value is None
            }
        session["checks"] = checks[-MAX_CHECKS:]
        session["updated_at"] = now()
        return _write_json_atomic(state_path(SESSION_FILE, cwd), session)
    except Exception:
        return False


def checks(cwd=None):
    """Return the recorded checks, oldest first. [] on any problem."""
    recorded = read_session(cwd).get("checks")
    if not isinstance(recorded, list):
        return []
    return [check for check in recorded if isinstance(check, dict)]


def green_checks(cwd=None):
    """Return the recorded checks that exited 0."""
    return [check for check in checks(cwd) if check.get("exit_code") == 0]


def end_session(cwd=None):
    """Archive session.json inside .claude/craft/. Return the archive path or ''.

    The session file is moved, never deleted, so the audit trail survives.
    """
    try:
        source = state_path(SESSION_FILE, cwd)
        if not source.is_file():
            return ""
        archive = craft_dir(cwd) / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        stamp = now().replace(":", "").replace("-", "")
        target = archive / ("session-%s.json" % (stamp or "unknown"))
        os.replace(str(source), str(target))
        return str(target)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# approval.json
# ---------------------------------------------------------------------------


def read_approvals(cwd=None):
    """Return every approval record. [] on any problem."""
    data = _read_json(state_path(APPROVAL_FILE, cwd), {})
    if not isinstance(data, dict):
        return []
    approvals = data.get("approvals")
    if not isinstance(approvals, list):
        return []
    return [approval for approval in approvals if isinstance(approval, dict)]


def approvals_for(session_id, cwd=None):
    """Return the approvals that cover session_id. [] when there are none.

    An approval whose session_id is null covers whichever session is active.
    bin/craft-approve writes that only when session.json holds no session id, so
    it cannot widen an approval that was bound to a session.
    """
    try:
        covering = []
        for approval in read_approvals(cwd):
            owner = approval.get("session_id")
            if owner is None:
                covering.append(approval)
            elif session_id and owner == session_id:
                covering.append(approval)
        return covering
    except Exception:
        return []


def add_approval(scenarios_text, session_id=None, kind="test-scenarios", note="", cwd=None):
    """Append one approval record. Return True on success."""
    try:
        data = _read_json(state_path(APPROVAL_FILE, cwd), {})
        if not isinstance(data, dict):
            data = {}
        approvals = data.get("approvals")
        if not isinstance(approvals, list):
            approvals = []
        text = str(scenarios_text or "")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        approvals.append(
            {
                "session_id": str(session_id) if session_id else None,
                "kind": str(kind),
                "approved_at": now(),
                "approved_by": "developer",
                "note": str(note or ""),
                "scenario_lines": len(lines),
                "sha256": text_digest(text),
                "scenarios": text,
            }
        )
        data["approvals"] = approvals[-MAX_APPROVALS:]
        return _write_json_atomic(state_path(APPROVAL_FILE, cwd), data)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# The active spec, and its approval
# ---------------------------------------------------------------------------

SPEC_STATES = ("none", "not approved", "stale", "approved")


def specs_dir(cwd=None):
    """Return <host repository>/.claude/specs."""
    return host_root(cwd) / ".claude" / "specs"


def active_spec_name(cwd=None):
    """Return the directory name in .claude/specs/ACTIVE, or ''."""
    try:
        text = (specs_dir(cwd) / "ACTIVE").read_text(encoding="utf-8")
        name = text.strip().splitlines()[0].strip() if text.strip() else ""
        # A name is one directory, never a path that could climb out.
        if not name or "/" in name or "\\" in name or name in (".", ".."):
            return ""
        return name
    except Exception:
        return ""


def active_spec_dir(cwd=None):
    """Return the active spec directory as a Path, or None."""
    try:
        name = active_spec_name(cwd)
        if not name:
            return None
        path = specs_dir(cwd) / name
        return path if path.is_dir() else None
    except Exception:
        return None


def file_digest(path):
    """Return the SHA-256 of a file's bytes, or '' when it cannot be read."""
    try:
        return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    except Exception:
        return ""


def spec_approvals(spec_name, cwd=None):
    """Return the spec approvals recorded for one spec directory, oldest first."""
    try:
        return [
            approval
            for approval in read_approvals(cwd)
            if approval.get("kind") == "spec" and approval.get("spec") == spec_name
        ]
    except Exception:
        return []


def spec_state(cwd=None):
    """Return (state, detail). state is one of SPEC_STATES. Never raises.

    none          no active spec, or its spec.md is missing
    not approved  spec.md exists, and no approval names it
    stale         the latest approval covers a different SHA-256 than spec.md has now
    approved      the latest approval covers spec.md exactly as it is on disk
    """
    detail = {"spec": "", "path": "", "sha256": "", "approved_sha256": "", "approved_at": ""}
    try:
        directory = active_spec_dir(cwd)
        if directory is None:
            return ("none", detail)
        spec_md = directory / "spec.md"
        detail["spec"] = directory.name
        detail["path"] = str(spec_md)
        if not spec_md.is_file():
            return ("none", detail)
        digest = file_digest(spec_md)
        detail["sha256"] = digest
        approvals = spec_approvals(directory.name, cwd)
        if not approvals:
            return ("not approved", detail)
        latest = approvals[-1]
        detail["approved_sha256"] = str(latest.get("sha256", ""))
        detail["approved_at"] = str(latest.get("approved_at", ""))
        if digest and latest.get("sha256") == digest:
            return ("approved", detail)
        return ("stale", detail)
    except Exception:
        return ("none", detail)


def add_spec_approval(spec_name, digest, note="", cwd=None):
    """Record that the developer approved spec.md at this SHA-256. True on success."""
    try:
        data = _read_json(state_path(APPROVAL_FILE, cwd), {})
        if not isinstance(data, dict):
            data = {}
        approvals = data.get("approvals")
        if not isinstance(approvals, list):
            approvals = []
        approvals.append(
            {
                "kind": "spec",
                "spec": str(spec_name),
                "sha256": str(digest),
                "approved_at": now(),
                "approved_by": "developer",
                "note": str(note or ""),
                "session_id": current_session_id(cwd),
            }
        )
        data["approvals"] = approvals[-MAX_APPROVALS:]
        return _write_json_atomic(state_path(APPROVAL_FILE, cwd), data)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# The scenarios of the active spec, and their approval
# ---------------------------------------------------------------------------

CRITERION_ROW = re.compile(r"^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|")
SECTION_HEADING = re.compile(r"^##\s+(.+?)\s*$")
RETIRED_HEADING = "Retired"
SCENARIO_LINE = re.compile(r"^-\s+(\S.*?)\s*$")


def criterion_ids(spec_text):
    """Return the criterion IDs of the "Acceptance criteria" section, in order. Never raises."""
    ids = []
    try:
        in_section = False
        for line in str(spec_text).splitlines():
            heading = SECTION_HEADING.match(line)
            if heading:
                in_section = heading.group(1).strip().lower().startswith("acceptance criteria")
                continue
            if in_section:
                match = CRITERION_ROW.match(line)
                if match and match.group(1) not in ids:
                    ids.append(match.group(1))
    except Exception:
        pass
    return ids


UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _table_cells(line):
    """Split one Markdown table row on unescaped pipes. Return None when the line is not a table row."""
    text = line.strip()
    if not text.startswith("|"):
        return None
    text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [cell.strip() for cell in UNESCAPED_PIPE.split(text)]


def unanswered_questions(spec_text):
    """Return the Open questions rows with no developer decision, as [(question, decision)]. Never raises.

    The Decision column is the one whose header cell reads "decision" (any
    case). A row is unanswered when its Decision cell does not contain
    "(developer" after `*_` and backticks are stripped. A short row has an empty
    Decision. A table with no Decision header counts every row as unanswered.
    A non-table line ends the table, so a second table gets its own header.
    """
    rows = []
    try:
        in_section = False
        column = None
        header_seen = False
        for line in str(spec_text).splitlines():
            heading = SECTION_HEADING.match(line)
            if heading:
                in_section = heading.group(1).strip().lower().startswith("open questions")
                column, header_seen = None, False
                continue
            if not in_section:
                continue
            cells = _table_cells(line)
            if cells is None:
                if line.strip():
                    column, header_seen = None, False
                continue
            if not header_seen:
                header_seen = True
                names = [cell.strip("*_` ").lower() for cell in cells]
                column = names.index("decision") if "decision" in names else None
                continue
            if all(set(cell) <= set("-: ") for cell in cells):
                continue
            decision = ""
            if column is not None and column < len(cells):
                decision = cells[column]
            plain = decision.replace("*", "").replace("_", "").replace("`", "").lower()
            if "(developer" not in plain:
                rows.append((cells[0], decision))
    except Exception:
        pass
    return rows


SESSION_HEADING = re.compile(r"^##\s+Session\s+(\d+)\b", re.IGNORECASE)
ANY_H2 = re.compile(r"^##\s")
MODEL_LINE = re.compile(r"^\s*Model:\s*(\S.*?)\s*$", re.IGNORECASE)


def session_models(tasks_text):
    """Return {session number: "<id> — <reason>"} for each Session block in tasks.md. Never raises.

    A session with no Model: line, or a placeholder value that starts with "<",
    maps to "". Any other "## " heading ends the block.
    """
    models = {}
    try:
        current = None
        for line in str(tasks_text).splitlines():
            heading = SESSION_HEADING.match(line)
            if heading:
                current = int(heading.group(1))
                models[current] = ""
                continue
            if ANY_H2.match(line):
                current = None
                continue
            if current is not None and not models[current]:
                match = MODEL_LINE.match(line)
                if match and not match.group(1).startswith("<"):
                    models[current] = match.group(1)
    except Exception:
        pass
    return models


def scenarios_path(cwd=None):
    """Return the path of scenarios.md in the active spec directory, or None."""
    directory = active_spec_dir(cwd)
    return None if directory is None else directory / "scenarios.md"


def parse_scenarios(text):
    """Split scenarios.md into (preamble, sections, retired). Never raises.

    preamble  the lines before the first "##" heading
    sections  {heading: [body lines]} in file order, for each "## <ID>"
    retired   {ID: [body lines]} for each "### <ID>" under "## Retired"; the lines
              directly under "## Retired" are kept under the key ""

    Body lines are kept as written, so a comment survives a draft. Trailing blank lines are dropped.
    """
    preamble, sections, retired = [], {}, {}
    try:
        current = preamble
        in_retired = False
        for line in str(text).splitlines():
            if line.startswith("### ") and in_retired:
                current = retired.setdefault(line[4:].strip(), [])
                continue
            heading = SECTION_HEADING.match(line)
            if heading:
                name = heading.group(1).strip()
                in_retired = name == RETIRED_HEADING
                current = retired.setdefault("", []) if in_retired else sections.setdefault(name, [])
                continue
            current.append(line)
        for body in [preamble] + list(sections.values()) + list(retired.values()):
            while body and not body[-1].strip():
                body.pop()
        if not retired.get(""):
            retired.pop("", None)
    except Exception:
        pass
    return (preamble, sections, retired)


def scenario_texts(body):
    """Return the scenario texts in one section body: its "- text" lines."""
    texts = []
    for line in body:
        match = SCENARIO_LINE.match(line)
        if match:
            texts.append(match.group(1))
    return texts


def read_scenarios(path):
    """Return {ID: [scenario text, ...]} in file order, or {} when unreadable. Never raises."""
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except Exception:
        return {}
    _preamble, sections, _retired = parse_scenarios(text)
    return {name: scenario_texts(body) for name, body in sections.items()}


def arrange_scenarios(ids, sections, retired):
    """Return (sections, retired) with one section per ID in spec order. Never invents a line.

    A section whose heading is not in ids moves to retired. A retired section
    whose ID is back in ids moves back, after the lines already in its section.
    """
    arranged = {}
    kept = {}
    for name, body in retired.items():
        if name not in ids:
            kept[name] = list(body)
    for name in ids:
        arranged[name] = list(sections.get(name, [])) + list(retired.get(name, []))
    for name, body in sections.items():
        if name not in ids:
            kept[name] = list(kept.get(name, [])) + list(body)
    return (arranged, kept)


def render_scenarios(preamble, sections, retired):
    """Return the text of scenarios.md for these parts."""

    def trimmed(body):
        body = list(body)
        while body and not body[-1].strip():
            body.pop()
        return body

    lines = trimmed(preamble)
    for name, body in sections.items():
        lines += ([""] if lines else []) + ["## " + name] + trimmed(body)
    if retired:
        lines += ([""] if lines else []) + ["## " + RETIRED_HEADING] + trimmed(retired.get("", []))
        for name, body in retired.items():
            if name:
                lines += ["", "### " + name] + trimmed(body)
    return "\n".join(lines) + "\n"


def write_scenarios(path, sections, retired, preamble=()):
    """Replace scenarios.md in one step. True on success. Never raises."""
    temporary = None
    try:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name("%s.%d.tmp" % (path.name, os.getpid()))
        temporary.write_text(render_scenarios(preamble, sections, retired), encoding="utf-8")
        os.replace(str(temporary), str(path))
        return True
    except Exception:
        if temporary is not None:
            try:
                temporary.unlink()
            except Exception:
                pass
        return False


def scenario_approvals(spec_name, cwd=None):
    """Return the scenario approvals recorded for one spec directory, oldest first."""
    try:
        return [
            approval
            for approval in read_approvals(cwd)
            if approval.get("kind") == "scenarios" and approval.get("spec") == spec_name
        ]
    except Exception:
        return []


def scenarios_state(cwd=None):
    """Return (state, detail). state is one of SPEC_STATES. Never raises.

    none          no active spec, or no scenarios.md
    not approved  scenarios.md exists, and no scenario approval names this spec
    stale         scenarios.md, or spec.md, differs from what the latest approval recorded
    approved      both files match the latest approval

    detail: spec, path, sha256 and spec_sha256 (the files now), approved_sha256,
    approved_spec_sha256, approved_at, count (scenarios), missing (criteria with none),
    error and reason. error is True when a file exists but cannot be read or parsed:
    the state is then "none", and the gate must allow (INV-3). A missing scenarios.md
    is plain "none" with error False.
    """
    detail = {
        "spec": "",
        "path": "",
        "sha256": "",
        "spec_sha256": "",
        "approved_sha256": "",
        "approved_spec_sha256": "",
        "approved_at": "",
        "count": 0,
        "missing": [],
        "error": False,
        "reason": "",
    }
    try:
        directory = active_spec_dir(cwd)
        if directory is None or not (directory / "spec.md").is_file():
            return ("none", detail)
        detail["spec"] = directory.name
        spec_bytes = (directory / "spec.md").read_bytes()
        detail["spec_sha256"] = hashlib.sha256(spec_bytes).hexdigest()
        ids = criterion_ids(spec_bytes.decode("utf-8"))
        path = directory / "scenarios.md"
        detail["path"] = str(path)
        try:
            scenario_bytes = path.read_bytes()
        except FileNotFoundError:
            detail["missing"] = list(ids)
            return ("none", detail)
        detail["sha256"] = hashlib.sha256(scenario_bytes).hexdigest()
        _preamble, sections, _retired = parse_scenarios(scenario_bytes.decode("utf-8"))
        found = {name: scenario_texts(body) for name, body in sections.items()}
        detail["count"] = sum(len(found.get(name, [])) for name in ids)
        detail["missing"] = [name for name in ids if not found.get(name)]
        approvals = scenario_approvals(directory.name, cwd)
        if not approvals:
            return ("not approved", detail)
        latest = approvals[-1]
        detail["approved_sha256"] = str(latest.get("sha256", ""))
        detail["approved_spec_sha256"] = str(latest.get("spec_sha256", ""))
        detail["approved_at"] = str(latest.get("approved_at", ""))
        if detail["sha256"] == detail["approved_sha256"] and detail["spec_sha256"] == detail["approved_spec_sha256"]:
            return ("approved", detail)
        return ("stale", detail)
    except Exception as error:
        detail["error"] = True
        detail["reason"] = "%s: %s" % (type(error).__name__, error)
        return ("none", detail)


def add_scenarios_approval(spec_name, digest, spec_digest, count, note="", cwd=None):
    """Record that the developer approved scenarios.md at this SHA-256. True on success."""
    try:
        data = _read_json(state_path(APPROVAL_FILE, cwd), {})
        if not isinstance(data, dict):
            data = {}
        approvals = data.get("approvals")
        if not isinstance(approvals, list):
            approvals = []
        approvals.append(
            {
                "kind": "scenarios",
                "spec": str(spec_name),
                "sha256": str(digest),
                "spec_sha256": str(spec_digest),
                "count": int(count),
                "approved_at": now(),
                "approved_by": "developer",
                "note": str(note or ""),
                "session_id": current_session_id(cwd),
            }
        )
        data["approvals"] = approvals[-MAX_APPROVALS:]
        return _write_json_atomic(state_path(APPROVAL_FILE, cwd), data)
    except Exception:
        return False


TASK_LINE = re.compile(r"^\s*[-*]\s*\[([ xX])\]\s*(.+?)\s*$")
STATE_FIELD = re.compile(r"\bState:\s*([a-z][a-z ]*[a-z])", re.IGNORECASE)
RISK_FIELD = re.compile(r"\bRisk:\s*[*_`]*(low|high)\b", re.IGNORECASE)
TITLE_LINE = re.compile(r"^#\s+(?:SPEC|TASKS):\s*(.+?)\s*$", re.MULTILINE)


def spec_progress(cwd=None):
    """Return a small summary of the active spec's tasks.md. {} on any problem.

    Keys: title, risk, state, done, total, next_task.
    """
    try:
        directory = active_spec_dir(cwd)
        if directory is None:
            return {}
        summary = {"title": "", "risk": "", "state": "", "done": 0, "total": 0, "next_task": ""}
        spec_text = ""
        try:
            spec_text = (directory / "spec.md").read_text(encoding="utf-8")
        except Exception:
            pass
        match = TITLE_LINE.search(spec_text)
        if match:
            summary["title"] = match.group(1)
        match = RISK_FIELD.search(spec_text)
        if match:
            summary["risk"] = match.group(1).lower()
        try:
            tasks_text = (directory / "tasks.md").read_text(encoding="utf-8")
        except Exception:
            return summary
        match = STATE_FIELD.search(tasks_text)
        if match:
            summary["state"] = match.group(1).strip().lower()
        in_comment = False
        for line in tasks_text.splitlines():
            if "<!--" in line:
                in_comment = True
            if in_comment:
                if "-->" in line:
                    in_comment = False
                continue
            task = TASK_LINE.match(line)
            if not task:
                continue
            summary["total"] += 1
            if task.group(1).lower() == "x":
                summary["done"] += 1
            elif not summary["next_task"]:
                summary["next_task"] = task.group(2)
        return summary
    except Exception:
        return {}


def _real(path, cwd=None):
    """Return path as an absolute path with every symlink resolved."""
    target = pathlib.Path(path)
    if not target.is_absolute():
        target = pathlib.Path(cwd or os.getcwd()) / target
    return os.path.realpath(str(target))


def is_inside_craft_area(path, cwd=None):
    """Return True when path is under <host>/.claude/, or outside the host repository.

    The spec gate shuts the host repository's source and tests. Spec files,
    craft state, and files outside the repository are not its business.
    Symlinks are resolved first, so a link cannot carry a write past the gate.
    """
    try:
        relative = pathlib.Path(_real(path, cwd)).relative_to(host_root(cwd))
    except Exception:
        return True
    parts = relative.parts
    return bool(parts) and parts[0] == ".claude"


def repo_relative(path, cwd=None):
    """Return path relative to the host repository, symlinks resolved, with "/" separators, or ''."""
    try:
        return pathlib.Path(_real(path, cwd)).relative_to(host_root(cwd)).as_posix()
    except Exception:
        return ""


CRAFT_STATE_PATH = re.compile(r"(?:^|/)\.claude/(?:craft(?:/|$)|specs/ACTIVE$)")
SETTINGS_FILES = ("settings.json", "settings.local.json")


def is_craft_state(path, cwd=None):
    """Return True when path is a .claude/craft directory, under one, or a .claude/specs/ACTIVE.

    This holds in any repository.

    Both the path as written and the path with symlinks resolved are checked.
    """
    try:
        target = pathlib.Path(path)
        if not target.is_absolute():
            target = pathlib.Path(cwd or os.getcwd()) / target
        written = os.path.normpath(str(target)).replace("\\", "/")
        return bool(CRAFT_STATE_PATH.search(written) or CRAFT_STATE_PATH.search(_real(path, cwd).replace("\\", "/")))
    except Exception:
        return False


def is_settings_file(path, cwd=None):
    """Return True when path is a .claude/settings.json or .claude/settings.local.json."""
    try:
        for candidate in (pathlib.Path(os.path.normpath(str(pathlib.Path(cwd or os.getcwd()) / path))),
                          pathlib.Path(_real(path, cwd))):
            if candidate.name in SETTINGS_FILES and candidate.parent.name == ".claude":
                return True
        return False
    except Exception:
        return False


def is_plugin_write(path, cwd=None):
    """Return True when path is under this plugin's root, and the root is outside the host repository.

    When the plugin root is the host repository or inside it, the developer is
    working on the plugin itself, and the answer is always False.
    """
    try:
        root = os.path.realpath(str(PLUGIN_ROOT))
        host = str(host_root(cwd))
        if root == host or root.startswith(host + os.sep):
            return False
        target = _real(path, cwd)
        return target == root or target.startswith(root + os.sep)
    except Exception:
        return False


def gate_shut(cwd=None):
    """Return True when the route is task or project and the spec is not approved."""
    return current_route(cwd) in ("task", "project") and spec_state(cwd)[0] != "approved"


# ---------------------------------------------------------------------------
# What a Bash command does, read from its text
# ---------------------------------------------------------------------------
#
# This is not a shell parser. It finds the common write forms, the commands
# that run craft-approve, and the other hook off-switches. A form it misses is
# caught after the call by changed_files() and by the approval.json snapshot.

SHELL_PUNCTUATION = "();<>|&`\n"
LITERAL_DOLLAR = "\x01"
HEREDOC_MARK = re.compile(r"<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][\w.-]*)\2")
HEREDOC_TOKEN = re.compile(r"^__CRAFT_HEREDOC_(\d+)__$")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WRAPPER_ARGUMENT = re.compile(r"^(?:-.*|[A-Za-z_][A-Za-z0-9_]*=.*|\d+(?:\.\d+)?[smhd]?)$")
WRAPPER_VALUES = {
    "sudo": ("-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-T", "--user", "--group", "--chdir"),
    "env": ("-u", "-C", "--unset", "--chdir"),
    "nice": ("-n", "--adjustment"),
    "timeout": ("-s", "-k", "--signal", "--kill-after"),
    "xargs": ("-I", "-n", "-P", "-L", "-d", "-E", "-s", "-a", "--max-args", "--max-procs", "--delimiter",
              "--arg-file", "--max-lines", "--eof"),
    "stdbuf": ("-i", "-o", "-e"),
}
WRAPPERS = tuple(WRAPPER_VALUES) + ("command", "exec", "nohup", "time", "builtin")
RESERVED_WORDS = ("if", "then", "elif", "else", "fi", "do", "done", "while", "until", "{", "}", "!", "[[", "]]", "esac")
LOOP_HEADERS = ("for", "select", "case", "function")
SHELLS = ("sh", "bash", "zsh", "dash", "ksh", "fish")
INTERPRETER = re.compile(r"^(?:python[\d.]*|pypy[\d.]*|node|nodejs|perl|ruby|\.|source)$")
CODE_FLAG = re.compile(r"^(?:-[A-Za-z]*[ce]|--eval)$")
IN_PLACE_FLAG = re.compile(r"^(?:-[A-Za-z]*i.*|--in-place.*)$")
DECLARERS = ("export", "declare", "typeset", "local", "readonly")
WRITE_COMMANDS = ("tee", "rm", "touch", "mv", "truncate", "cp", "ln", "install", "dd", "sed", "perl", "patch", "git")
GIT_READ_ONLY = ("log", "show", "diff", "grep", "blame", "status")
GIT_READ_ONLY_APPLY = ("--check", "--stat", "--numstat", "--summary")
READ_ONLY = (
    "rg", "grep", "egrep", "fgrep", "cat", "less", "more", "head", "tail", "wc", "ls", "file", "stat", "echo",
    "printf", "sort", "uniq", "cut", "tr", "nl", "diff", "cd", "pushd", "popd", "pwd", "true", "false",
    "basename", "dirname", "realpath", "readlink", "which", "jq",
)
STATE_WORDS = re.compile(r"\.claude/craft\b|craft/(?:session|findings|reviews|approval)\.json|specs/ACTIVE|\bagent_gate\b|\brecord_spawn\b")
BACKUP_PATH = re.compile(r"/\.claude/craft/backups/[0-9a-f]{64}$")
STATE_SAFE_PROGRAMS = ("craft-check", "craft-scenarios", "craft-stack", "craft-std", "craft-ui-state")
COPY_VALUED = ("-m", "--mode", "-o", "--owner", "-g", "--group", "-S", "--suffix")
SCRIPT_FLAGS = ("-e", "-f", "--expression", "--file")
CRAFT_PROGRAMS = ("craft-session", "craft-spec", "craft_state.py")


def _is_state_safe_program(program, arguments):
    """Return True for a bin/ program run that writes craft state honestly, as a program, or `git add`."""
    subcommand = arguments[0] if arguments else ""
    if program in STATE_SAFE_PROGRAMS:
        return True
    if program == "git":
        return _git_subcommand(arguments)[0] == "add"
    if program == "craft-spec":
        return subcommand in ("status", "trace", "lenses")
    if program == "craft-session":
        state = arguments[arguments.index("--state") + 1] if "--state" in arguments[:-1] else ""
        return subcommand in ("status", "record-finding", "record-review") or (subcommand == "finding" and state == "fixed")
    return False
MAX_BASES = 4

# A write call in Python, Node, Perl, or Ruby code, path known or not. A call
# that starts another process counts as a write to an unknown path.
CODE_WRITES = re.compile(
    r"\.write_(?:text|bytes)\s*\("
    r"|\bopen\s*\(\s*[^,()]+,\s*(?:mode\s*=\s*)?[rbf]?['\"][rbt]*[wax+]"
    r"|\b(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream|copyFile|copyFileSync"
    r"|renameSync|unlinkSync|rmSync)\s*\("
    r"|\bshutil\.(?:copy\w*|move|rmtree)\s*\("
    r"|\bos\.(?:remove|unlink|rename|replace|truncate|system|popen|exec\w*|spawn\w*)\s*\("
    r"|\bsubprocess\.\w+\s*\("
    r"|\bchild_process\b"
    r"|\bRuntime\.getRuntime\s*\(\s*\)\s*\.\s*exec"
    r"|(?<![.\w])(?:system|exec|spawn)\s*\("
    r"|\bIO\.popen|\bOpen3\.|%x\("
    r"|\b(?:File|IO)\.write\s*\("
    r"|\bFileUtils\.\w+"
    r"|\bopen\s*\(?\s*(?:my\s+)?[$\w]+\s*,\s*['\"]\+?>"
)
# The same calls, when the path is a string literal.
CODE_WRITE_PATHS = re.compile(
    r"\bopen\s*\(\s*[rbf]?(['\"])([^'\"\n]+)\1\s*,\s*(?:mode\s*=\s*)?[rbf]?['\"][rbt]*[wax+]"
    r"|\bPath\s*\(\s*[rbf]?(['\"])([^'\"\n]+)\3\s*\)\s*\.\s*(?:write_text|write_bytes|touch|unlink)\b"
    r"|\b(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream|File\.write|IO\.write)"
    r"\s*\(\s*(['\"`])([^'\"`\n]+)\5"
)


def _scan(command):
    """Return (shell text, heredoc bodies). Comments are dropped, and each body is cut out.

    A "#" that starts a word outside quotes starts a comment. A heredoc body
    leaves the text, and the token __CRAFT_HEREDOC_<n>__ marks its place. A "$"
    inside single quotes becomes LITERAL_DOLLAR, so it is never expanded.
    """
    text = str(command)
    shell, bodies, pending = [], [], []
    quote = ""
    previous = "\n"
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\n" and not quote and pending:
            shell.append("\n")
            index += 1
            while pending and index <= len(text):
                end = text.find("\n", index)
                end = len(text) if end < 0 else end
                line = text[index:end]
                number, strip_tabs, delimiter = pending[0]
                if (line.lstrip("\t") if strip_tabs else line).rstrip("\r") == delimiter:
                    pending.pop(0)
                else:
                    bodies[number].append(line)
                index = end + 1
            previous = "\n"
            continue
        if quote:
            if char == "\\" and quote == '"' and index + 1 < len(text):
                shell.append(text[index:index + 2])
                index += 2
                continue
            quote = "" if char == quote else quote
            if quote == "'" and char == "$":
                char = LITERAL_DOLLAR
        elif char == "\\" and index + 1 < len(text):
            shell.append(text[index:index + 2])
            index += 2
            previous = "x"
            continue
        elif char in "'\"":
            quote = char
        elif char == "#" and (previous.isspace() or previous in ";&|()`"):
            end = text.find("\n", index)
            index = len(text) if end < 0 else end
            continue
        elif text.startswith("<<<", index):
            shell.append("<<<")
            index += 3
            previous = "<"
            continue
        elif char == "<":
            match = HEREDOC_MARK.match(text, index)
            if match:
                bodies.append([])
                pending.append((len(bodies) - 1, bool(match.group(1)), match.group(3)))
                shell.append("<< __CRAFT_HEREDOC_%d__" % (len(bodies) - 1))
                index = match.end()
                previous = "x"
                continue
        shell.append(char)
        previous = char
        index += 1
    return ("".join(shell), ["\n".join(body) for body in bodies])


def _simple_commands(text):
    """Return the simple commands of shell text as dicts.

    words, redirects, heredocs (body numbers), joiner (the operator before the
    command: "", ";", "&&", "||", "|", "&"), and depth (how many subshell
    parentheses are open).

    Returns None when the text cannot be split into words, for example an open quote.
    """
    lexer = shlex.shlex(text.replace("\\\n", " "), posix=True, punctuation_chars=SHELL_PUNCTUATION)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        return None

    def is_operator(token):
        return bool(token) and all(char in SHELL_PUNCTUATION for char in token)

    def new_command(joiner, depth):
        return {"words": [], "redirects": [], "heredocs": [], "joiner": joiner, "depth": depth}

    depth = 0
    commands = [new_command("", 0)]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not is_operator(token):
            following = tokens[index] if index < len(tokens) else ""
            if not (token.isdigit() and is_operator(following) and following[0] in "<>"):
                commands[-1]["words"].append(token)
            continue
        positions = [position for position in (token.find(">"), token.find("<")) if position >= 0]
        cut = 0 if token.startswith("&>") else min(positions, default=-1)
        if cut != 0:
            separator = token if cut < 0 else token[:cut]
            depth = max(0, depth + separator.count("(") - separator.count(")"))
            joiner = separator.replace("(", "").replace(")", "").replace("\n", ";").strip()
            commands.append(new_command(joiner or ";", depth))
        if cut < 0:
            continue
        operator = token[cut:]
        target = tokens[index] if index < len(tokens) and not is_operator(tokens[index]) else None
        if target is None:
            continue
        index += 1
        if operator.startswith("<<") and not operator.startswith("<<<"):
            heredoc = HEREDOC_TOKEN.match(target)
            if heredoc:
                commands[-1]["heredocs"].append(int(heredoc.group(1)))
        elif ">" in operator and not (operator.endswith(">&") and (target.isdigit() or target == "-")):
            commands[-1]["redirects"].append(target)
    return [command for command in commands if command["words"] or command["redirects"]]


def _command_words(words):
    """Return (assignments, words from the command name on, wrappers) past env, sudo, if, and the like."""
    assignments, wrappers = [], []
    index = 0
    while index < len(words):
        word = words[index]
        if ASSIGNMENT.match(word):
            assignments.append(word)
            index += 1
            continue
        if word in RESERVED_WORDS:
            index += 1
            continue
        name = os.path.basename(word)
        if name not in WRAPPERS:
            break
        wrappers.append(name)
        index += 1
        valued = WRAPPER_VALUES.get(name, ())
        while index < len(words) and WRAPPER_ARGUMENT.match(words[index]):
            if ASSIGNMENT.match(words[index]):
                assignments.append(words[index])
            index += 2 if words[index] in valued else 1
    return (assignments, words[index:], wrappers)


def _expand(target):
    """Return target with ~ and the set variables expanded. A single-quoted "$" stays literal."""
    return os.path.expandvars(os.path.expanduser(target))


def _resolve(target, base):
    """Return target as an absolute path against base, symlinks resolved, or None.

    '' stands for "somewhere here": it resolves to base itself. A target that
    starts with a variable that is not set (`"$TMPDIR/x"`) is None: its place
    is unknown, and the after-check covers it. A variable later in a relative
    path (`app/$NAME.py`) is kept as written, so the path stays in base.
    """
    expanded = _expand(target)
    if target == "":
        return os.path.realpath(str(base))
    if expanded.startswith("$") or "`" in expanded:
        return None
    path = pathlib.Path(expanded.replace(LITERAL_DOLLAR, "$"))
    if not path.is_absolute():
        path = pathlib.Path(base) / path
    return os.path.realpath(str(path))


def _resolve_all(target, bases):
    """Return target resolved against each base, without repeats and without unknowns."""
    return [path for path in dict.fromkeys(_resolve(target, base) for base in bases) if path]


def _is_unknown(target):
    """Return True when a target stands for a write to an unknown path in the directory."""
    return target == ""


def _operands(arguments, valued=(), valued_pattern=None):
    """Return the arguments that are not options, skipping the value of each valued option."""
    operands = []
    skip = False
    for argument in arguments:
        if skip:
            skip = False
        elif argument == "--":
            continue
        elif argument in valued or (valued_pattern is not None and valued_pattern.match(argument)):
            skip = True
        elif not argument.startswith("-") or argument == "-":
            operands.append(argument)
    return operands


def _in_place_targets(arguments):
    """Return the files a sed -i or perl -i call edits."""
    operands = _operands(arguments, valued=SCRIPT_FLAGS, valued_pattern=CODE_FLAG)
    has_script = any(argument in SCRIPT_FLAGS or CODE_FLAG.match(argument)
                     or argument.startswith(("--expression=", "--file=")) for argument in arguments)
    return operands if has_script else operands[1:]


def _git_subcommand(arguments):
    """Return (subcommand, its arguments) past git's own options."""
    rest = list(arguments)
    while rest and rest[0].startswith("-"):
        rest = rest[2:] if rest[0] in ("-C", "-c") else rest[1:]
    return (rest[0], rest[1:]) if rest else ("", [])


def _command_targets(name, arguments):
    """Return the paths a known writing command writes. '' stands for "somewhere"."""
    if name in ("tee", "rm", "mv"):
        return _operands(arguments)
    if name == "touch":
        return _operands(arguments, valued=("-d", "-t", "-r", "--date", "--reference"))
    if name == "truncate":
        return _operands(arguments, valued=("-s", "--size", "-r", "--reference"))
    if name in ("cp", "ln", "install"):
        for index, argument in enumerate(arguments):
            if argument in ("-t", "--target-directory") and index + 1 < len(arguments):
                return [arguments[index + 1]]
            if argument.startswith("--target-directory="):
                return [argument.split("=", 1)[1]]
        operands = _operands(arguments, valued=COPY_VALUED)
        if name == "install" and "-d" in arguments:
            return operands
        return operands[-1:] if len(operands) > 1 else []
    if name == "dd":
        return [argument[3:] for argument in arguments if argument.startswith("of=")]
    if name in ("sed", "perl") and any(IN_PLACE_FLAG.match(argument) for argument in arguments):
        return _in_place_targets(arguments)
    if name == "patch":
        return [] if "--dry-run" in arguments else [""]
    if name == "git":
        subcommand, rest = _git_subcommand(arguments)
        if subcommand == "apply" and not any(flag in rest for flag in GIT_READ_ONLY_APPLY):
            return [""]
        if subcommand == "checkout" and "--" in rest:
            return rest[rest.index("--") + 1:]
        if subcommand == "restore":
            staged_only = any(flag in rest for flag in ("--staged", "-S")) and not any(
                flag in rest for flag in ("--worktree", "-W"))
            return [] if staged_only else _operands(rest, valued=("-s", "--source"))
    if name == "find":
        if "-delete" in arguments:
            return [""]
        for index, argument in enumerate(arguments[:-1]):
            program = os.path.basename(arguments[index + 1])
            if argument in ("-exec", "-execdir", "-ok", "-okdir") and (
                    program in WRITE_COMMANDS or program in SHELLS or INTERPRETER.match(program)):
                return [""]
    return []


def _code_targets(code):
    """Return the paths that interpreter code writes. '' stands for a write to an unknown path."""
    paths = [match.group(2) or match.group(4) or match.group(6) for match in CODE_WRITE_PATHS.finditer(code)]
    if len(CODE_WRITES.findall(code)) > len(paths):
        paths.append("")
    return paths


def _interpreter_code(arguments, heredocs):
    """Return (code, script, script arguments) for an interpreter or shell call.

    code is what -c, -e, or a heredoc gives it. script is the file it runs.
    Both are '' when it reads its program from standard input, as in `... | sh`.
    """
    for index, argument in enumerate(arguments):
        if CODE_FLAG.match(argument) and index + 1 < len(arguments):
            return (arguments[index + 1], "", [])
        if argument == "-":
            break
        if not argument.startswith("-"):
            return ("", argument, arguments[index + 1:])
    return ("\n".join(heredocs), "", [])


def _is_read_only(name, arguments, redirects):
    """Return True when a simple command only reads: no redirect, and a read-only program."""
    if any(target != "/dev/null" for target in redirects):
        return False
    if not name or name in READ_ONLY:
        return True
    if name == "sed":
        return "-n" in arguments and not any(IN_PLACE_FLAG.match(argument) for argument in arguments)
    if name == "git":
        return _git_subcommand(arguments)[0] in GIT_READ_ONLY
    return False


def _reads_program_from_stdin(simple):
    """Return True when a simple command is a shell or interpreter that runs what it reads on stdin."""
    _assignments, words, _wrappers = _command_words(simple["words"])
    name = os.path.basename(words[0]) if words else ""
    if not (name in SHELLS or INTERPRETER.match(name)):
        return False
    code, script, _rest = _interpreter_code(words[1:], [])
    return not code and not script


def _data_positions(name, arguments, piped_to_shell):
    """Return the argument positions that hold data, not a command: messages, selectors, printed text."""
    if name in ("echo", "printf"):
        return set() if piped_to_shell else set(range(len(arguments)))
    data = set()
    start = 0
    if name == "git":
        subcommand, rest = _git_subcommand(arguments)
        if subcommand not in ("commit", "tag", "notes"):
            return data
        start, valued, joined = len(arguments) - len(rest), ("-m", "-F", "--message", "--file"), ("--message=", "--file=")
    elif name == "pytest" or (INTERPRETER.match(name) and "pytest" in arguments):
        start = arguments.index("pytest") + 1 if "pytest" in arguments else 0
        valued, joined = ("-k", "-m"), ()
    else:
        return data
    for index in range(start, len(arguments)):
        argument = arguments[index]
        if argument in valued:
            data.add(index + 1)
        elif argument.startswith(joined) or (name == "git" and argument[:2] in ("-m", "-F") and len(argument) > 2):
            data.add(index)
    return data


def _walk(command, bases, depth, effects):
    """Add what command does to effects. bases are the directories a relative path may mean.

    After `cd X`, a command joined by && or | runs in X only. After ;, ||, or
    inside parentheses, the cd may not have happened, so both directories count.
    """
    text, bodies = _scan(command)
    commands = _simple_commands(text)
    if commands is None:
        effects["unparsed"] = True
        return
    fallback = list(bases)
    pipeline = {"mentions": False, "unsafe": False}
    for position, simple in enumerate(commands):
        if simple["joiner"] not in ("&&", "|", "|&"):
            bases = fallback
        if simple["joiner"] not in ("|", "|&"):
            _close_pipeline(pipeline, effects)
        heredocs = [bodies[number] for number in simple["heredocs"] if number < len(bodies)]
        assignments, words, wrappers = _command_words(simple["words"])
        if words and words[0] in LOOP_HEADERS:
            continue
        name = os.path.basename(words[0]) if words else ""
        arguments = words[1:]
        following = commands[position + 1] if position + 1 < len(commands) else None
        piped_to_shell = bool(following) and following["joiner"] in ("|", "|&") and _reads_program_from_stdin(following)
        if not _is_read_only(name, arguments, simple["redirects"]):
            effects["read_only"] = False
        data = _data_positions(name, arguments, piped_to_shell)
        program_text = [words[0] if words else ""] + [word for index, word in enumerate(arguments) if index not in data]
        if name in SHELLS or INTERPRETER.match(name) or piped_to_shell:
            program_text += heredocs
        if any("craft-approve" in part for part in program_text + simple["redirects"]):
            effects["mentions"] = True
        piped = bool(following) and following["joiner"] in ("|", "|&")
        state_data = _data_positions(name, arguments, piped)
        state_text = [words[0] if words else ""] + [word for index, word in enumerate(arguments) if index not in state_data]
        state_text += simple["redirects"] + assignments + (heredocs if name in SHELLS or INTERPRETER.match(name) else [])
        for assignment in assignments:
            if STATE_WORDS.search(assignment):
                effects["state_vars"].add(assignment.split("=", 1)[0])
        if any(STATE_WORDS.search(part) for part in state_text) or any(
                "$" + variable in part or "${" + variable in part for variable in effects["state_vars"] for part in state_text):
            pipeline["mentions"] = True
        if any(word.startswith("CRAFT_HOOKS=") for word in assignments) or (
                name in DECLARERS and any(word.startswith("CRAFT_HOOKS=") for word in arguments)):
            effects["hooks"] = True
        plain = [argument for argument in arguments if not argument.startswith("-")]
        if name == "claude" and plain[:1] in (["plugin"], ["plugins"]) and (
                plain[1:2] in (["disable"], ["uninstall"], ["remove"])
                or (plain[1:2] == ["marketplace"] and plain[2:3] in (["remove"], ["rm"]))):
            effects["plugin_off"] = True
        program, program_arguments = name, arguments
        targets = _command_targets(name, arguments)
        if name in ("cd", "pushd"):
            destination = arguments[0] if arguments else "~"
            moved = _resolve_all(destination, bases) if destination != "-" else []
            if simple["depth"] > 0 or not moved:
                bases = fallback = list(dict.fromkeys(bases + moved))[:MAX_BASES]
            else:
                fallback = list(dict.fromkeys(fallback + moved))[:MAX_BASES]
                bases = moved
        elif name == "eval" or name in SHELLS:
            if name == "eval":
                code, script, rest = " ".join(arguments), "", []
            else:
                code, script, rest = _interpreter_code(arguments, heredocs)
            program, program_arguments = (os.path.basename(script), rest) if script else (program, arguments)
            if code and depth < 3:
                _walk(code.replace(LITERAL_DOLLAR, "$"), bases, depth + 1, effects)
            elif not code and not script:
                targets.append("")
        elif INTERPRETER.match(name):
            code, script, rest = _interpreter_code(arguments, heredocs)
            program, program_arguments = (os.path.basename(script), rest) if script else (program, arguments)
            if code:
                targets += _code_targets(code)
            elif not script:
                targets.append("")
        if program in CRAFT_PROGRAMS:
            effects["programs"].append({"program": program, "arguments": program_arguments})
        if not _is_read_only(name, arguments, simple["redirects"]) and not _is_state_safe_program(
                program, program_arguments) and not _is_backup_restore(name, arguments, bases):
            pipeline["unsafe"] = True
        if "xargs" in wrappers and (name in WRITE_COMMANDS or name in SHELLS or INTERPRETER.match(name)):
            targets.append("")
        if any(_is_unknown(target) for target in targets + simple["redirects"]):
            effects["unknown"] = True
        resolved = [path for target in targets for path in _resolve_all(target, bases)]
        redirects = [path for target in simple["redirects"] for path in _resolve_all(target, bases)]
        if resolved or redirects:
            effects["writers"].append(
                {"name": name, "arguments": arguments, "targets": resolved, "redirects": redirects, "bases": list(bases)}
            )
            effects["writes"] += resolved + redirects
    _close_pipeline(pipeline, effects)


def _close_pipeline(pipeline, effects):
    """Mark a state write when one pipeline names a state file and runs a command that can write. Then reset it."""
    if pipeline["mentions"] and pipeline["unsafe"]:
        effects["state_write"] = True
    pipeline["mentions"] = pipeline["unsafe"] = False


def _is_backup_restore(name, arguments, bases):
    """Return True for `cp <a .claude/craft/backups/<sha256>> <a path outside .claude/craft>`."""
    operands = _operands(arguments, valued=COPY_VALUED) if name == "cp" else []
    if len(operands) != 2:
        return False
    sources = _resolve_all(operands[0], bases)
    targets = _resolve_all(operands[1], bases)
    return bool(sources and targets) and all(BACKUP_PATH.search(path) for path in sources) and not any(
        CRAFT_STATE_PATH.search(path) for path in targets)


def bash_effects(command, cwd=None):
    """Return what a Bash command does, read from its text. Never raises.

    writes      absolute paths, symlinks resolved, of the files it writes by a recognised form
    writers     one dict per simple command that writes: name, arguments, targets, redirects, bases
    programs    one dict per run of craft-session, craft-spec, or craft_state.py: program, arguments
    approve     True when "craft-approve" is in a command part (not a commit message,
                a test selector, or printed text) and a command in the text is not read-only
    state_write True when one pipeline names a .claude/craft path or specs/ACTIVE, in a
                command part, an assignment, or a variable set to one, and runs a command
                that is neither read-only, nor a bin/ program that writes state honestly
                (craft-check, craft-spec status, ...), nor `git add`, nor the cp of a backup
    hooks       True when it assigns CRAFT_HOOKS
    plugin_off  True when it runs `claude plugin disable|uninstall|remove` or `plugin marketplace remove`
    unknown     True when it writes to a path the text does not show (reported as the directory)
    unparsed    True when the text cannot be split into words
    """
    effects = {
        "writes": [],
        "writers": [],
        "programs": [],
        "approve": False,
        "mentions": False,
        "state_vars": set(),
        "state_write": False,
        "hooks": False,
        "plugin_off": False,
        "unknown": False,
        "unparsed": False,
        "read_only": True,
    }
    try:
        _walk(str(command), [os.path.realpath(str(cwd or os.getcwd()))], 0, effects)
        effects["approve"] = effects["mentions"] and not effects["read_only"]
    except Exception:
        pass
    return effects


def is_restore(writer, target, record):
    """Return True when writer, one simple command of bash_effects(), only restores target as record says.

    clean before    `git checkout -- <path>`, or `git restore <path>` from the index or from HEAD
    absent before   `rm <path>`, and so for a file deleted before the call
    dirty before    `cp <its backup> <path>`
    """
    try:
        before = record.get("before")
        if target not in writer["targets"]:
            return False
        if before == "clean":
            subcommand, rest = _git_subcommand(writer["arguments"]) if writer["name"] == "git" else ("", [])
            if subcommand == "checkout":
                return rest[:1] == ["--"]
            sources = [rest[index + 1] for index, argument in enumerate(rest[:-1]) if argument in ("-s", "--source")]
            sources += [argument.split("=", 1)[1] for argument in rest if argument.startswith("--source=")]
            return subcommand == "restore" and all(source == "HEAD" for source in sources)
        if before in ("absent", "deleted"):
            return writer["name"] == "rm"
        backup = record.get("backup")
        if writer["name"] != "cp" or not backup:
            return False
        sources = _operands(writer["arguments"], valued=COPY_VALUED)[:-1]
        return len(sources) == 1 and os.path.realpath(backup) in _resolve_all(sources[0], writer["bases"])
    except Exception:
        return False


# ---------------------------------------------------------------------------
# What a Bash call changed: snapshots, backups, and gated writes
# ---------------------------------------------------------------------------

BIG_FILE = 1024 * 1024
BACKUP_LIMIT = 20 * 1024 * 1024
SNAPSHOT_MAX_AGE = 3600
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def content_digest(path):
    """Return the SHA-256 of a file, "big:<size>:<mtime>" above 1 MB, or '' when it is missing."""
    try:
        stat = os.stat(str(path))
        if stat.st_size > BIG_FILE:
            return "big:%d:%d" % (stat.st_size, stat.st_mtime_ns)
        return file_digest(path)
    except Exception:
        return ""


def _git(arguments, cwd=None, data=None, timeout=5):
    """Run one read-only git command in the host repository. Return stdout as bytes, or None."""
    try:
        result = subprocess.run(
            ["git"] + list(arguments),
            cwd=str(host_root(cwd)),
            input=data,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"),
        )
        return result.stdout if result.returncode == 0 else None
    except Exception:
        return None


def changed_files(cwd=None, untracked=None):
    """Return {path: content_digest} for the changed, non-ignored files outside .claude/. Never raises.

    The paths are relative to the host repository. A deleted file has ''.
    When untracked is a set, the untracked paths are added to it.
    Returns None outside a git work tree, or when git does not answer.
    """
    try:
        output = _git(["status", "--porcelain", "-z", "--untracked-files=all"], cwd)
        if output is None:
            return None
        root = host_root(cwd)
        files = {}
        rename_source = False
        for field in output.decode("utf-8", "surrogateescape").split("\0"):
            path = field if rename_source else field[3:]
            rename_source = not rename_source and ("R" in field[:2] or "C" in field[:2])
            if path and not path.startswith(".claude/"):
                files[path] = content_digest(root / path)
                if field[:2] == "??" and untracked is not None:
                    untracked.add(path)
        return files
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Stale checks: a fingerprint of the files a check ran against
# ---------------------------------------------------------------------------


FINGERPRINT_SECONDS = 4


def _blob_id(data):
    """Return the git blob id of data."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _plain_name(path):
    """Return True when `git hash-object --stdin-paths` reads path back unchanged."""
    return not (path.startswith('"') or "\n" in path or path.endswith("\r"))


def _working_blob(path, root, cwd, deadline):
    """Return the git blob id of the working-tree file at path. Never raises.

    A symlink is its link text. Otherwise git hashes the file, filters
    included, so a commit keeps the id. After the deadline, or when git does
    not answer, the id of the raw bytes stands in.
    """
    full = root / path
    try:
        if os.path.islink(str(full)):
            return _blob_id(os.fsencode(os.readlink(str(full))))
        remaining = deadline - time.monotonic()
        if remaining > 0.5:
            output = _git(["hash-object", "--", path], cwd, timeout=remaining)
            if output and output.strip():
                return output.decode().strip()
        return _blob_id(full.read_bytes())
    except Exception:
        return "unreadable:" + file_digest(full)


def tree_fingerprint(cwd=None):
    """Return a SHA-256 of the content of every file outside .claude/, or None. Never raises.

    The fingerprint covers the blobs at HEAD (`git ls-tree -r HEAD`),
    replaced by the working-tree blob of each path that `git status` lists
    (modified, added, untracked and not ignored). A deleted path is dropped.
    It depends on content only, so committing the tested code keeps it equal.
    None outside a git work tree, when HEAD exists but git cannot list it, or
    when git does not answer. One odd path never makes the result None: that
    path alone falls back to its own hash. The whole call has one deadline of
    FINGERPRINT_SECONDS.

    This runs git a few times. Call it from craft-check, the Stop hook, and
    craft-ui-state only, never from a per-tool-call hook.
    """
    try:
        deadline = time.monotonic() + FINGERPRINT_SECONDS
        changed = changed_files(cwd)
        if changed is None:
            return None
        root = host_root(cwd)
        listing = _git(["ls-tree", "-r", "-z", "HEAD"], cwd, timeout=max(1, deadline - time.monotonic()))
        if listing is None:
            if _git(["rev-parse", "--verify", "-q", "HEAD"], cwd) is not None:
                return None
            listing = b""
        blobs = {}
        for entry in listing.decode("utf-8", "surrogateescape").split("\0"):
            meta, _tab, path = entry.partition("\t")
            if path and not path.startswith(".claude/"):
                blobs[path] = meta.split(" ")[-1]
        batch = []
        for path in sorted(changed):
            full = str(root / path)
            if not os.path.lexists(full):
                blobs.pop(path, None)
            elif os.path.islink(full):
                blobs[path] = _working_blob(path, root, cwd, deadline)
            elif os.path.isdir(full):
                continue
            elif _plain_name(path):
                batch.append(path)
            else:
                blobs[path] = _working_blob(path, root, cwd, deadline)
        output = None
        if batch:
            output = _git(
                ["hash-object", "--stdin-paths"], cwd,
                data=("\n".join(batch) + "\n").encode("utf-8", "surrogateescape"),
                timeout=max(1, deadline - time.monotonic()),
            )
        names = output.decode().split() if output is not None else []
        if len(names) == len(batch):
            blobs.update(zip(batch, names))
        else:
            for path in batch:
                blobs[path] = _working_blob(path, root, cwd, deadline)
        digest = hashlib.sha256()
        for path in sorted(blobs):
            digest.update(path.encode("utf-8", "surrogateescape") + b"\0" + blobs[path].encode() + b"\n")
        return digest.hexdigest()
    except Exception:
        return None


def same_command(first, second):
    """Return True when two commands are equal after collapsing whitespace."""
    return " ".join(str(first).split()) == " ".join(str(second).split())


def check_is_stale(check, current):
    """Return True when a recorded check ran against other files than current.

    A check with no tree (recorded outside git, or before this release), or a
    current of None, is never stale.
    """
    tree = check.get("tree") if isinstance(check, dict) else None
    return bool(tree and current and tree != current)

_UNSET = object()


def checkpoint_evidence(cwd=None, recorded=None, current=_UNSET, checkpoint=None):
    """Return (check, state) for Gate A's tests evidence; state is ok, failed, stale, or not run.

    With a checkpoint command, the evidence is the newest check run from the
    repository root whose command equals it (whitespace collapsed), of any exit
    code. A check with no `cwd` field counts as run from the root. Without a
    checkpoint, it is the newest green check. It is ok only when it exited 0
    and its tree equals current. The Stop hook and the board both call this.
    current is the fingerprint now; it is computed only when needed.
    """
    recorded = checks(cwd) if recorded is None else recorded
    checkpoint = (checkpoint_command(cwd) if checkpoint is None else checkpoint).strip()
    if checkpoint:
        found = [c for c in recorded if not c.get("cwd") and same_command(c.get("command", ""), checkpoint)]
    else:
        found = [c for c in recorded if c.get("exit_code") == 0]
    if not found:
        return (None, "not run")
    check = found[-1]
    if check.get("exit_code") != 0:
        return (check, "failed")
    if check.get("tree"):
        if current is _UNSET:
            current = tree_fingerprint(cwd)
        if check_is_stale(check, current):
            return (check, "stale")
    return (check, "ok")



def head_digest(path, cwd=None):
    """Return the SHA-256 of path as committed at HEAD, or '' when git has no such file."""
    blob = _git(["cat-file", "blob", "HEAD:" + str(path)], cwd)
    return hashlib.sha256(blob).hexdigest() if blob is not None else ""


def backup_files(files, cwd=None, untracked=()):
    """Copy each tracked file whose digest is a SHA-256 to .claude/craft/backups/<sha256>, once. Never raises.

    An untracked file is never copied: it may hold a secret, and git never had
    it. A file over 1 MB has no SHA-256 digest, so it is not copied. One call
    copies at most BACKUP_LIMIT bytes.
    """
    folder = craft_dir(cwd) / "backups"
    root = host_root(cwd)
    copied = 0
    for path, digest in files.items():
        target = folder / str(digest)
        if path in untracked or not SHA256_HEX.match(str(digest)) or target.exists():
            continue
        temporary = folder / ("%s.%d.tmp" % (digest, os.getpid()))
        try:
            data = (root / path).read_bytes()
            if hashlib.sha256(data).hexdigest() != digest or copied + len(data) > BACKUP_LIMIT:
                continue
            folder.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(data)
            os.replace(str(temporary), str(target))
            copied += len(data)
        except Exception:
            try:
                temporary.unlink()
            except Exception:
                pass


def prune_backups(records, cwd=None):
    """Delete the backups that no record in records names. Never raises."""
    try:
        keep = {os.path.basename(str(record.get("backup", ""))) for record in records.values() if isinstance(record, dict)}
        for backup in (craft_dir(cwd) / "backups").glob("*"):
            if backup.name not in keep:
                backup.unlink()
    except Exception:
        pass


def approval_snapshot(cwd=None):
    """Return approval.json as it is now, as a dict. Never raises.

    exists, mode, size, mtime_ns, and data: the bytes in base64, or None when
    the file cannot be read.
    """
    path = state_path(APPROVAL_FILE, cwd)
    try:
        stat = os.stat(str(path))
    except FileNotFoundError:
        return {"exists": False}
    except Exception:
        return {"exists": True, "mode": None, "size": None, "mtime_ns": None, "data": None}
    snapshot = {"exists": True, "mode": stat.st_mode & 0o7777, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    try:
        snapshot["data"] = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        snapshot["data"] = None
    return snapshot


def restore_approval(prior, cwd=None):
    """Put approval.json back as prior says. Return True when it had changed and was put back.

    A file that is unreadable now counts as changed. When prior itself could
    not be read, a changed file is deleted, because its old bytes are unknown.
    """
    try:
        if not isinstance(prior, dict) or "exists" not in prior:
            return False
        current = approval_snapshot(cwd)
        if current == prior and (current.get("data") is not None or not current.get("exists")):
            return False
        path = state_path(APPROVAL_FILE, cwd)
        if not prior["exists"] or prior.get("data") is None:
            if not current.get("exists") or current == prior:
                return False
            path.unlink()
            return True
        temporary = path.with_name("%s.%d.tmp" % (path.name, os.getpid()))
        temporary.write_bytes(base64.b64decode(prior["data"]))
        if prior.get("mode") is not None:
            os.chmod(str(temporary), prior["mode"])
        os.replace(str(temporary), str(path))
        return True
    except Exception:
        return False


def _snapshot_path(tool_use_id, cwd=None):
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", str(tool_use_id or "none"))[:120] or "none"
    return craft_dir(cwd) / "snapshots" / (name + ".json")


def save_bash_snapshot(tool_use_id, snapshot, cwd=None):
    """Store the state before one Bash call in its own file. Prune files older than an hour. True on success."""
    try:
        folder = craft_dir(cwd) / "snapshots"
        if folder.is_dir():
            cutoff = datetime.datetime.now().timestamp() - SNAPSHOT_MAX_AGE
            for old in folder.glob("*.json"):
                try:
                    if old.stat().st_mtime < cutoff:
                        old.unlink()
                except Exception:
                    pass
        return _write_json_atomic(_snapshot_path(tool_use_id, cwd), snapshot)
    except Exception:
        return False


def pop_bash_snapshot(tool_use_id, cwd=None):
    """Remove and return the snapshot of one Bash call, or None when there is none."""
    path = _snapshot_path(tool_use_id, cwd)
    snapshot = _read_json(path, None)
    try:
        path.unlink()
    except Exception:
        pass
    return snapshot if isinstance(snapshot, dict) else None


def _record_is_current(record, cwd=None):
    """Return True while a gated-write record belongs to the active spec, and no approval came after it."""
    if not isinstance(record, dict) or record.get("spec") != active_spec_name(cwd):
        return False
    approvals = spec_approvals(record.get("spec"), cwd)
    return not approvals or str(approvals[-1].get("approved_at", "")) < str(record.get("at", ""))


def gated_writes(cwd=None):
    """Return {path: record} for the current gated writes. {} on any problem.

    record: before (clean, absent, deleted, or dirty), sha (dirty only), backup
    (dirty only, '' when none), blocking, at, and spec.
    """
    recorded = read_session(cwd).get("gated_writes")
    if not isinstance(recorded, dict):
        return {}
    return {path: record for path, record in recorded.items() if _record_is_current(record, cwd)}


def gated_records(before, after, cwd=None, untracked=()):
    """Return {path: record} for the files whose digest differs between two changed_files() results.

    untracked holds the paths that were untracked before the call. Such a file
    that existed and changed has no backup: it is reported, and never blocks.
    """
    changed = [path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)]
    unseen = [path for path in changed if path not in before]
    tracked = set()
    if unseen:
        output = _git(["ls-files", "-z", "--"] + unseen, cwd)
        tracked = set(output.decode("utf-8", "surrogateescape").split("\0")) if output else set()
    stamp, spec = now(), active_spec_name(cwd)
    records = {}
    for path in changed:
        record = {"at": stamp, "spec": spec, "blocking": True, "sha": "", "backup": ""}
        digest = before.get(path)
        if digest is None:
            record["before"] = "clean" if path in tracked else "absent"
        elif digest == "":
            record["before"] = "deleted"
        elif path in untracked:
            record.update(before="untracked", sha=digest, blocking=False)
        else:
            backup = craft_dir(cwd) / "backups" / digest
            record.update(before="dirty", sha=digest)
            record["backup"] = str(backup) if SHA256_HEX.match(digest) and backup.is_file() else ""
            record["blocking"] = bool(record["backup"])
        records[path] = record
    return records


def add_gated_writes(records, cwd=None):
    """Record files a Bash call changed while the gate was shut. The first record of a path stays."""
    try:
        session = read_session(cwd)
        recorded = gated_writes(cwd)
        for path, record in records.items():
            recorded.setdefault(path, record)
        session["gated_writes"] = recorded
        return _write_json_atomic(state_path(SESSION_FILE, cwd), session)
    except Exception:
        return False


def is_restored(record, digest):
    """Return True when a file is back as it was. digest is its changed_files() entry, None when absent."""
    if record.get("before") in ("dirty", "untracked"):
        return digest == record.get("sha")
    if record.get("before") == "deleted":
        return digest == ""
    return digest is None


def settle_gated_writes(cwd=None, current=None):
    """Drop the gated writes that are restored or no longer current. Return the rest. Never raises.

    current is a changed_files() result. Returns {} when git does not answer.
    """
    try:
        session = read_session(cwd)
        recorded = session.get("gated_writes")
        if not isinstance(recorded, dict) or not recorded:
            return {}
        current = changed_files(cwd) if current is None else current
        if current is None:
            return {}
        left = {
            path: record
            for path, record in recorded.items()
            if _record_is_current(record, cwd) and not is_restored(record, current.get(path))
        }
        if left != recorded:
            session["gated_writes"] = left
            _write_json_atomic(state_path(SESSION_FILE, cwd), session)
            prune_backups(left, cwd)
        return left
    except Exception:
        return {}


def clear_gated_writes(cwd=None):
    """Forget the gated writes and the Stop refusal count, and delete the backups. True on success."""
    try:
        session = read_session(cwd)
        if session.pop("gated_writes", None) is None and session.pop("unreverted_refusals", None) is None:
            return True
        session.pop("unreverted_refusals", None)
        prune_backups({}, cwd)
        return _write_json_atomic(state_path(SESSION_FILE, cwd), session)
    except Exception:
        return False


def blocking_writes(cwd=None):
    """Return {path: record} for the gated writes that block a stop now. {} when none, or the gate is open."""
    if not read_session(cwd).get("gated_writes") or not gate_shut(cwd):
        return {}
    return {path: record for path, record in settle_gated_writes(cwd).items() if record.get("blocking")}


def set_refusals(count, cwd=None, key="unreverted_refusals"):
    """Store how many stops in a row were refused (for unreverted files, or under another key). True on success."""
    try:
        session = read_session(cwd)
        if session.get(key, 0) == count:
            return True
        session[key] = count
        return _write_json_atomic(state_path(SESSION_FILE, cwd), session)
    except Exception:
        return False


def restore_command(path, record, cwd=None):
    """Return the one command that restores path as record says, or '' when none can."""
    full = shlex.quote(str(host_root(cwd) / path))
    before = record.get("before")
    if before == "clean":
        return "git restore --source=HEAD --staged --worktree -- " + full
    if before in ("absent", "deleted"):
        return "rm " + full
    if record.get("backup"):
        return "cp %s %s" % (shlex.quote(record["backup"]), full)
    return ""


# ---------------------------------------------------------------------------
# findings.json
# ---------------------------------------------------------------------------


def read_findings(cwd=None):
    """Return every recorded finding. [] on any problem."""
    data = _read_json(state_path(FINDINGS_FILE, cwd), {})
    if not isinstance(data, dict):
        return []
    findings = data.get("findings")
    if not isinstance(findings, list):
        return []
    return [finding for finding in findings if isinstance(finding, dict)]


def add_finding(finding, cwd=None):
    """Append one adjudicated finding. Return True on success."""
    try:
        if not isinstance(finding, dict):
            return False
        data = _read_json(state_path(FINDINGS_FILE, cwd), {})
        if not isinstance(data, dict):
            data = {}
        findings = data.get("findings")
        if not isinstance(findings, list):
            findings = []
        record = dict(finding)
        record.setdefault("recorded_at", now())
        findings.append(record)
        data["findings"] = findings[-MAX_FINDINGS:]
        return _write_json_atomic(state_path(FINDINGS_FILE, cwd), data)
    except Exception:
        return False


def update_finding(finding_id, changes, cwd=None):
    """Merge changes into the finding with this id. Return True when one was changed."""
    try:
        data = _read_json(state_path(FINDINGS_FILE, cwd), {})
        findings = data.get("findings") if isinstance(data, dict) else None
        if not isinstance(findings, list):
            return False
        changed = False
        for finding in findings:
            if isinstance(finding, dict) and str(finding.get("id")) == str(finding_id):
                finding.update(changes)
                finding["updated_at"] = now()
                changed = True
        return changed and _write_json_atomic(state_path(FINDINGS_FILE, cwd), data)
    except Exception:
        return False


def read_reviews(cwd=None):
    """Return the recorded review rounds, oldest first. [] on any problem."""
    data = _read_json(state_path(REVIEWS_FILE, cwd), {})
    rounds = data.get("reviews") if isinstance(data, dict) else None
    return [item for item in rounds if isinstance(item, dict)] if isinstance(rounds, list) else []


def add_review(review, cwd=None):
    """Append one review round: lenses, decision, counts. Return True on success."""
    try:
        data = _read_json(state_path(REVIEWS_FILE, cwd), {})
        if not isinstance(data, dict):
            data = {}
        rounds = data.get("reviews") if isinstance(data.get("reviews"), list) else []
        record = dict(review)
        record.setdefault("at", now())
        record.setdefault("spec", active_spec_name(cwd))
        rounds.append(record)
        data["reviews"] = rounds[-MAX_FINDINGS:]
        return _write_json_atomic(state_path(REVIEWS_FILE, cwd), data)
    except Exception:
        return False


def open_findings(cwd=None):
    """Return the findings that are not closed."""
    return [
        finding
        for finding in read_findings(cwd)
        if str(finding.get("state", "open")).lower() not in ("closed", "resolved", "dismissed", "rejected", "fixed")
    ]


# ---------------------------------------------------------------------------
# Gate B: the review state, and the lens floor
# ---------------------------------------------------------------------------

BLOCKING_SEVERITIES = ("critical", "high")
LENS_SECONDS = 4
UNTRACKED_READ_LIMIT = 200_000
DOC_SUFFIXES = (".md", ".rst", ".txt")
CONCURRENCY_CODE = re.compile(
    r"^\+.*(\basync\s+def\b|\basync\s+(function\b|\()|\bawait\s|\basyncio\.|TaskGroup|\bgather\(|create_task\(|"
    r"run_in_threadpool|to_thread\(|\bgo\s+func\b|\bgo\s+[\w.]+\(|errgroup|sync\.(WaitGroup|Mutex|RWMutex)|"
    r"\bchan\b|make\(chan|CompletableFuture|ExecutorService|Executors\.|@Async|parallelStream|\bMono<|\bFlux<|"
    r"VirtualThread|Promise\.(all|allSettled|race|any)\(|worker_threads|new Worker\(|ThreadPoolExecutor|"
    r"ProcessPoolExecutor|multiprocessing\.|concurrent\.futures|\bThread\(|threading\.Thread|Semaphore\(|"
    r"\b(launch|async)\s*\{|new Fiber\()",
    re.M,
)
# Each lens, the path sets that earn it, in the order the floor lists them.
LENS_PATH_SETS = (
    ("logic", ("money", "migrations", "tests", "services")),
    ("security", ("views", "auth")),
    ("query", ("models", "migrations")),
)


def _text(output):
    """Return git output as text."""
    return output.decode("utf-8", "surrogateescape") if output else ""


def head_commit(cwd=None):
    """Return the HEAD commit id of the host repository, or None."""
    return resolve_commit("HEAD", cwd)


def resolve_commit(ref, cwd=None):
    """Return the commit id that ref names, or None. A ref that starts with "-" is no ref."""
    output = _git(["rev-parse", "--verify", "-q", "--end-of-options", str(ref) + "^{commit}"], cwd)
    return output.decode().strip() if output and output.strip() else None


def _changed_since(base, cwd, deadline):
    """Return (paths, added, complete) since base, or None when git does not answer.

    base is a commit id, or None when HEAD is unborn (every file is then new).
    paths are the committed, uncommitted and untracked paths outside .claude/,
    with both names of a rename. added is [(path, line)] for every added line,
    untracked files included. complete is False when the deadline stopped the read.
    """
    def left():
        return max(1, deadline - time.monotonic())

    scope = ["--", ".", ":(exclude).claude"]
    plain = ["-c", "core.quotePath=false"]
    if base:
        names = _git(plain + ["diff", "--name-only", "-z", "--no-renames", "--end-of-options", base] + scope, cwd, timeout=left())
        if names is None:
            return None
        paths = [name for name in _text(names).split("\0") if name]
        others = _git(["ls-files", "-z", "--others", "--exclude-standard"] + scope, cwd, timeout=left())
    else:
        paths = []
        others = _git(["ls-files", "-z", "--cached", "--others", "--exclude-standard"] + scope, cwd, timeout=left())
    untracked = [name for name in _text(others).split("\0") if name and not name.startswith(".claude/")]
    paths += [name for name in untracked if name not in paths]
    added, current, complete = [], "", True
    if base:
        patch = _git(plain + ["diff", "-U0", "--no-color", "--no-renames", "--end-of-options", base] + scope, cwd, timeout=left())
        for line in _text(patch).splitlines():
            if line.startswith("+++ "):
                current = (line[6:] if line.startswith("+++ b/") else line[4:]).split("\t")[0]
            elif line.startswith("+"):
                added.append((current, line))
    root = host_root(cwd)
    for name in untracked:
        if time.monotonic() > deadline:
            complete = False
            break
        try:
            full = root / name
            if full.is_symlink() or full.stat().st_size > UNTRACKED_READ_LIMIT:
                continue
            added += [(name, "+" + row) for row in full.read_text(encoding="utf-8", errors="replace").splitlines()]
        except OSError:
            continue
    return paths, added, complete


def lens_floor(cwd=None, base=None, seconds=LENS_SECONDS):
    """Return the lenses a review must cover, as [{"lens", "reason"}]. Never raises.

    spec and style always. The rest come from the changed paths since base
    (default: the session's `base`, then HEAD): committed, uncommitted and
    untracked, .claude/ excluded, both names of a rename. A base that names no
    commit falls back to HEAD (untracked files only when HEAD is unborn), and
    the spec lens says so. The path sets come from craft_stack.globs_for
    (config/paths.json plus each stack). concurrency comes from added lines
    that match CONCURRENCY_CODE. logic and security always stand when the
    active spec says Risk: high. Each lens carries one reason that names the
    path, line, or rule that caused it. When git does not answer, only spec and
    style stand. Runs git a few times under one deadline of `seconds`: call it
    from the Stop hook and the board only. When the deadline stops the work,
    the spec lens says `floor incomplete`.
    """
    floor = [
        {"lens": "spec", "reason": "every task and project change"},
        {"lens": "style", "reason": "every task and project change"},
    ]

    def note(text):
        floor[0]["reason"] += "; " + text

    try:
        # Imported here: craft_stack imports this module, so a top-level import is circular.
        import craft_stack

        deadline = time.monotonic() + seconds
        wanted = str(base or read_session(cwd).get("base") or "HEAD")
        sha = resolve_commit(wanted, cwd)
        if sha is None:
            sha = head_commit(cwd)
            if wanted != "HEAD":
                note("base %s not found; floor from HEAD" % wanted)
        changed = _changed_since(sha, cwd, deadline)
        if changed is None:
            return floor
        paths, added, complete = changed
        found = craft_stack.detect(cwd)
        for lens, keys in LENS_PATH_SETS:
            hit = None
            for key in keys:
                globs = craft_stack.globs_for(key, cwd, found)
                for path in paths:
                    if time.monotonic() > deadline:
                        complete = False
                        break
                    if path_matches(path, globs):
                        hit = "%s path %s" % (key, path)
                        break
                if hit:
                    break
            if hit:
                floor.append({"lens": lens, "reason": hit})
        for path, line in added:
            if time.monotonic() > deadline:
                complete = False
                break
            if not path.endswith(DOC_SUFFIXES) and CONCURRENCY_CODE.search(line):
                floor.append({"lens": "concurrency", "reason": "%s adds concurrent code: %s" % (path, line[1:].strip()[:60])})
                break
        if spec_progress(cwd).get("risk") == "high":
            have = {entry["lens"] for entry in floor}
            for lens in ("logic", "security"):
                if lens not in have:
                    floor.append({"lens": lens, "reason": "Risk: high"})
        if not complete:
            note("floor incomplete: the time limit stopped the diff read")
    except Exception:
        pass
    return floor


def reviewer_spawns(cwd=None):
    """Return the reviewer spawns recorded in session.json: [{"agent", "at"}]."""
    spawns = read_session(cwd).get("spawns")
    return [item for item in spawns if isinstance(item, dict)] if isinstance(spawns, list) else []


def record_spawn(agent, cwd=None, at=None):
    """Append one reviewer spawn to session.json `spawns`. True on success."""
    try:
        session = read_session(cwd)
        spawns = session.get("spawns") if isinstance(session.get("spawns"), list) else []
        session["spawns"] = (spawns + [{"agent": str(agent), "at": at or now()}])[-200:]
        return _write_json_atomic(state_path(SESSION_FILE, cwd), session)
    except Exception:
        return False


def counted_rounds(reviews, spec_name, spawns):
    """Return the review rounds of the spec that a reviewer was really spawned for.

    Only a round whose spec is exactly spec_name counts. It also needs one of
    the reviewers it names (compared by short name) to have a recorded spawn
    after the previous counted round. The first round needs any spawn.
    """
    counted, since = [], ""
    for item in reviews:
        if (item.get("spec") or "") != (spec_name or ""):
            continue
        names = {str(name).rsplit(":", 1)[-1] for name in item.get("reviewers") or []}
        spawned = [
            spawn for spawn in spawns
            if str(spawn.get("agent", "")).rsplit(":", 1)[-1] in names and str(spawn.get("at", "")) > since
        ]
        if spawned:
            counted.append(item)
            since = str(item.get("at", ""))
    return counted


def missing_lenses(rounds, floor):
    """Return the lenses of floor that no round in rounds ran, in floor order."""
    covered = set()
    for item in rounds:
        lenses = item.get("lenses")
        if isinstance(lenses, list):
            covered.update(str(lens).strip().lower() for lens in lenses)
    return [entry["lens"] for entry in floor if entry["lens"] not in covered]


def gate_b(findings, reviews, spec_name, floor=None, spawns=()):
    """Return the Gate B state of the active spec. One answer for the Stop hook and the board.

    state is not run, changes requested, in review, or green. A round counts
    only when its spec is exactly spec_name and a reviewer it names was
    spawned (see counted_rounds). blocking counts the Critical and High
    findings that are confirmed, open, or still proposed; blocking_ids names
    them and proposed_ids says which were never adjudicated. missing lists the
    floor lenses no counted round ran. rounds counts the rounds of the spec,
    counted the ones that count.
    """
    def ours(item):
        return not spec_name or item.get("spec") in (spec_name, None, "")

    rounds = counted_rounds(reviews, spec_name, spawns)
    last = rounds[-1] if rounds else None
    findings = [finding for finding in findings if ours(finding)]
    blocking = [
        finding for finding in findings
        if str(finding.get("severity", "")).lower() in BLOCKING_SEVERITIES
        and str(finding.get("state", "open")).lower() in ("confirmed", "open", "proposed")
    ]
    proposed = [finding for finding in findings if str(finding.get("state", "")).lower() == "proposed"]
    missing = missing_lenses(rounds, floor) if floor else []
    if last is None:
        state = "not run"
    elif blocking:
        state = "changes requested"
    elif missing:
        state = "in review"
    elif last.get("decision") == "APPROVE" and not proposed:
        state = "green"
    else:
        state = "in review"
    return {
        "state": state, "green": state == "green", "last_round": last, "blocking": len(blocking),
        "blocking_ids": [str(finding.get("id", "?")) for finding in blocking],
        "proposed_ids": [
            str(finding.get("id", "?")) for finding in blocking if str(finding.get("state", "")).lower() == "proposed"
        ],
        "proposed": len(proposed),
        "rounds": len([item for item in reviews if (item.get("spec") or "") == (spec_name or "")]),
        "counted": len(rounds),
        "missing": missing, "floor": [entry["lens"] for entry in floor or []],
    }


# ---------------------------------------------------------------------------
# Path matching
# ---------------------------------------------------------------------------


def load_paths():
    """Return the whole of config/paths.json. {} on any problem."""
    global _paths_cache
    if _paths_cache is None:
        data = _read_json(PATHS_CONFIG, {})
        _paths_cache = data if isinstance(data, dict) else {}
    return _paths_cache


def globs_for(key):
    """Return the glob list under one key of config/paths.json. [] when unknown.

    An empty list means the hook has no opinion, so the call is allowed.
    """
    try:
        value = load_paths().get(key)
        if not isinstance(value, list):
            return []
        return [glob for glob in value if isinstance(glob, str) and glob]
    except Exception:
        return []


def path_matches(path, globs):
    """Return True when path matches any glob in globs.

    Two rules, and no others:

    * fnmatch does the matching, so "*" crosses a directory separator. Write
      "*/tests/*" and "tests/*" as two patterns when you mean both.
    * A glob that holds no "/" is also matched against the file name alone, so
      "test_*.py" matches "apps/wallet/tests/test_limit.py".

    Returns False on any problem, which means "allow".
    """
    try:
        if not path or not globs:
            return False
        text = str(path).replace("\\", "/")
        while text.startswith("./"):
            text = text[2:]
        name = text.rsplit("/", 1)[-1]
        for glob in globs:
            if not isinstance(glob, str) or not glob:
                continue
            if fnmatch.fnmatch(text, glob):
                return True
            if "/" not in glob and fnmatch.fnmatch(name, glob):
                return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Hook plumbing, shared by every hook in scripts/
# ---------------------------------------------------------------------------


def hooks_disabled():
    """Return True when CRAFT_HOOKS=off. Every hook checks this first."""
    try:
        return str(os.environ.get("CRAFT_HOOKS", "")).strip().lower() == "off"
    except Exception:
        return False


def read_payload(stream=None):
    """Return the hook payload from stdin as a dict. {} when it cannot be read.

    Malformed JSON, an empty body and a closed pipe all give {}, and every hook
    treats {} as "allow".
    """
    try:
        source = stream if stream is not None else sys.stdin
        raw = source.read()
    except Exception:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def payload_cwd(payload):
    """Return the working directory the payload reports, or None."""
    try:
        value = payload.get("cwd")
        return value if isinstance(value, str) and value else None
    except Exception:
        return None


def payload_session_id(payload):
    """Return the Claude session id the payload reports, or None."""
    try:
        value = payload.get("session_id")
        return value if isinstance(value, str) and value else None
    except Exception:
        return None


def target_path(payload):
    """Return the file path a Write or Edit call targets, or ''."""
    try:
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            return ""
        for key in ("file_path", "notebook_path", "path"):
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                return value
        return ""
    except Exception:
        return ""


def is_write_tool(payload):
    """Return True when the payload describes a Write-like tool call."""
    try:
        return payload.get("tool_name") in WRITE_TOOLS
    except Exception:
        return False


def emit_allow():
    """Let the call through, silently. Return the exit code to use.

    Nothing is printed on purpose. A PreToolUse hook that answers "allow" in
    JSON bypasses the permission system and auto-approves a write the developer
    would otherwise be asked about. Silence keeps the normal rules in force.
    """
    return 0


def emit_deny_tool(reason):
    """Block a PreToolUse tool call and tell Claude why. Return the exit code.

    The reason goes out three ways on purpose, because each one is enough on its
    own and the three together survive a change in any single channel:
    the documented JSON decision, the stderr text, and exit code 2.
    """
    message = str(reason)
    try:
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": message,
                    }
                }
            )
        )
        sys.stdout.flush()
    except Exception:
        pass
    try:
        sys.stderr.write(message + "\n")
        sys.stderr.flush()
    except Exception:
        pass
    return 2


def emit_block_stop(reason):
    """Stop Claude from finishing, and give it the correction. Return the code."""
    message = str(reason)
    try:
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "Stop",
                        "decision": "block",
                        "reason": message,
                    }
                }
            )
        )
        sys.stdout.flush()
    except Exception:
        pass
    try:
        sys.stderr.write(message + "\n")
        sys.stderr.flush()
    except Exception:
        pass
    return 2


def emit_after_tool(reason):
    """Tell Claude, after a tool call ran, what it must correct. Return the exit code."""
    message = str(reason)
    try:
        sys.stdout.write(json.dumps({"decision": "block", "reason": message}))
        sys.stdout.flush()
    except Exception:
        pass
    try:
        sys.stderr.write(message + "\n")
        sys.stderr.flush()
    except Exception:
        pass
    return 2


def emit_warning(message):
    """Let the call or the stop go on, and show the developer a warning. Return the exit code."""
    try:
        sys.stdout.write(json.dumps({"systemMessage": str(message)}))
        sys.stdout.flush()
    except Exception:
        pass
    return 0


def run_hook(decide):
    """Run one hook end to end. Return the exit code. Never raises.

    decide(payload) returns ("allow", ""), ("deny", reason) before a tool call,
    ("report", reason) after one, ("block", reason) at Stop, or ("warn",
    message) to allow with a warning. Anything else, and any exception at all,
    means allow.
    """
    try:
        payload = read_payload()
        action, reason = decide(payload)
    except Exception:
        return 0
    if action == "deny":
        return emit_deny_tool(reason)
    if action == "report":
        return emit_after_tool(reason)
    if action == "block":
        return emit_block_stop(reason)
    if action == "warn":
        return emit_warning(reason)
    return emit_allow()


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _argument(argv, flag, default=None):
    """Return the value after flag in argv, or default."""
    if flag in argv:
        index = argv.index(flag)
        if index + 1 < len(argv):
            return argv[index + 1]
    return default


def _command_status(argv):
    cwd = _argument(argv, "--cwd")
    session = read_session(cwd)
    report = {
        "host_root": str(host_root(cwd)),
        "craft_dir": str(craft_dir(cwd)),
        "active": is_active(cwd),
        "route": current_route(cwd),
        "session_id": current_session_id(cwd),
        "checkpoint_command": checkpoint_command(cwd),
        "checks": len(checks(cwd)),
        "green_checks": len(green_checks(cwd)),
        "spec": active_spec_name(cwd),
        "spec_state": spec_state(cwd)[0],
        "open_findings": len(open_findings(cwd)),
        "started_at": session.get("started_at", ""),
        "updated_at": session.get("updated_at", ""),
    }
    if "--json" in argv:
        print(json.dumps(report, indent=2))
        return 0
    for key in sorted(report):
        print("%-20s %s" % (key, report[key]))
    return 0


def _command_start(argv):
    route = _argument(argv, "--route", "")
    if not route:
        sys.stderr.write("start needs --route quick|task|project\n")
        return 2
    ok = start_session(
        route,
        session_id=_argument(argv, "--session"),
        checkpoint=_argument(argv, "--checkpoint"),
        cwd=_argument(argv, "--cwd"),
    )
    if not ok:
        sys.stderr.write("could not write session.json\n")
        return 1
    print("craft session started on route %s" % route.strip().lower())
    return 0


def _command_record_check(argv):
    command = _argument(argv, "--command")
    exit_code = _argument(argv, "--exit-code")
    if command is None or exit_code is None:
        sys.stderr.write('record-check needs --command "CMD" and --exit-code N\n')
        return 2
    try:
        code = int(exit_code)
    except ValueError:
        sys.stderr.write("--exit-code must be a whole number\n")
        return 2
    if not record_check(command, code, cwd=_argument(argv, "--cwd")):
        sys.stderr.write("could not write session.json\n")
        return 1
    print("recorded: exit %d for %s" % (code, command))
    return 0


def _command_end(argv):
    archived = end_session(cwd=_argument(argv, "--cwd"))
    if not archived:
        sys.stderr.write("no active session to end\n")
        return 1
    print("session archived at %s" % archived)
    return 0


def main(argv):
    commands = {
        "status": _command_status,
        "start": _command_start,
        "record-check": _command_record_check,
        "end": _command_end,
    }
    if not argv or argv[0] in ("-h", "--help") or argv[0] not in commands:
        print((__doc__ or "").strip())
        print("")
        print("commands: %s" % ", ".join(sorted(commands)))
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    return commands[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
