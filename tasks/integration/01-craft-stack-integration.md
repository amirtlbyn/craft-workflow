# TASKS: craft-stack Integration with Frontend

Spec: frontend-technical-spec.md · Key: CSI-1 · Route: project · State: pending
Checkpoint: `bin/craft-check -- python3 scripts/craft_stack_integration_test.py`

## Session 1 — craft-stack Extension

State: pending · Covers: CSI-1

- [ ] T1 — Modify `bin/craft-stack` to detect frontend stacks — CSI-1
- [ ] T2 — Implement frontend stack priority system — CSI-1
- [ ] T3 — Create frontend stack detection in existing detection logic — CSI-1
- [ ] T4 — Update stack reporting to include frontend stacks — CSI-1
- [ ] T5 — Implement mixed stack detection (fullstack projects) — CSI-1
- [ ] T6 — Write integration tests for frontend stack detection — CSI-1
- [ ] T7 — Test with sample fullstack project — CSI-1

## Session 2 — craft-stack skills Integration

State: pending · Covers: CSI-2

- [ ] T8 — Extend `bin/craft-stack skills` for frontend — CSI-2
- [ ] T9 — Implement frontend skill routing based on stack — CSI-2
- [ ] T10 — Create frontend skill loading logic — CSI-2
- [ ] T11 — Update skill selection algorithm — CSI-2
- [ ] T12 — Write tests for frontend skill routing — CSI-2
- [ ] T13 — Test with React project skill selection — CSI-2
- [ ] T14 — Test with Vue project skill selection — CSI-2

## Session 3 — craft-stack checks Integration

State: pending · Covers: CSI-3

- [ ] T15 — Extend `bin/craft-stack checks` for frontend — CSI-3
- [ ] T16 — Implement frontend check commands — CSI-3
- [ ] T17 — Create bundle size check integration — CSI-3
- [ ] T18 — Implement accessibility check integration — CSI-3
- [ ] T19 — Update check command resolution — CSI-3
- [ ] T20 — Write tests for frontend check commands — CSI-3
- [ ] T21 — Test check execution with frontend project — CSI-3

## Session 4 — craft-stack lens Integration

State: pending · Covers: CSI-4

- [ ] T22 — Extend `bin/craft-stack lens` for frontend — CSI-4
- [ ] T23 — Implement frontend lens note retrieval — CSI-4
- [ ] T24 — Create stack-specific lens customization — CSI-4
- [ ] T25 — Update lens path resolution — CSI-4
- [ ] T26 — Write tests for frontend lens integration — CSI-4
- [ ] T27 — Test lens loading with frontend stack — CSI-4

## Session 5 — Backward Compatibility

State: pending · Covers: CSI-5

- [ ] T28 — Ensure existing backend stacks continue working — CSI-5
- [ ] T29 — Implement feature flags for frontend features — CSI-5
- [ ] T30 — Create migration path for existing users — CSI-5
- [ ] T31 — Update documentation for new features — CSI-5
- [ ] T32 — Write backward compatibility tests — CSI-5
- [ ] T33 — Test mixed project detection — CSI-5
- [ ] T34 — Validate no regression in backend detection — CSI-5

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - core integration)

Resume: craft-stack fully integrated with frontend capabilities, maintaining backward compatibility