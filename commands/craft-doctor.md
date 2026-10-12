---
description: Check that the standards, skills, agents, commands and hooks of this workflow are healthy
argument-hint: [empty, or --json]
---

Run the health check for this workflow and report what it found.

Run exactly this, from the repository root:

```bash
"${CLAUDE_PLUGIN_ROOT}"/bin/craft-doctor $ARGUMENTS
```

The script reads. It writes no file and it changes no Git state.

Report its output as it is. Then add these three lines:

1. The summary counts, and the exit code.
2. Every `FAIL`, with the one action that clears it.
3. `Healthy` when the exit code is 0, or `Misconfigured` when it is 1.

**Do not repair a `FAIL` yourself.** A `FAIL` usually means the environment is
wrong, not the plugin. Two rules hold:

- A `standards/*.md` hash mismatch means the vendored document changed without a
  recorded sync. Report the file. Never edit a `*.human.md` file to clear it.
- An unresolvable command in section 6 means the tool is not installed here. Say
  which command, and that the workflow must report `blocked` rather than `done`
  until it runs.

What each status means:

| Status | Meaning |
|---|---|
| `PASS` | The check ran and the thing is correct |
| `FAIL` | The check ran and the thing is wrong. The exit code becomes 1 |
| `SKIP` | The check could not run, and that is acceptable |
| `INFO` | Informational. It never changes the exit code |
