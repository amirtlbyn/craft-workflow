# TASKS: Component Design Skill Development

Spec: frontend-technical-spec.md · Key: CDS-1 · Route: project · State: done

Checkpoint: `bin/craft-check -- python3 scripts/frontend_skill_test.py`

The skill lives at `skills/component-design/SKILL.md` (the plugin's skill
directory — the spec's `frontend/skills/` layout was unified into `skills/`).
The standards detail lives in
`standards/component_design_standards.ai.md`.

## Session 1 — Component Design Skill Foundation

State: done · Covers: CDS-1

- [x] T1 — Create component design skill directory — CDS-1 (`skills/component-design/`)
- [x] T2 — Write SKILL.md with component design principles — CDS-1
- [x] T3 — Create props design guidelines section — CDS-1 (Props and emits)
- [x] T4 — Create component composition patterns section — CDS-1 (Responsibility and boundaries; Composition in the standards file)
- [x] T5 — Write state management guidelines for components — CDS-1 (`state-management` owns the taxonomy; boundary stated in the skill)
- [x] T6 — Create performance optimization section — CDS-1 (Performance)
- [x] T7 — Write accessibility guidelines for components — CDS-1 (Accessibility section + `accessibility_standards.ai.md`)
- [x] T8 — Test skill loading in Claude Code — CDS-1 (checkpoint asserts the pack routing returns the skill; `bin/craft-stack skills` verified)

## Session 2 — React-Specific Component Patterns

State: done · Covers: CDS-2

- [x] T9 — Create React component patterns reference — CDS-2 (React patterns)
- [x] T10 — Write React.memo() usage guidelines — CDS-2
- [x] T11 — Create useCallback/useMemo best practices — CDS-2
- [x] T12 — Write custom hooks design patterns — CDS-2
- [x] T13 — Create context API usage guidelines — CDS-2
- [x] T14 — Write error boundary implementation patterns — CDS-2
- [x] T15 — Test with React component examples — CDS-2 (checkpoint coverage checks)

## Session 3 — Vue-Specific Component Patterns

State: done · Covers: CDS-3

- [x] T16 — Create Vue component patterns reference — CDS-3 (Vue patterns)
- [x] T17 — Write composition API best practices — CDS-3
- [x] T18 — Create computed properties guidelines — CDS-3
- [x] T19 — Write watchers usage patterns — CDS-3
- [x] T20 — Create provide/inject patterns — CDS-3
- [x] T21 — Write slot/scoped slot patterns — CDS-3
- [x] T22 — Test with Vue component examples — CDS-3

## Session 4 — Angular-Specific Component Patterns

State: done · Covers: CDS-4

- [x] T23 — Create Angular component patterns reference — CDS-4 (Angular patterns)
- [x] T24 — Write OnPush change detection guidelines — CDS-4
- [x] T25 — Create pure pipes patterns — CDS-4
- [x] T26 — Write trackBy usage for ngFor — CDS-4
- [x] T27 — Create unsubscribe patterns — CDS-4
- [x] T28 — Write dependency injection patterns — CDS-4
- [x] T29 — Test with Angular component examples — CDS-4

## Session 5 — Component Testing Integration

State: done · Covers: CDS-5

- [x] T30 — Create component testing guidelines section — CDS-5 (Testing)
- [x] T31 — Write props testing patterns — CDS-5
- [x] T32 — Create event handler testing — CDS-5
- [x] T33 — Write state transition testing — CDS-5
- [x] T34 — Create accessibility testing integration — CDS-5
- [x] T35 — Write performance testing patterns — CDS-5
- [x] T36 — Test with component test examples — CDS-5 (checkpoint coverage checks)

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - skill development)

Resume: Component design skill ready for integration with craft workflow
