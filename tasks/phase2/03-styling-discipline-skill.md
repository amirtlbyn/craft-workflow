# TASKS: Styling Discipline Skill Development

Spec: frontend-technical-spec.md · Key: SDS-1 · Route: project · State: done

Checkpoint: `bin/craft-check -- python3 scripts/frontend_skill_test.py`

The skill lives at `skills/styling-discipline/SKILL.md` (the plugin's skill
directory — the spec's `frontend/skills/` layout was unified into `skills/`).

## Session 1 — Styling Skill Foundation

State: done · Covers: SDS-1

- [x] T1 — Create styling discipline skill directory — SDS-1 (`skills/styling-discipline/`)
- [x] T2 — Write SKILL.md with styling principles — SDS-1
- [x] T3 — Create CSS methodology selection guide — SDS-1 (One paradigm per repository)
- [x] T4 — Write design system integration patterns — SDS-1 (Design systems)
- [x] T5 — Create responsive design guidelines — SDS-1 (Responsive)
- [x] T6 — Write accessibility compliance section — SDS-1 (Accessibility is a styling concern)
- [x] T7 — Test skill loading in Claude Code — SDS-1 (checkpoint asserts pack routing)

## Session 2 — CSS-in-JS Patterns

State: done · Covers: SDS-2

- [x] T8 — Create CSS-in-JS patterns reference — SDS-2 (CSS-in-JS (React))
- [x] T9 — Write Styled Components best practices — SDS-2
- [x] T10 — Create Emotion usage guidelines — SDS-2
- [x] T11 — Write theme configuration patterns — SDS-2
- [x] T12 — Create dynamic styling patterns — SDS-2
- [x] T13 — Write performance optimization for CSS-in-JS — SDS-2
- [x] T14 — Test with CSS-in-JS examples — SDS-2 (checkpoint coverage checks)

## Session 3 — Utility CSS Patterns

State: done · Covers: SDS-3

- [x] T15 — Create utility CSS patterns reference — SDS-3 (Utility CSS (Tailwind, UnoCSS))
- [x] T16 — Write Tailwind CSS best practices — SDS-3
- [x] T17 — Create UnoCSS usage guidelines — SDS-3
- [x] T18 — Write custom utility configuration — SDS-3
- [x] T19 — Create component extraction patterns — SDS-3
- [x] T20 — Write performance considerations — SDS-3
- [x] T21 — Test with utility CSS examples — SDS-3

## Session 4 — CSS Modules & Preprocessors

State: done · Covers: SDS-4

- [x] T22 — Create CSS Modules patterns reference — SDS-4 (CSS Modules, SCSS/Less, and methodology)
- [x] T23 — Write SCSS/Less best practices — SDS-4
- [x] T24 — Create BEM methodology guidelines — SDS-4
- [x] T25 — Write CSS architecture patterns — SDS-4
- [x] T26 — Create theming with CSS variables — SDS-4
- [x] T27 — Write performance optimization — SDS-4
- [x] T28 — Test with CSS Modules examples — SDS-4

## Session 5 — Design System Integration

State: done · Covers: SDS-5

- [x] T29 — Create design system integration guide — SDS-5 (Design systems)
- [x] T30 — Write MUI (Material-UI) patterns — SDS-5
- [x] T31 — Create Chakra UI usage guidelines — SDS-5
- [x] T32 — Write Ant Design patterns — SDS-5
- [x] T33 — Create custom design system development — SDS-5
- [x] T34 — Write component library integration — SDS-5
- [x] T35 — Test with design system examples — SDS-5 (checkpoint coverage checks)

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - styling system)

Resume: Styling discipline skill ready for lens and gate integration
