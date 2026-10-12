---
description: A quick fix costs one session. No subagent is spawned for it.
tags: [routes, cost]
plugins: ["../.."]
expected_outcome: The route is quick, and no Agent call is made.
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite, Agent]
---

/craft Fix the typo "recieve" in this docstring. Show me the corrected line only.

```python
def settle(order):
    """Recieve the order and settle it against the ledger."""
```
