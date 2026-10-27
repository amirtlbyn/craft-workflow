# TASKS: Component Review Lens Development

Spec: frontend-technical-spec.md · Key: CRL-1 · Route: project · State: pending
Checkpoint: `bin/craft-check -- python3 scripts/component_lens_test.py`

## Session 1 — Component Lens Foundation

State: pending · Covers: CRL-1

- [ ] T1 — Create component lens directory `frontend/lenses/component/` — CRL-1
- [ ] T2 — Write component.md lens file with checklist — CRL-1
- [ ] T3 — Create props validation section — CRL-1
- [ ] T4 — Write event handling patterns checklist — CRL-1
- [ ] T5 — Create lifecycle management guidelines — CRL-1
- [ ] T6 — Write performance considerations checklist — CRL-1
- [ ] T7 — Test lens loading in reviewer — CRL-1

## Session 2 — React Component Lens

State: pending · Covers: CRL-2

- [ ] T8 — Create React-specific component lens section — CRL-2
- [ ] T9 — Write React.memo() validation checklist — CRL-2
- [ ] T10 — Create useCallback/useMemo validation — CRL-2
- [ ] T11 — Write hooks rules validation — CRL-2
- [ ] T12 — Create custom hooks validation — CRL-2
- [ ] T13 — Write error boundary validation — CRL-2
- [ ] T14 — Test with React component reviews — CRL-2

## Session 3 — Vue Component Lens

State: pending · Covers: CRL-3

- [ ] T15 — Create Vue-specific component lens section — CRL-3
- [ ] T16 — Write computed properties validation — CRL-3
- [ ] T17 — Create watchers validation checklist — CRL-3
- [ ] T18 — Write composition API patterns validation — CRL-3
- [ ] T19 — Create provide/inject validation — CRL-3
- [ ] T20 — Write slot usage validation — CRL-3
- [ ] T21 — Test with Vue component reviews — CRL-3

## Session 4 — Angular Component Lens

State: pending · Covers: CRL-4

- [ ] T22 — Create Angular-specific component lens section — CRL-4
- [ ] T23 — Write OnPush change detection validation — CRL-4
- [ ] T24 — Create pure pipes validation — CRL-4
- [ ] T25 — Write trackBy validation for ngFor — CRL-4
- [ ] T26 — Create unsubscribe patterns validation — CRL-4
- [ ] T27 — Write dependency injection validation — CRL-4
- [ ] T28 — Test with Angular component reviews — CRL-4

## Session 5 — Component Testing Lens Integration

State: pending · Covers: CRL-5

- [ ] T29 — Create component testing validation section — CRL-5
- [ ] T30 — Write props testing validation — CRL-5
- [ ] T31 — Create event testing validation — CRL-5
- [ ] T32 — Write state transition testing validation — CRL-5
- [ ] T33 — Create accessibility testing validation — CRL-5
- [ ] T34 — Write performance testing validation — CRL-5
- [ ] T35 — Test with component test reviews — CRL-5

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - review system)

Resume: Component review lens ready for integration with existing review protocol