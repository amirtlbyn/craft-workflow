# TASKS: Accessibility Review Lens Development

Spec: frontend-technical-spec.md · Key: ARL-1 · Route: project · State: pending
Checkpoint: `bin/craft-check -- python3 scripts/accessibility_lens_test.py`

## Session 1 — Accessibility Lens Foundation

State: pending · Covers: ARL-1

- [ ] T1 — Create accessibility lens directory `frontend/lenses/accessibility/` — ARL-1
- [ ] T2 — Write accessibility.md lens file with checklist — ARL-1
- [ ] T3 — Create keyboard accessibility section — ARL-1
- [ ] T4 — Write ARIA attributes validation — ARL-1
- [ ] T5 — Create color contrast validation — ARL-1
- [ ] T6 — Write screen reader compatibility — ARL-1
- [ ] T7 — Test lens loading in reviewer — ARL-1

## Session 2 — Interactive Elements Accessibility

State: pending · Covers: ARL-2

- [ ] T8 — Create button accessibility validation — ARL-2
- [ ] T9 — Write link accessibility validation — ARL-2
- [ ] T10 — Create form control accessibility — ARL-2
- [ ] T11 — Write focus management validation — ARL-2
- [ ] T12 — Create modal/dialog accessibility — ARL-2
- [ ] T13 — Write navigation accessibility — ARL-2
- [ ] T14 — Test with interactive element reviews — ARL-2

## Session 3 — Visual Accessibility

State: pending · Covers: ARL-3

- [ ] T15 — Create color contrast validation tools — ARL-3
- [ ] T16 — Write text size and spacing validation — ARL-3
- [ ] T17 — Create visual focus indicators — ARL-3
- [ ] T18 — Write motion and animation validation — ARL-3
- [ ] T19 — Create responsive design accessibility — ARL-3
- [ ] T20 — Write high contrast mode support — ARL-3
- [ ] T21 — Test with visual accessibility reviews — ARL-3

## Session 4 — Screen Reader Accessibility

State: pending · Covers: ARL-4

- [ ] T22 — Create semantic HTML validation — ARL-4
- [ ] T23 — Write ARIA landmark roles validation — ARL-4
- [ ] T24 — Create ARIA live regions validation — ARL-4
- [ ] T25 — Write screen reader announcements — ARL-4
- [ ] T26 — Create heading structure validation — ARL-4
- [ ] T27 — Write alternative text validation — ARL-4
- [ ] T28 — Test with screen reader reviews — ARL-4

## Session 5 — Automated Accessibility Testing Integration

State: pending · Covers: ARL-5

- [ ] T29 — Create axe-core integration module — ARL-5
- [ ] T30 — Write automated accessibility test runner — ARL-5
- [ ] T31 — Create accessibility violation reporting — ARL-5
- [ ] T32 — Write WCAG compliance checking — ARL-5
- [ ] T33 — Create accessibility score calculation — ARL-5
- [ ] T34 — Write integration with craft-check — ARL-5
- [ ] T35 — Test automated accessibility reviews — ARL-5

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - accessibility compliance)

Resume: Accessibility review lens ready for integration with component testing