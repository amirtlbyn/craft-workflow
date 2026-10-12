---
description: A request this workflow does not own must not load any skill.
tags: [negative]
plugins: ["../.."]
expected_outcome: The question is answered directly. No skill is invoked.
max_turns: 6
timeout_seconds: 180
allowed_tools: [Skill]
---

In two sentences, what is the practical difference between TCP and UDP?
