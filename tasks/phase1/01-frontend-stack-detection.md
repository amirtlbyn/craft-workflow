# TASKS: Frontend Stack Detection System

Spec: frontend-technical-spec.md · Key: FSD-1 · Route: project · State: pending
Checkpoint: `bin/craft-check -- python3 scripts/frontend_stack_detection_test.py`

## Session 1 — React Stack Detection

State: pending · Covers: FSD-1

- [ ] T1 — Create frontend stack detection module in `frontend/stacks/detection.py` — FSD-1
- [ ] T2 — Implement React detection logic (package.json contains react) — FSD-1
- [ ] T3 — Create React stack configuration `frontend/stacks/react/stack.json` — FSD-1
- [ ] T4 — Implement framework detection (Next.js, Remix, Vite) — FSD-1
- [ ] T5 — Write tests for React stack detection in `tests/frontend/test_stack_detection.py` — FSD-1
- [ ] T6 — Update `bin/craft-stack` to include frontend stack detection — FSD-1
- [ ] T7 — Test detection with sample React project — FSD-1

## Session 2 — Vue Stack Detection

State: pending · Covers: FSD-2

- [ ] T8 — Implement Vue detection logic (package.json contains vue) — FSD-2
- [ ] T9 — Create Vue stack configuration `frontend/stacks/vue/stack.json` — FSD-2
- [ ] T10 — Implement framework detection (Nuxt, Vite, Vue CLI) — FSD-2
- [ ] T11 — Write tests for Vue stack detection — FSD-2
- [ ] T12 — Test detection with sample Vue project — FSD-2

## Session 3 — Angular Stack Detection

State: pending · Covers: FSD-3

- [ ] T13 — Implement Angular detection logic (package.json contains @angular/core) — FSD-3
- [ ] T14 — Create Angular stack configuration `frontend/stacks/angular/stack.json` — FSD-3
- [ ] T15 — Write tests for Angular stack detection — FSD-3
- [ ] T16 — Test detection with sample Angular project — FSD-3

## Session 4 — Build Tool Detection

State: pending · Covers: FSD-4

- [ ] T17 — Create build tool detection module `frontend/build/detection.py` — FSD-4
- [ ] T18 — Implement Vite detection (vite.config.js/ts) — FSD-4
- [ ] T19 — Implement Next.js detection (next.config.js) — FSD-4
- [ ] T20 — Implement Webpack detection (webpack.config.js) — FSD-4
- [ ] T21 — Implement Turbopack detection (turbopack.config.js) — FSD-4
- [ ] T22 — Write tests for build tool detection — FSD-4
- [ ] T23 — Test detection with various build configurations — FSD-4

Gate A: `bin/craft-spec trace --session 4` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - core infrastructure)

Resume: Complete stack detection system ready for integration with existing craft-stack command