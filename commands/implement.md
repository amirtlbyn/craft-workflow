---
description: Implement the next open session or task of the active spec
argument-hint: [session number or task, or empty for the next open one]
---

Implement: $ARGUMENTS

Run `bin/craft-spec status`. The spec must be `approved`. With no argument, take
the first session in `tasks.md` whose state is `pending` or `in progress`.

- **task route:** implement in this session, from `tasks.md`.
- **project route:** delegate to `coder`. Give it the plugin root as an
  absolute path, the spec directory, and the session number. When Jev is on,
  run `bin/craft-jev decide --stage route --request "<the session's goal>"` and
  spawn `coder` with the implementer model it names, when the host lets you
  choose a subagent's model. Do not paste the
  spec. `coder` reads it.

After the code exists, inspect the diff yourself. Run Gate A through
`bin/craft-check` and `bin/craft-spec trace` (`--session N` on the project
route). Then route the review with
`config/workflow.md` §3 — a subagent cannot spawn reviewers.

**Do not report the work as done until both gates pass.** When only Gate A
passes, say `tests green` and name what Gate B still needs. Tick `tasks.md` and
append both gates to `log.md`.
