---
description: The coder model is picked by difficulty and written as a Model line.
tags: [routing, models]
plugins: ["../.."]
expected_outcome: The plan gives the mechanical session haiku and the security session opus, each as a Model line with a reason.
max_turns: 12
timeout_seconds: 360
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite, Write, Edit, Bash, AskUserQuestion]
---

Plan these two sessions of a Risk: low project and state the model you would give coder for each, in the form 'Model: <id> — <reason>'. Session 1: rename a constant in 14 files. Session 2: rewrite the withdrawal authorization check in the ledger so a trader cannot overdraw under concurrent requests.
