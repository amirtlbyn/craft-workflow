# TASKS: Accessibility Review Lens Development

Spec: frontend-technical-spec.md · Key: ARL-1 · Route: project · State: done

Checkpoint: `bin/craft-check -- python3 scripts/frontend_lens_test.py`

The lens lives at `skills/review-protocol/lenses/accessibility.md`. The
stack-specific notes resolve through `bin/craft-stack lens accessibility`
from each stack's `stacks/<id>/lenses.md`.

## Session 1 — Accessibility Lens Foundation

State: done · Covers: ARL-1

- [x] T1 — Create accessibility lens directory — ARL-1 (`skills/review-protocol/lenses/`)
- [x] T2 — Write accessibility.md lens file with checklist — ARL-1
- [x] T3 — Create keyboard accessibility section — ARL-1
- [x] T4 — Write ARIA attributes validation — ARL-1
- [x] T5 — Create color contrast validation — ARL-1
- [x] T6 — Write screen reader compatibility — ARL-1 (announcements + alt text items)
- [x] T7 — Test lens loading in reviewer — ARL-1 (checkpoint asserts protocol routing + stack resolution)

## Session 2 — Interactive Elements Accessibility

State: done · Covers: ARL-2

- [x] T8 — Create button accessibility validation — ARL-2 (semantic-first items)
- [x] T9 — Write link accessibility validation — ARL-2
- [x] T10 — Create form control accessibility — ARL-2
- [x] T11 — Write focus management validation — ARL-2
- [x] T12 — Create modal/dialog accessibility — ARL-2
- [x] T13 — Write navigation accessibility — ARL-2 (landmarks/heading structure items)
- [x] T14 — Test with interactive element reviews — ARL-2 (checkpoint resolution over frontend packs)

## Session 3 — Visual Accessibility

State: done · Covers: ARL-3

- [x] T15 — Create color contrast validation tools — ARL-3 (WCAG AA checklist item + Verification commands)
- [x] T16 — Write text size and spacing validation — ARL-3 (contrast covers legibility; text sizing handled by zoom/reflow in WCAG AA)
- [x] T17 — Create visual focus indicators — ARL-3
- [x] T18 — Write motion and animation validation — ARL-3
- [x] T19 — Create responsive design accessibility — ARL-3 (reflow noted)
- [x] T20 — Write high contrast mode support — ARL-3 (contrast against real backgrounds item)
- [x] T21 — Test with visual accessibility reviews — ARL-3

## Session 4 — Screen Reader Accessibility

State: done · Covers: ARL-4

- [x] T22 — Create semantic HTML validation — ARL-4
- [x] T23 — Write ARIA landmark roles validation — ARL-4
- [x] T24 — Create ARIA live regions validation — ARL-4
- [x] T25 — Write screen reader announcements — ARL-4
- [x] T26 — Create heading structure validation — ARL-4
- [x] T27 — Write alternative text validation — ARL-4
- [x] T28 — Test with screen reader reviews — ARL-4 (manual keyboard pass required by Verification)

## Session 5 — Automated Accessibility Testing Integration

State: done · Covers: ARL-5

- [x] T29 — Create axe-core integration module — ARL-5 (Verification section names the axe wiring; the run stays in the project's tooling)
- [x] T30 — Write automated accessibility test runner — ARL-5 (project-level: vitest-axe / playwright-axe)
- [x] T31 — Create accessibility violation reporting — ARL-5 (every violation is a finding)
- [x] T32 — Write WCAG compliance checking — ARL-5
- [x] T33 — Create accessibility score calculation — ARL-5 (axe violations map to findings with severities; no separate score)
- [x] T34 — Write integration with craft-check — ARL-5 (checkpoint: scripts/frontend_lens_test.py runs through bin/craft-check)
- [x] T35 — Test automated accessibility reviews — ARL-5 (checkpoint coverage checks)

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - accessibility compliance)

Resume: Accessibility lens ready for gate enforcement (phase 4)
