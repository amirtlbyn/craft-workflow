---
description: Turn the optional Jev decision layer on or off, check it, or ask it for a routing decision
argument-hint: on | off | status | test | decide <request> | set endpoint <url> | set model <id> | unset endpoint | approve on|off
---

Load the `jev` skill, then run the matching command from the host repository
root:

- `on`, `off`, `status`, `test` → `<plugin root>/bin/craft-jev $ARGUMENTS`
- `set endpoint <url>`, `set model <id>`, `unset endpoint`, `unset model` →
  `<plugin root>/bin/craft-jev $ARGUMENTS`
- `approve on`, `approve off`, `approve status` → `<plugin root>/bin/craft-jev $ARGUMENTS`
- `decide <request>` → `<plugin root>/bin/craft-jev decide --stage route --request "<request>"`
- no argument → `<plugin root>/bin/craft-jev status`

The plugin root is `${CLAUDE_PLUGIN_ROOT}` when the host sets it.

**`approve on` is the developer's decision, never yours.** Run it only when the
developer typed `/jev approve on` in this conversation. Never suggest turning it
on to get past a prompt. After `approve on`, repeat the command's warning lines.

Report the output as it is. After `on`, say whether a key was found, and suggest
`/jev test`. `test` makes one paid call of a fraction of a cent, so run it only
when the developer asked for it. Never print, echo, or store the API key.
