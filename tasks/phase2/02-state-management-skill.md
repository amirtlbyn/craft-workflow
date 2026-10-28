# TASKS: State Management Skill Development

Spec: frontend-technical-spec.md · Key: SMS-1 · Route: project · State: done

Checkpoint: `bin/craft-check -- python3 scripts/frontend_skill_test.py`

The skill lives at `skills/state-management/SKILL.md` (the plugin's skill
directory — the spec's `frontend/skills/` layout was unified into `skills/`).

## Session 1 — State Management Skill Foundation

State: done · Covers: SMS-1

- [x] T1 — Create state management skill directory — SMS-1 (`skills/state-management/`)
- [x] T2 — Write SKILL.md with state management principles — SMS-1
- [x] T3 — Create state selection guidelines (local vs global vs server) — SMS-1 (The taxonomy)
- [x] T4 — Write state patterns section (derived state, normalization) — SMS-1 (Dependency visibility; SSR rule)
- [x] T5 — Create performance considerations section — SMS-1 (Performance)
- [x] T6 — Write state testing guidelines — SMS-1 (Testing state)
- [x] T7 — Test skill loading in Claude Code — SMS-1 (checkpoint asserts pack routing)

## Session 2 — React State Management Patterns

State: done · Covers: SMS-2

- [x] T8 — Create React state management reference — SMS-2 (React patterns)
- [x] T9 — Write useState/useReducer patterns — SMS-2
- [x] T10 — Create Context API state patterns — SMS-2
- [x] T11 — Write Zustand usage guidelines — SMS-2
- [x] T12 — Create Jotai/Recoil patterns — SMS-2
- [x] T13 — Write TanStack Query server state patterns — SMS-2
- [x] T14 — Test with React state examples — SMS-2 (checkpoint coverage checks)

## Session 3 — Vue State Management Patterns

State: done · Covers: SMS-3

- [x] T15 — Create Vue state management reference — SMS-3 (Vue patterns)
- [x] T16 — Write reactive()/ref() patterns — SMS-3
- [x] T17 — Create computed() property patterns — SMS-3
- [x] T18 — Write Pinia store patterns — SMS-3
- [x] T19 — Create Vuex migration guidelines — SMS-3
- [x] T20 — Write Vue Query server state patterns — SMS-3
- [x] T21 — Test with Vue state examples — SMS-3

## Session 4 — Angular State Management Patterns

State: done · Covers: SMS-4

- [x] T22 — Create Angular state management reference — SMS-4 (Angular patterns)
- [x] T23 — Write RxJS state patterns — SMS-4
- [x] T24 — Create NgRx store patterns — SMS-4
- [x] T25 — Write Akita store guidelines — SMS-4
- [x] T26 — Create service-based state patterns — SMS-4
- [x] T27 — Write Angular Query server state patterns — SMS-4
- [x] T28 — Test with Angular state examples — SMS-4

## Session 5 — Performance Optimization

State: done · Covers: SMS-5

- [x] T29 — Create state slicing patterns — SMS-5
- [x] T30 — Write selector optimization with reselect — SMS-5
- [x] T31 — Create batch update patterns — SMS-5
- [x] T32 — Write memoization guidelines — SMS-5
- [x] T33 — Create lazy loading state patterns — SMS-5 (store-per-domain keeps slices lazy; covered under Performance/state slicing)
- [x] T34 — Write state persistence patterns — SMS-5
- [x] T35 — Test performance optimization examples — SMS-5 (checkpoint coverage checks)

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - state management)

Resume: State management skill ready for lens and gate integration
