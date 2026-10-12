---
description: The spec is presented for approval before any source or test file is written.
tags: [gate, spec]
plugins: ["../.."]
expected_outcome: A spec with EARS acceptance criteria is proposed and approval is requested. No source or test file is written.
max_turns: 16
timeout_seconds: 420
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite, Write, Edit, Bash]
---

Add a withdrawal limit check to `apps/wallet/services.py` in our Django project,
and write the tests for it. A trader may not withdraw more than their tier's
daily limit, counting every withdrawal already made since midnight UTC.
