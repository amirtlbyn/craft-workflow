# TASKS: Frontend Stack Detection System

Spec: frontend-technical-spec.md · Key: FSD-1 · Route: project · State: done

Checkpoint: `bin/craft-check -- python3 scripts/frontend_stack_detection_test.py`

## Session 1 — React Stack Detection

State: done · Covers: FSD-1

- [x] T1 — Create frontend stack detection module in `frontend/stacks/detection.py` — FSD-1
- [x] T2 — Implement React detection logic (package.json contains react) — FSD-1
- [x] T3 — Create React stack configuration `frontend/stacks/react/stack.json` — FSD-1 (shipped as the unified `stacks/react/stack.json` pack)
- [x] T4 — Implement framework detection (Next.js, Remix, Vite) — FSD-1 (detection only; spec §2 frameworks→skills mapping is NOT wired — no stack.json has a `frameworks` key)
- [x] T5 — Write tests for React stack detection in `tests/frontend/test_stack_detection.py` — FSD-1 (shipped as `scripts/frontend_unit_detection_test.py`)
- [x] T6 — Update `bin/craft-stack` to include frontend stack detection — FSD-1 (via `scripts/craft_stack.py` pack detection)
- [x] T7 — Test detection with sample React project — FSD-1

## Session 2 — Vue Stack Detection

State: done · Covers: FSD-2

- [x] T8 — Implement Vue detection logic (package.json contains vue) — FSD-2
- [x] T9 — Create Vue stack configuration `frontend/stacks/vue/stack.json` — FSD-2 (shipped as the unified `stacks/vue/stack.json` pack)
- [x] T10 — Implement framework detection (Nuxt, Vite, Vue CLI) — FSD-2
- [x] T11 — Write tests for Vue stack detection — FSD-2
- [x] T12 — Test detection with sample Vue project — FSD-2

## Session 3 — Angular Stack Detection

State: done · Covers: FSD-3

- [x] T13 — Implement Angular detection logic (package.json contains @angular/core) — FSD-3
- [x] T14 — Create Angular stack configuration `frontend/stacks/angular/stack.json` — FSD-3 (shipped as the unified `stacks/angular/stack.json` pack)
- [x] T15 — Write tests for Angular stack detection — FSD-3
- [x] T16 — Test detection with sample Angular project — FSD-3

## Session 4 — Build Tool Detection

State: done · Covers: FSD-4

- [x] T17 — Create build tool detection module `frontend/build/detection.py` — FSD-4
- [x] T18 — Implement Vite detection (vite.config.js/ts) — FSD-4
- [x] T19 — Implement Next.js detection (next.config.js) — FSD-4
- [x] T20 — Implement Webpack detection (webpack.config.js) — FSD-4
- [x] T21 — Implement Turbopack detection (turbopack.config.js) — FSD-4
- [x] T22 — Write tests for build tool detection — FSD-4
- [x] T23 — Test detection with various build configurations — FSD-4

Gate A: `bin/craft-spec trace --session 4` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - core infrastructure)

Resume: Complete stack detection system ready for integration with existing craft-stack command
