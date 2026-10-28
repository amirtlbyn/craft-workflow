#!/usr/bin/env python3
"""PreToolUse on Write|Edit - the component gate for frontend files.

On a frontend stack, a component that skips its contract is the exact defect
the component lens keeps finding after the fact. This hook moves three cheap,
structural checks to before the write lands. It is deliberately not the full
CGT checklist: props typing, Storybook, and documentation need a parser; the
reviewer's component lens owns those. What a regex can judge fairly, this
gate judges early.

The hook is inert unless all of these hold:

  1. A craft session is recorded at <repo>/.claude/craft/session.json
  2. The target path is inside the host repository
  3. `bin/craft-stack for <path>` names a frontend stack (react, vue, nuxt)
     and the path is a component source file

Then it denies the write when the new content violates one of:

  * a full Write to a component file with no component definition (empty or
    placeholder content; Edit fragments are checked as fragments)
  * an event listener or subscription added with no teardown in the same file
    (React: removeEventListener without addEventListener symmetry is allowed;
    the rule fires when addEventListener/setInterval/subscribe appears and no
    cleanup token does)
  * inline styles carrying a raw hex color when the file otherwise uses none
    (new hardcoded palette sneaks past design tokens)

Fails open. Any exception, any payload it does not recognise, any missing
configuration: the write goes through. The reviewer's component and
accessibility lenses stay the real judges.

Kill switch: CRAFT_HOOKS=off
"""

import pathlib
import re
import sys

# Claude Code runs this file by path, so its own directory is already on
# sys.path. The line below keeps the import working when a test imports the
# module from somewhere else.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

FRONTEND_STACKS = ("react", "vue", "nuxt")
COMPONENT_SUFFIXES = (".vue", ".jsx", ".tsx")
SOURCE_SUFFIXES = (".js", ".ts", ".mjs", ".jsx", ".tsx", ".vue", ".svelte")

LISTENER_ADD = re.compile(
    r"\b(addEventListener\s*\(|setInterval\s*\(|setTimeout\s*\(|\.subscribe\s*\()")
TEARDOWN = re.compile(
    r"\b(removeEventListener\s*\(|clearInterval\s*\(|clearTimeout\s*\(|"
    r"unsubscribe\s*\(|takeUntil\(|takeUntilDestroyed\s*\(|onUnmounted|onBeforeUnmount|ngOnDestroy|onScopeDispose|AbortController)")
COMPONENT_DEF = re.compile(
    r"(\bexport\s+default\b|\bdefineComponent\b|<template|@Component\s*\(|"
    r"\bfunction\s+[A-Z]\w*\s*\(|\bconst\s+[A-Z]\w*\s*[=:]\s*\(?\s*\{|class\s+[A-Z]\w*)")
RAW_HEX = re.compile(r"""(?:style\s*=\s*["'][^"']*|background(?:-color)?\s*:\s*|color\s*:\s*)#[0-9a-fA-F]{3,8}\b""")

HEADER = """The component gate is shut. This write breaks a structural component rule
that the component lens would flag after the fact.

  blocked path   %(path)s
  stack          %(stack)s
  rule           %(rule)s
"""

FOOTER = """
Fix the content and rewrite, or split the change so the violating hunk is
reviewed deliberately. The reviewer's component lens stays the final judge;
this gate only refuses the mechanical violations.

Writes under .claude/ are always allowed. To turn every craft hook off for one
command, set CRAFT_HOOKS=off."""

RULES = {
    "no-component": "a component file must define a component (template, defineComponent, @Component, or an exported component function)",
    "listener-teardown": "an addEventListener/setInterval/subscribe needs a teardown in the same file (removeEventListener, clearTimeout, unsubscribe, takeUntil*, onUnmounted, ngOnDestroy, onScopeDispose)",
    "raw-hex-style": "a raw hex color appeared in inline styles; use the design token or register a new one (styling-discipline)",
}


def is_frontend_source(path, cwd):
    """Return the stack id when craft-stack assigns this path a frontend stack."""
    try:
        import craft_stack

        found = craft_stack.detect(cwd)
        owner = craft_stack.owner_of(path, cwd, found)
        if owner and owner["id"] in FRONTEND_STACKS:
            return owner["id"]
    except Exception:
        return None
    return None


def violations(text, suffix, *, check_component=True, existing_text=""):
    """Return the list of rule names the candidate content violates."""
    broken = []
    if not suffix.endswith(COMPONENT_SUFFIXES):
        return broken
    stripped = (text or "").strip()
    if check_component and stripped and not COMPONENT_DEF.search(stripped):
        broken.append("no-component")
    if LISTENER_ADD.search(stripped) and not TEARDOWN.search(stripped):
        broken.append("listener-teardown")
    if RAW_HEX.search(stripped) and not RAW_HEX.search(existing_text or ""):
        broken.append("raw-hex-style")
    return broken


def decide(payload):
    """Return ("allow", "") or ("deny", reason). Never raises."""
    try:
        if craft_state.hooks_disabled():
            return ("allow", "")
        if not craft_state.is_write_tool(payload):
            return ("allow", "")

        cwd = craft_state.payload_cwd(payload)
        path = craft_state.target_path(payload)
        if not path or not cwd or not craft_state.is_active(cwd):
            return ("allow", "")
        target = pathlib.Path(path)
        if not target.is_absolute():
            target = pathlib.Path(cwd) / target
        if target.suffix not in SOURCE_SUFFIXES:
            return ("allow", "")
        if craft_state.is_inside_craft_area(str(target), cwd):
            return ("allow", "")

        stack = is_frontend_source(str(target), cwd)
        if not stack:
            return ("allow", "")

        content = ""
        try:
            writes = payload.get("tool_input") or {}
            content = str(writes.get("content") or writes.get("new_string") or "")
        except Exception:
            content = ""

        existing = ""
        try:
            existing = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        broken = violations(
            content,
            target.suffix,
            check_component=payload.get("tool_name") == "Write",
            existing_text=existing,
        )
        if not broken:
            return ("allow", "")
        rule = RULES[broken[0]]
        values = {"path": str(target), "stack": stack, "rule": rule}
        return ("deny", HEADER % values + FOOTER)
    except Exception:
        return ("allow", "")


if __name__ == "__main__":
    sys.exit(craft_state.run_hook(decide))
