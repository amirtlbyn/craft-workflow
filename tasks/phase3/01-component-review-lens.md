# TASKS: Component Review Lens Development

Spec: frontend-technical-spec.md · Key: CRL-1 · Route: project · State: done

Checkpoint: `bin/craft-check -- python3 scripts/frontend_lens_test.py`

The lens lives at `skills/review-protocol/lenses/component.md` (the plugin's
lens directory — the spec's `frontend/lenses/` layout was unified into
`skills/review-protocol/lenses/`). The stack-specific notes resolve through
`bin/craft-stack lens component` from each stack's `stacks/<id>/lenses.md`.

## Session 1 — Component Lens Foundation

State: done · Covers: CRL-1

- [x] T1 — Create component lens directory — CRL-1 (`skills/review-protocol/lenses/`)
- [x] T2 — Write component.md lens file with checklist — CRL-1
- [x] T3 — Create props validation section — CRL-1
- [x] T4 — Write event handling patterns checklist — CRL-1 (emits contract items)
- [x] T5 — Create lifecycle management guidelines — CRL-1 (teardown items)
- [x] T6 — Write performance considerations checklist — CRL-1 (measured memoization items)
- [x] T7 — Test lens loading in reviewer — CRL-1 (checkpoint asserts protocol routing + stack resolution)

## Session 2 — React Component Lens

State: done · Covers: CRL-2

- [x] T8 — Create React-specific component lens section — CRL-2 (Stack notes: React)
- [x] T9 — Write React.memo() validation checklist — CRL-2
- [x] T10 — Create useCallback/useMemo validation — CRL-2
- [x] T11 — Write hooks rules validation — CRL-2
- [x] T12 — Create custom hooks validation — CRL-2 (hooks contract items)
- [x] T13 — Write error boundary validation — CRL-2
- [x] T14 — Test with React component reviews — CRL-2 (checkpoint resolution over the react pack)

## Session 3 — Vue Component Lens

State: done · Covers: CRL-3

- [x] T15 — Create Vue-specific component lens section — CRL-3 (Stack notes: Vue; stacks/vue/lenses.md Component Lens)
- [x] T16 — Write computed properties validation — CRL-3
- [x] T17 — Create watchers validation checklist — CRL-3
- [x] T18 — Write composition API patterns validation — CRL-3
- [x] T19 — Create provide/inject validation — CRL-3
- [x] T20 — Write slot usage validation — CRL-3
- [x] T21 — Test with Vue component reviews — CRL-3

## Session 4 — Angular Component Lens

State: done · Covers: CRL-4

- [x] T22 — Create Angular-specific component lens section — CRL-4 (Stack notes: Angular; stacks/angular/lenses.md Component Lens)
- [x] T23 — Write OnPush change detection validation — CRL-4
- [x] T24 — Create pure pipes validation — CRL-4 (Angular stack notes in the skill)
- [x] T25 — Write trackBy validation for ngFor — CRL-4
- [x] T26 — Create unsubscribe patterns validation — CRL-4
- [x] T27 — Write dependency injection validation — CRL-4
- [x] T28 — Test with Angular component reviews — CRL-4

## Session 5 — Component Testing Lens Integration

State: done · Covers: CRL-5

- [x] T29 — Create component testing validation section — CRL-5 (testable-from-contract item)
- [x] T30 — Write props testing validation — CRL-5
- [x] T31 — Create event testing validation — CRL-5
- [x] T32 — Write state transition testing validation — CRL-5 (render states item)
- [x] T33 — Create accessibility testing validation — CRL-5 (accessibility lens owns this; cross-referenced)
- [x] T34 — Write performance testing validation — CRL-5
- [x] T35 — Test with component test reviews — CRL-5 (checkpoint coverage checks)

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - review system)

Resume: Component lens ready for gate enforcement (phase 4)
