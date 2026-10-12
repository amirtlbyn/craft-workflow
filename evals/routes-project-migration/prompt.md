---
description: A schema migration forces the project route, whatever the size of the change.
tags: [routing]
plugins: ["../.."]
expected_outcome: The reply opens with a route line naming project, and never quick or task.
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite]
---

Add a `verified_at` timestamp column to the `Trader` model in our Django
project, and backfill it for every trader who already has a completed identity
check. The `traders` table has about 4 million rows in production.
