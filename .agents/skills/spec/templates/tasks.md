# TASKS: {title}

Spec: spec.md · Key: {key} · Route: {route} · State: pending
Checkpoint: `{checkpoint}`

<!-- tasks.md is the live state. Tick a box when its task is written AND its
     check ran. Every task names the file it changes and the criterion it
     serves. On the project route, add one "## Session N" block per session. -->

## Session 1 — {title}

State: pending · Covers: {key}-1

- [ ] T1 — <file-level action, e.g. add `debit()` to `WalletService` in `apps/wallet/services.py`> — {key}-1
- [ ] T2 — test {key}-1 in `<test file>`

Gate A: `bin/craft-spec trace --session 1` green · checkpoint green through `bin/craft-check` · the stack's lint and format green (`bin/craft-stack checks`)
Gate B: `reviewer` (lenses: spec, style, <routed>) · `deep-reviewer` when Risk: high

Resume: <what the next session expects to find: files, last commit, next task>
