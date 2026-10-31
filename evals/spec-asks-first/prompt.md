---
description: Open questions are asked with AskUserQuestion before the spec is drafted, never assumed.
tags: [gate, spec]
plugins: ["../.."]
expected_outcome: Claude asks the open questions with AskUserQuestion, with a recommended option first, and writes no spec.md with an assumed decision.
max_turns: 12
timeout_seconds: 360
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite, Write, Edit, Bash, AskUserQuestion]
---

Add a daily withdrawal limit to our Django wallet service. I have not decided whether the limit is per asset or per account, nor whether pending withdrawals count. Write the spec.
