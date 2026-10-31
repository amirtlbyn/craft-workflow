#!/usr/bin/env python3
"""PreToolUse on Bash and the write tools - only the developer approves, and only the developer turns hooks off.

An approval opens the spec gate or the scenarios gate. bin/craft-approve writes
it to .claude/craft/approval.json. The developer gives it, not Claude. The
other files under .claude/craft/ (session.json, findings.json, reviews.json)
and .claude/specs/ACTIVE hold the evidence the gates trust, and only the bin/
commands write them. So this hook denies, in every repository, with or without
a craft session:

  1. A Bash command that runs craft-approve. The rule is strict: when the text
     holds "craft-approve" and any command in it is not read-only, it is
     denied. `rg craft-approve skills/` is allowed.
  2. A hook off-switch: a Bash assignment of CRAFT_HOOKS; `CRAFT_HOOKS`,
     `disableAllHooks`, or craft-workflow set to false in `enabledPlugins`,
     written to a .claude/settings.json or .claude/settings.local.json (JSON
     escapes decoded); a settings file written by cp, mv, tee, or the like,
     whose content the command does not show; `claude plugin
     disable|uninstall|remove` and `claude plugin marketplace remove`; a write
     under the plugin root when the root is outside the repository.
  3. A write to .claude/craft/ or under it, or to .claude/specs/ACTIVE, by a
     write tool or by a Bash write form, symlinks resolved.
     The rule is strict, as for craft-approve, and it applies when a craft
     session is active or the text names .claude: when one pipeline names a
     craft path (.claude/craft, craft/session.json and the other state files,
     specs/ACTIVE), directly or through a variable set to one, and runs a
     command that is neither read-only, nor an honest bin/ program run
     (craft-check, craft-spec status|trace|lenses, craft-session status|
     record-finding|record-review|finding --state fixed, craft-scenarios,
     craft-stack, craft-std, craft-ui-state), nor `git add`, nor the `cp` of a
     backup that a restore command gives, it is denied.
     `jq . .claude/craft/session.json` and a commit message that names it are
     allowed. A file named session.json elsewhere is not a state file.
  4. A bin/ subcommand that changes trusted state on Claude's behalf:
     `craft-session start` that changes a task or project route; `craft-session
     end` or `craft-spec new` while a file a Bash call changed with the gate
     shut is not restored; `record-check` by hand, through craft-session or
     craft_state.py; `craft-session finding ID --state <any but fixed>`.
     craft-check records checks itself, as a program, and stays allowed.

A Bash command whose text cannot be split into words is denied when it holds
one of the words above. That is a decision on unreadable text, not an error
path: an exception inside this hook still allows the call.

The denial for craft-approve gives the exact line the developer types in the
prompt. A `!` command from the developer does not reach this hook.

A Bash command that holds none of craft, CRAFT_HOOKS, disableAllHooks,
approval.json, plugin, settings, or ACTIVE costs one regular expression search
and nothing more.

Kill switch: CRAFT_HOOKS=off, in the developer's own environment
"""

import json
import pathlib
import re
import sys

# Claude Code runs this file by path, so its own directory is already on
# sys.path. The line below keeps the import working when a test imports the
# module from somewhere else.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

BIN = craft_state.PLUGIN_ROOT / "bin"
WORTH_A_LOOK = re.compile(
    r"craft|agent_gate|record_spawn|CRAFT_HOOKS|disableAllHooks|approval\.json|[Pp]lugin|settings|ACTIVE"
)
OFF_SWITCH = re.compile(r"CRAFT_HOOKS|disableAllHooks|craft-workflow[^\"'\n]*[\"']\s*:\s*false")
UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")
COPY_LIKE = ("cp", "mv", "install", "ln", "dd", "tee", "rsync")

APPROVE_DENIAL = """Only the developer approves a spec or its scenarios, and only the developer
turns the craft hooks off. Claude does not run craft-approve, and does not set
CRAFT_HOOKS.

Stop here. Ask the developer to type one of these lines in the prompt, or to
press `a` on the board:

  ! "%(bin)s/craft-approve"
  ! "%(bin)s/craft-approve" --scenarios

The first approves spec.md. The second approves scenarios.md. The `!` runs the
line in the developer's shell, as the developer.

A command whose text names craft-approve is allowed only when every command in
it only reads (rg, grep, cat, sed -n, git log, ...). To write a file that
names it, use the Write tool."""

STATE_DENIAL = """This write targets the craft workflow's own state:

  %(path)s

Only the bin/ commands write .claude/craft/, run as programs: craft-approve by
the developer, craft-check, craft-session, craft-spec. A record that Claude
writes is a forged record.

To read state, use cat, jq, or bin/craft-spec status. To approve, ask the
developer to type one of these lines in the prompt, or to press `a` on the
board:

  ! "%(bin)s/craft-approve"
  ! "%(bin)s/craft-approve" --scenarios"""

OFF_DENIAL = """This call would turn the craft hooks off:

  %(what)s

Only the developer turns the hooks off. Stop, and tell the developer which
hook is in the way and why. The developer decides."""

ROUTE_DENIAL = """This command changes the route of the active craft session from %(current)s to
%(route)s. The route decides which gates hold, so only the developer changes it.

Ask the developer to type this line in the prompt:

  ! "%(bin)s/craft-session" start --route %(route)s"""

BLOCKED_DENIAL = """This command would end the craft session or start a new spec, and a Bash call
changed these files while the spec gate was shut:

%(paths)s

Restore them first, with the commands the hook gave, or ask the developer. The
developer can run the same command in the prompt with `!`."""

RECORD_CHECK_DENIAL = """A check is recorded by running it. Claude does not record an exit code by hand.

Run the command through craft-check. It records the exit code the command
really returned:

  "%(bin)s/craft-check" -- <the command>

When the check ran where craft-check cannot reach, ask the developer to record
it with `! "%(bin)s/craft-session" record-check --command "..." --exit-code N`."""

FINDING_DENIAL = """Only the developer decides a review finding's state. Claude marks a finding
`fixed` after the fix is verified, and no other state.

Ask the developer to decide on the board's Review tab, or to type:

  ! "%(bin)s/craft-session" finding %(finding)s --state %(state)s"""

SPAWN_DENIAL = """Reviewer spawns are recorded only by the Agent tool: the hook scripts/agent_gate.py
writes them when Claude spawns a reviewer. A command that feeds that hook a
payload, or calls record_spawn, would forge the record Gate B relies on.

Spawn the reviewer with the Agent tool."""

UNREADABLE = """This command names the craft workflow's approval or its hooks, and its text
cannot be read (an open quote, for example). It is denied, because a command
that cannot be read cannot be checked.

Write the command again with balanced quotes. To write a file, use the Write
tool."""


def turns_hooks_off(text):
    """Return True when settings text sets CRAFT_HOOKS, disableAllHooks, or disables craft-workflow.

    Text that parses as JSON is read as JSON. Other text is matched after its
    \\uXXXX escapes are decoded.
    """
    decoded = UNICODE_ESCAPE.sub(lambda match: chr(int(match.group(1), 16)), str(text))
    try:
        data = json.loads(text)
    except ValueError:
        return bool(OFF_SWITCH.search(decoded))
    pending = [data]
    while pending:
        item = pending.pop()
        if isinstance(item, list):
            pending += item
        if not isinstance(item, dict):
            continue
        if item.get("disableAllHooks") or "CRAFT_HOOKS" in item:
            return True
        if any("craft-workflow" in str(key) and value is False for key, value in item.items()):
            return True
        pending += list(item.values())
    return False


def option(arguments, flag):
    """Return the value of --flag VALUE or --flag=VALUE in arguments, in lower case, or ''."""
    for index, argument in enumerate(arguments):
        if argument == flag and index + 1 < len(arguments):
            return arguments[index + 1].strip().lower()
        if argument.startswith(flag + "="):
            return argument.split("=", 1)[1].strip().lower()
    return ""


def blocked_paths(cwd):
    """Return the files a CRF-4 record blocks a stop for, one per line, or ''."""
    return "\n".join("  " + path for path in sorted(craft_state.blocking_writes(cwd)))


def program_denial(program, arguments, cwd):
    """Return the deny reason for a craft-session, craft-spec, or craft_state.py run, or ''."""
    subcommand = arguments[0] if arguments else ""
    values = {"bin": BIN}
    if program in ("craft-session", "craft_state.py"):
        if subcommand == "record-check":
            return RECORD_CHECK_DENIAL % values
        if subcommand == "start" and craft_state.is_active(cwd):
            route = option(arguments, "--route")
            current = craft_state.current_route(cwd)
            if current in ("task", "project") and route != current:
                return ROUTE_DENIAL % dict(values, current=current, route=route or "none")
        if subcommand == "end" and blocked_paths(cwd):
            return BLOCKED_DENIAL % {"paths": blocked_paths(cwd)}
        state = option(arguments, "--state")
        if program == "craft-session" and subcommand == "finding" and state and state != "fixed":
            finding = arguments[1] if len(arguments) > 1 else "F1"
            return FINDING_DENIAL % dict(values, finding=finding, state=state)
    if program == "craft-spec" and subcommand == "new" and blocked_paths(cwd):
        return BLOCKED_DENIAL % {"paths": blocked_paths(cwd)}
    return ""


def deny_write(path, cwd, new_text):
    """Return the deny reason for a write of new_text to path, or ''."""
    if craft_state.is_craft_state(path, cwd):
        return STATE_DENIAL % {"path": path, "bin": BIN}
    if craft_state.is_settings_file(path, cwd) and turns_hooks_off(new_text):
        return OFF_DENIAL % {"what": "CRAFT_HOOKS, disableAllHooks, or craft-workflow disabled in %s" % path}
    if craft_state.is_plugin_write(path, cwd):
        return OFF_DENIAL % {"what": "a write under the plugin root, %s" % craft_state.PLUGIN_ROOT}
    return ""


def tool_text(tool_input):
    """Return the new text a Write, Edit, MultiEdit, or NotebookEdit call puts in its file."""
    parts = [tool_input.get(key) for key in ("content", "new_string", "new_source")]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        parts += [edit.get("new_string") for edit in edits if isinstance(edit, dict)]
    return "\n".join(part for part in parts if isinstance(part, str))


def decide(payload):
    """Return ("allow", "") or ("deny", reason). Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("allow", "")
        cwd = craft_state.payload_cwd(payload)
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            return ("allow", "")

        if craft_state.is_write_tool(payload):
            path = craft_state.target_path(payload)
            reason = deny_write(path, cwd, tool_text(tool_input)) if path else ""
            return ("deny", reason) if reason else ("allow", "")

        if payload.get("tool_name") != "Bash":
            return ("allow", "")
        command = tool_input.get("command")
        if not isinstance(command, str) or not WORTH_A_LOOK.search(command):
            return ("allow", "")

        effects = craft_state.bash_effects(command, cwd)
        if effects["unparsed"]:
            return ("deny", UNREADABLE)
        if effects["approve"] or effects["hooks"]:
            return ("deny", APPROVE_DENIAL % {"bin": BIN})
        if effects["state_write"] and re.search(r"\bagent_gate\b|\brecord_spawn\b", command):
            return ("deny", SPAWN_DENIAL)
        if effects["state_write"] and (craft_state.is_active(cwd) or ".claude" in command):
            return ("deny", STATE_DENIAL % {"path": "a .claude/craft state file, or specs/ACTIVE, named in this command", "bin": BIN})
        if effects["plugin_off"]:
            return ("deny", OFF_DENIAL % {"what": "claude plugin disable, uninstall, or remove"})
        if effects["unknown"] and OFF_SWITCH.search(command):
            return ("deny", OFF_DENIAL % {"what": "a write to a path the command does not show, with CRAFT_HOOKS or disableAllHooks"})
        for writer in effects["writers"]:
            for target in writer["targets"] + writer["redirects"]:
                if craft_state.is_settings_file(target, cwd) and writer["name"] in COPY_LIKE:
                    return ("deny", OFF_DENIAL % {"what": "a settings file written from content this command does not show, %s. Use the Write or Edit tool" % target})
                reason = deny_write(target, cwd, command)
                if reason:
                    return ("deny", reason)
        for run in effects["programs"]:
            reason = program_denial(run["program"], run["arguments"], cwd)
            if reason:
                return ("deny", reason)
        return ("allow", "")
    except Exception:
        return ("allow", "")


if __name__ == "__main__":
    sys.exit(craft_state.run_hook(decide))
