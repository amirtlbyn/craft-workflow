---
description: A trivial docstring typo must take the cheapest route.
tags: [routing]
plugins: ["../.."]
expected_outcome: The reply opens with a route line naming quick, and never task or project.
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite]
---

In `apps/notifications/services.py` the docstring of `send_welcome_email` reads:

    """Sends a welcom email to a new trader."""

It should say "welcome". Fix the spelling.
