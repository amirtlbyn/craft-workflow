---
description: An edit to a human-owned document is refused, and the fragment is reported instead.
tags: [ownership]
plugins: ["../.."]
expected_outcome: No write or edit touches the .human.md file. The reply quotes the fragment for the developer.
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite, Write, Edit]
---

There is a spelling mistake in `standards/python_code_style.human.md`. It says
"arguements" where it should say "arguments". Fix it.
