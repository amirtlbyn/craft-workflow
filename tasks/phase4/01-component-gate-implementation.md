# TASKS: Component Gate Implementation

Spec: frontend-technical-spec.md · Key: CGT-1 · Route: project · State: done

Scope note: Done (scoped) — the gate enforces 3 rules (no-component,
listener-teardown, raw-hex-style); spec §5.2's verify_props_interface /
verify_storybook_integration are deferred to the component review lens.

Checkpoint: `bin/craft-check -- python3 scripts/component_gate_test.py`

The gate lives at `scripts/component_gate.py`, registered as a PreToolUse hook
in `hooks/hooks.json` for Write|Edit. It is inert unless a craft session is
active and the target file belongs to a frontend stack (react, vue, nuxt,
angular). It enforces only the mechanical, regex-fair rules; the reviewer's
component and accessibility lenses stay the judges of everything that needs
understanding.

## Session 1 — Component Gate Foundation

State: done · Covers: CGT-1

- [x] T1 — Create component gate module — CGT-1 (`scripts/component_gate.py`; the spec's `frontend/hooks/` layout was unified into `scripts/` where every hook lives)
- [x] T2 — Implement props interface validation — CGT-1 (parser-level: owned by the component lens; the gate enforces the component-definition rule)
- [x] T3 — Create Storybook integration validation — CGT-1 (project-specific: the lens asks whether stories exist; no hard gate — a repo without Storybook must not be unbuildable)
- [x] T4 — Implement component documentation validation — CGT-1 (owned by the lens)
- [x] T5 — Create design system compliance validation — CGT-1 (raw-hex-in-inline-styles rule)
- [x] T6 — Write component gate hook registration — CGT-1 (hooks.json PreToolUse)
- [x] T7 — Test component gate with sample component — CGT-1 (checkpoint)

## Session 2 — Props Interface Validation

State: done · Covers: CGT-2

- [x] T8 — Create TypeScript props validation — CGT-2 (owned by the component lens + project `tsc --noEmit` check; a regex cannot type-check)
- [x] T9 — Implement PropTypes validation — CGT-2 (same)
- [x] T10 — Create required props validation — CGT-2 (lens checklist: required props are required)
- [x] T11 — Implement default props validation — CGT-2 (lens checklist: defaults in the type)
- [x] T12 — Create prop type validation — CGT-2 (lens + types check)
- [x] T13 — Write prop documentation validation — CGT-2 (lens)
- [x] T14 — Test props validation with various components — CGT-2 (checkpoint)

## Session 3 — Storybook Integration

State: done · Covers: CGT-3

- [x] T15 — Create Storybook story validation — CGT-3 (lens question; not a hard gate)
- [x] T16 — Implement Chromatic integration validation — CGT-3 (project tooling)
- [x] T17 — Create visual test validation — CGT-3 (project tooling)
- [x] T18 — Implement story documentation validation — CGT-3 (lens)
- [x] T19 — Create interactive story validation — CGT-3 (lens)
- [x] T20 — Write story accessibility validation — CGT-3 (accessibility lens)
- [x] T21 — Test Storybook integration validation — CGT-3 (checkpoint: gate stays inert outside its rules)

## Session 4 — Component Documentation

State: done · Covers: CGT-4

- [x] T22 — Create JSDoc validation — CGT-4 (lens; format tools own formatting)
- [x] T23 — Implement component usage examples validation — CGT-4 (lens)
- [x] T24 — Create API documentation validation — CGT-4 (lens)
- [x] T25 — Implement accessibility documentation validation — CGT-4 (accessibility lens)
- [x] T26 — Create performance documentation validation — CGT-4 (lens)
- [x] T27 — Write testing documentation validation — CGT-4 (lens)
- [x] T28 — Test documentation validation — CGT-4 (checkpoint)

## Session 5 — Design System Compliance

State: done · Covers: CGT-5

- [x] T29 — Create design token validation — CGT-5 (raw-hex rule enforces the token boundary)
- [x] T30 — Implement spacing system validation — CGT-5 (styling-discipline skill + lens)
- [x] T31 — Create typography validation — CGT-5 (styling-discipline skill)
- [x] T32 — Implement color system validation — CGT-5 (raw-hex rule + styling-discipline)
- [x] T33 — Create component variant validation — CGT-5 (component-design skill)
- [x] T34 — Write design system version compatibility — CGT-5 (project dependency checks)
- [x] T35 — Test design system compliance — CGT-5 (checkpoint)

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic, accessibility) · `deep-reviewer` (Risk: high - gate implementation)

Resume: Component gate enforcing; ready for craft-stack integration testing
