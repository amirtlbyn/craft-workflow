#!/usr/bin/env python3
"""PreToolUse - let Jev approve routine tool calls, so fewer prompts interrupt the work.

Off by default. It acts only when both switches are on:

    bin/craft-jev on
    bin/craft-jev approve on

It can only turn a permission prompt into an approval. It never widens what the
rest of the workflow refuses. The order of the checks is the safety design:

  1. Kill switch, switches, and permission mode. In bypassPermissions or plan
     mode it does nothing.
  2. The other craft hooks. When protect_human_owned or gate_spec would deny the
     call, this hook stays silent and lets them deny it.
  3. deny_patterns in config/jev.json. A match denies the call, with no model
     involved: rm -rf /, mkfs, curl | sh, and the like.
  4. ask_patterns and ask_path_patterns. A match stays silent, so Claude Code
     asks the developer as usual: git push, installs, network tools,
     credentials, databases, arbitrary code in `python -c`, and every command
     that changes this workflow's own gates, such as craft-approve.
  5. Jev. Only a verdict of "allow" with confidence at or above the threshold,
     and both risk questions below the risk threshold, approves the call.
     Anything else, including a timeout or an error, stays silent.

Silence means "no opinion": Claude Code applies its normal permission rules.
The hook never answers "ask" and never answers "deny" on Jev's word alone.

What is sent: the tool name, the Bash command or the file path with secrets
redacted, whether the path is inside the repository, the route, and whether
the spec is approved. Never file contents.

Every decision goes to .claude/craft/jev-approvals.jsonl.

Kill switch: CRAFT_HOOKS=off. CRAFT_JEV_APPROVE=off turns off only this hook.
"""

import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

LOG_FILE = "jev-approvals.jsonl"
SKIP_MODES = ("bypassPermissions", "plan")
DEFAULT_TOOLS = ("Bash", "Write", "Edit", "MultiEdit", "NotebookEdit")

REDACTIONS = (
    (re.compile(r"(?i)(authorization:\s*(bearer|basic|token)\s+)[^\s'\"]+"), r"\1<redacted>"),
    (re.compile(r"(?i)\bbearer\s+[a-z0-9._\-]{8,}"), "Bearer <redacted>"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"), "sk-<redacted>"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{16,}|glpat-[A-Za-z0-9_\-]{16,}|xox[baprs]-[A-Za-z0-9\-]{10,})"),
     "<redacted-token>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<redacted-aws-key>"),
    (re.compile(r"(?i)\b([a-z_]*(password|passwd|secret|token|api_?key)[a-z_]*\s*[=:]\s*)[^\s'\"&]+"),
     r"\1<redacted>"),
    (re.compile(r"(?i)(://[^/\s:@]+:)[^@\s/]+@"), r"\1<redacted>@"),
)


def redact(text):
    """Return text with the common secret shapes replaced."""
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def matches_any(patterns, text):
    """Return the first pattern that matches text, or ''."""
    for pattern in patterns or []:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return pattern
        except re.error:
            continue
    return ""


def describe(payload, cwd, approve):
    """Return (kind, subject, inside_repository) for the call."""
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        return "command", command[: int(approve.get("max_command_chars", 1500))], True
    path = craft_state.target_path(payload)
    root = craft_state.host_root(cwd)
    target = pathlib.Path(path)
    if not target.is_absolute():
        target = pathlib.Path(cwd or os.getcwd()) / target
    target = pathlib.Path(os.path.normpath(str(target)))
    try:
        return "path", target.relative_to(root).as_posix(), True
    except ValueError:
        return "path", str(target), False


def other_hooks_deny(payload):
    """Return True when protect_human_owned or gate_spec would deny this call."""
    try:
        import gate_spec
        import protect_human_owned

        for hook in (protect_human_owned, gate_spec):
            if hook.decide(payload)[0] == "deny":
                return True
    except Exception:
        return True
    return False


def log(cwd, record):
    try:
        path = craft_state.state_path(LOG_FILE, cwd)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    except OSError:
        pass


def decide(payload):
    """Return ("allow", reason), ("deny", reason), or ("silent", why). Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("silent", "kill switch")
        import jev_client

        cwd = craft_state.payload_cwd(payload)
        if not jev_client.is_approve_enabled(cwd):
            return ("silent", "approval off")
        if payload.get("permission_mode") in SKIP_MODES:
            return ("silent", "permission mode %s" % payload.get("permission_mode"))

        config = jev_client.effective_config(cwd)
        approve = config.get("approve") if isinstance(config.get("approve"), dict) else {}
        tool = payload.get("tool_name")
        if tool not in (approve.get("tools") or DEFAULT_TOOLS):
            return ("silent", "tool not covered")
        if other_hooks_deny(payload):
            return ("silent", "another craft hook denies it")

        kind, subject, inside = describe(payload, cwd, approve)
        if kind == "command":
            rule = matches_any(approve.get("deny_patterns"), subject)
            if rule:
                return ("deny", "craft-workflow refuses this command. It matches a deny rule in "
                                "config/jev.json: %s. Ask the developer to run it by hand if it is "
                                "really wanted." % rule)
            rule = matches_any(approve.get("ask_patterns"), subject)
            if rule:
                return ("silent", "always ask: %s" % rule)
        else:
            if not inside:
                return ("silent", "always ask: path outside the repository")
            rule = matches_any(approve.get("ask_path_patterns"), subject)
            if rule:
                return ("silent", "always ask: %s" % rule)

        import deciders

        decider_config = deciders.load(cwd)
        if not deciders.available(decider_config, purpose="approve"):
            return ("silent", "no API key")
        questions = approve.get("questions") or {}
        if not questions.get("verdict"):
            return ("silent", "no verdict question in config/jev.json")

        state_spec, _detail = craft_state.spec_state(cwd)
        state = {
            "tool": tool,
            kind: redact(subject),
            "inside_repository": inside,
            "route": craft_state.current_route(cwd) or "none",
            "spec": state_spec,
        }
        call_config = dict(config, timeout_seconds=approve.get("timeout_seconds", 3),
                           retries=approve.get("retries", 0))
        try:
            answers, meta = deciders.ask(
                questions, state, cwd=cwd, purpose="approve", jev_config=call_config,
                timeout=approve.get("timeout_seconds", 3), config=decider_config,
            )
        except jev_client.JevError as error:
            return ("silent", "Jev failed: %s" % error)

        verdict, confidence = jev_client.choice_of(answers.get("verdict"))
        irreversible = jev_client.noul_probability(answers.get("irreversible"))
        sends_out = jev_client.noul_probability(answers.get("sends_data_out"))
        threshold = float(approve.get("confidence_threshold", 0.9))
        risk_threshold = float(approve.get("risk_threshold", 0.3))
        summary = "verdict %s %.2f · irreversible %s · sends data out %s · %s ms" % (
            verdict, confidence,
            "?" if irreversible is None else "%.2f" % irreversible,
            "?" if sends_out is None else "%.2f" % sends_out,
            meta.get("latency_ms"),
        )
        if (
            verdict == "allow"
            and confidence >= threshold
            and irreversible is not None and irreversible < risk_threshold
            and sends_out is not None and sends_out < risk_threshold
        ):
            return ("allow", "Approved by %s (%s)." % (meta.get("label") or "Jev", summary))
        return ("silent", "Jev did not approve: %s" % summary)
    except Exception as error:
        return ("silent", "error: %s" % type(error).__name__)


def emit_allow(reason):
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.stdout.flush()
    return 0


def main():
    payload = craft_state.read_payload()
    action, reason = decide(payload)
    if action != "silent" or reason not in ("approval off", "kill switch", "tool not covered"):
        try:
            tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
            subject = str(tool_input.get("command") or craft_state.target_path(payload) or "")
            log(
                craft_state.payload_cwd(payload),
                {
                    "at": craft_state.now(),
                    "tool": payload.get("tool_name"),
                    "subject": redact(subject)[:160],
                    "decision": "prompt" if action == "silent" else action,
                    "reason": reason,
                },
            )
        except Exception:
            pass
    if action == "allow":
        return emit_allow(reason)
    if action == "deny":
        return craft_state.emit_deny_tool(reason)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
