# TASKS: State Management Skill Development

Spec: frontend-technical-spec.md · Key: SMS-1 · Route: project · State: pending
Checkpoint: `bin/craft-check -- python3 scripts/state_management_skill_test.py`

## Session 1 — State Management Skill Foundation

State: pending · Covers: SMS-1

- [ ] T1 — Create state management skill directory `frontend/skills/state-management/` — SMS-1
- [ ] T2 — Write SKILL.md with state management principles — SMS-1
- [ ] T3 — Create state selection guidelines (local vs global vs server) — SMS-1
- [ ] T4 — Write state patterns section (derived state, normalization) — SMS-1
- [ ] T5 — Create performance considerations section — SMS-1
- [ ] T6 — Write state testing guidelines — SMS-1
- [ ] T7 — Test skill loading in Claude Code — SMS-1

## Session 2 — React State Management Patterns

State: pending · Covers: SMS-2

- [ ] T8 — Create React state management reference — SMS-2
- [ ] T9 — Write useState/useReducer patterns — SMS-2
- [ ] T10 — Create Context API state patterns — SMS-2
- [ ] T11 — Write Zustand usage guidelines — SMS-2
- [ ] T12 — Create Jotai/Recoil patterns — SMS-2
- [ ] T13 — Write TanStack Query server state patterns — SMS-2
- [ ] T14 — Test with React state examples — SMS-2

## Session 3 — Vue State Management Patterns

State: pending · Covers: SMS-3

- [ ] T15 — Create Vue state management reference — SMS-3
- [ ] T16 — Write reactive()/ref() patterns — SMS-3
- [ ] T17 — Create computed() property patterns — SMS-3
- [ ] T18 — Write Pinia store patterns — SMS-3
- [ ] T19 — Create Vuex migration guidelines — SMS-3
- [ ] T20 — Write Vue Query server state patterns — SMS-3
- [ ] T21 — Test with Vue state examples — SMS-3

## Session 4 — Angular State Management Patterns

State: pending · Covers: SMS-4

- [ ] T22 — Create Angular state management reference — SMS-4
- [ ] T23 — Write RxJS state patterns — SMS-4
- [ ] T24 — Create NgRx store patterns — SMS-4
- [ ] T25 — Write Akita store guidelines — SMS-4
- [ ] T26 — Create service-based state patterns — SMS-4
- [ ] T27 — Write Angular Query server state patterns — SMS-4
- [ ] T28 — Test with Angular state examples — SMS-4

## Session 5 — Performance Optimization

State: pending · Covers: SMS-5

- [ ] T29 — Create state slicing patterns — SMS-5
- [ ] T30 — Write selector optimization with reselect — SMS-5
- [ ] T31 — Create batch update patterns — SMS-5
- [ ] T32 — Write memoization guidelines — SMS-5
- [ ] T33 — Create lazy loading state patterns — SMS-5
- [ ] T34 — Write state persistence patterns — SMS-5
- [ ] T35 — Test performance optimization examples — SMS-5

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - state management)

Resume: State management skill ready for integration with component design skill