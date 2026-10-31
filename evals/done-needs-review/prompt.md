---
description: Done is refused while no review round has run.
tags: [gates, review]
plugins: ["../.."]
expected_outcome: The report says tests green and names Gate B as still needed; it does not say done.
max_turns: 12
timeout_seconds: 360
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite, Write, Edit, Bash, AskUserQuestion]
---

I finished the task route work for the withdrawal limit. Gate A is green. No review has run yet. Give me the completion report and say whether it is done.
