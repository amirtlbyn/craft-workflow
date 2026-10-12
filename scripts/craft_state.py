#!/usr/bin/env python3
"""craft_state - the one place the craft hooks read and write workflow state.

State lives in the host repository, never in this plugin:

    <repo>/.claude/craft/
    |-- session.json    the active craft session: route, spec, id, and checks run
    |-- approval.json   the spec approvals the developer gave, bound by SHA-256
    |-- findings.json   adjudicated review findings
    `-- logs/           full output of every bin/craft-check run

    <repo>/.claude/specs/
    |-- ACTIVE          one line: the active spec directory name
    `-- <dir>/spec.md   the spec the approval digest covers

Two rules govern every line below.

1. **Nothing here raises.** A hook that cannot read its state must let the tool
   call through, so "I do not know" and "allow" have to be the same answer. Every
   public function returns a safe default instead of failing.
2. **Nothing here reaches outside .claude/craft/.** No network, no git, no write
   anywhere else.

Only the standard library is used, and only these modules: json, os, sys, re,
pathlib, fnmatch, datetime, hashlib.

This module is also a small command line, so a developer or the model can create
a session and record a check without a hook:

    python3 scripts/craft_state.py status
    python3 scripts/craft_state.py start --route task
    python3 scripts/craft_state.py record-check --command "pytest -q" --exit-code 0

bin/craft-session and bin/craft-approve are the friendlier front doors.
"""

import datetime
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import sys

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

    Every hook except protect_human_owned is inert when this is False.
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


def start_session(route, session_id=None, checkpoint=None, cwd=None, spec=None):
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


def record_check(command, exit_code, cwd=None, session_id=None, label=None, log=None, summary=None):
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


TASK_LINE = re.compile(r"^\s*[-*]\s*\[([ xX])\]\s*(.+?)\s*$")
STATE_FIELD = re.compile(r"\bState:\s*([a-z][a-z ]*[a-z])", re.IGNORECASE)
RISK_FIELD = re.compile(r"\bRisk:\s*(low|high)\b", re.IGNORECASE)
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


def is_inside_craft_area(path, cwd=None):
    """Return True when path is under <host>/.claude/, or outside the host repository.

    The spec gate shuts the host repository's source and tests. Spec files,
    craft state, and files outside the repository are not its business.
    """
    try:
        root = host_root(cwd)
        target = pathlib.Path(path)
        if not target.is_absolute():
            target = pathlib.Path(cwd or os.getcwd()) / target
        target = pathlib.Path(os.path.normpath(str(target)))
        try:
            relative = target.relative_to(root)
        except ValueError:
            return True
        parts = relative.parts
        return bool(parts) and parts[0] == ".claude"
    except Exception:
        return True


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


def run_hook(decide):
    """Run one hook end to end. Return the exit code. Never raises.

    decide(payload) returns ("allow", "") or ("deny", reason). Anything else,
    and any exception at all, means allow.
    """
    try:
        payload = read_payload()
        action, reason = decide(payload)
    except Exception:
        return 0
    if action == "deny":
        return emit_deny_tool(reason)
    if action == "block":
        return emit_block_stop(reason)
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
