# TASKS: Component Design Skill Development

Spec: frontend-technical-spec.md · Key: CDS-1 · Route: project · State: pending
Checkpoint: `bin/craft-check -- python3 scripts/component_skill_test.py`

## Session 1 — Component Design Skill Foundation

State: pending · Covers: CDS-1

- [ ] T1 — Create component design skill directory `frontend/skills/component-design/` — CDS-1
- [ ] T2 — Write SKILL.md with component design principles — CDS-1
- [ ] T3 — Create props design guidelines section — CDS-1
- [ ] T4 — Create component composition patterns section — CDS-1
- [ ] T5 — Write state management guidelines for components — CDS-1
- [ ] T6 — Create performance optimization section — CDS-1
- [ ] T7 — Write accessibility guidelines for components — CDS-1
- [ ] T8 — Test skill loading in Claude Code — CDS-1

## Session 2 — React-Specific Component Patterns

State: pending · Covers: CDS-2

- [ ] T9 — Create React component patterns reference — CDS-2
- [ ] T10 — Write React.memo() usage guidelines — CDS-2
- [ ] T11 — Create useCallback/useMemo best practices — CDS-2
- [ ] T12 — Write custom hooks design patterns — CDS-2
- [ ] T13 — Create context API usage guidelines — CDS-2
- [ ] T14 — Write error boundary implementation patterns — CDS-2
- [ ] T15 — Test with React component examples — CDS-2

## Session 3 — Vue-Specific Component Patterns

State: pending · Covers: CDS-3

- [ ] T16 — Create Vue component patterns reference — CDS-3
- [ ] T17 — Write composition API best practices — CDS-3
- [ ] T18 — Create computed properties guidelines — CDS-3
- [ ] T19 — Write watchers usage patterns — CDS-3
- [ ] T20 — Create provide/inject patterns — CDS-3
- [ ] T21 — Write slot/scoped slot patterns — CDS-3
- [ ] T22 — Test with Vue component examples — CDS-3

## Session 4 — Angular-Specific Component Patterns

State: pending · Covers: CDS-4

- [ ] T23 — Create Angular component patterns reference — CDS-4
- [ ] T24 — Write OnPush change detection guidelines — CDS-4
- [ ] T25 — Create pure pipes patterns — CDS-4
- [ ] T26 — Write trackBy usage for ngFor — CDS-4
- [ ] T27 — Create unsubscribe patterns — CDS-4
- [ ] T28 — Write dependency injection patterns — CDS-4
- [ ] T29 — Test with Angular component examples — CDS-4

## Session 5 — Component Testing Integration

State: pending · Covers: CDS-5

- [ ] T30 — Create component testing guidelines section — CDS-5
- [ ] T31 — Write props testing patterns — CDS-5
- [ ] T32 — Create event handler testing — CDS-5
- [ ] T33 — Write state transition testing — CDS-5
- [ ] T34 — Create accessibility testing integration — CDS-5
- [ ] T35 — Write performance testing patterns — CDS-5
- [ ] T36 — Test with component test examples — CDS-5

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - skill development)

Resume: Component design skill ready for integration with craft workflow