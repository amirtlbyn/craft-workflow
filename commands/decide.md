---
description: Choose which AI deciders answer the workflow's routing questions — Jev, free tiers, local models, or Claude Haiku — and test them
argument-hint: status | on | off | use <p,p> | council <p,p,p> | mode first|council | set <p> model <id> | test [p|all] | discover <p> [--free]
---

Load the `jev` skill (it covers every decider, not only Jev), then run from the
host repository root:

- no argument → `<plugin root>/bin/craft-decide status`
- anything else → `<plugin root>/bin/craft-decide $ARGUMENTS`

The plugin root is `${CLAUDE_PLUGIN_ROOT}` when the host sets it.

Report the output as it is: the status table shows each provider, whether it is
free, whether it may keep prompts, and whether a key or a local server was
found. When a provider is not ready, say which environment variable or key file
it needs (`~/.config/craft-workflow/<provider>.key`). Never print, echo, or
store a key.

`test` and `discover` make network calls: run them only when the developer
asked. `test all` asks every provider once. `claude` runs `claude -p` on the
developer's own plan, so it spends their usage: say so before you run it.

`approve-with` decides which deciders may approve tool calls. It is the
developer's decision, never yours, and `bin/craft-jev approve on` must also be
on. Run it only when the developer typed it in this conversation.
