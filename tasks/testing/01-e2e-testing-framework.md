# TASKS: End-to-End Testing Framework

Spec: frontend-technical-spec.md · Key: ETF-1 · Route: project · State: done

Checkpoint: `bin/craft-check -- python3 scripts/e2e_frontend_test.py`

The framework lives at `scripts/e2e_frontend_test.py`. It generates throwaway
sample projects per framework in a temp directory and drives every layer of
the rewrite against them the way a real session would: detection → build
analysis → skill routing → lens resolution → component gate.

## Session 1 — Testing Framework Foundation

State: done · Covers: ETF-1

- [x] T1 — Create testing framework directory — ETF-1 (`scripts/e2e_frontend_test.py`; the spec's `frontend/testing/` layout was unified into `scripts/` with the other checkpoints)
- [x] T2 — Implement test project generation — ETF-1 (`write_project` + templates)
- [x] T3 — Create React test project template — ETF-1 (REACT_APP)
- [x] T4 — Create Vue test project template — ETF-1 (VUE_APP)
- [x] T5 — Create Angular test project template — ETF-1 (ANGULAR_APP, plus NUXT_APP and a django+react MIXED_APP)
- [x] T6 — Write test project validation — ETF-1 (detection + failure paths)
- [x] T7 — Test framework with sample projects — ETF-1

## Session 2 — Stack Detection Testing

State: done · Covers: ETF-2

- [x] T8 — Create stack detection test suite — ETF-2 (session 2 of the checkpoint)
- [x] T9 — Write React detection tests — ETF-2
- [x] T10 — Write Vue detection tests — ETF-2
- [x] T11 — Write Angular detection tests — ETF-2
- [x] T12 — Create mixed stack detection tests — ETF-2 (django + react)
- [x] T13 — Write detection failure tests — ETF-2 (empty project; broken manifest never claims a frontend stack)
- [x] T14 — Run comprehensive detection test suite — ETF-2 (all green)

## Session 3 — Build Tool Testing

State: done · Covers: ETF-3

- [x] T15 — Create build tool test suite — ETF-3 (session 3 of the checkpoint)
- [x] T16 — Write Vite configuration tests — ETF-3
- [x] T17 — Write Webpack configuration tests — ETF-3 (scripts/build_tool_integration_test.py)
- [x] T18 — Write Next.js configuration tests — ETF-3 (scripts/frontend_stack_detection_test.py)
- [x] T19 — Create bundle analyzer tests — ETF-3
- [x] T20 — Write performance monitoring tests — ETF-3
- [x] T21 — Run build tool test suite — ETF-3 (all green)

## Session 4 — Skill Testing

State: done · Covers: ETF-4

- [x] T22 — Create skill testing framework — ETF-4 (checkpoint session 4)
- [x] T23 — Write component design skill tests — ETF-4
- [x] T24 — Write state management skill tests — ETF-4
- [x] T25 — Write styling discipline skill tests — ETF-4
- [x] T26 — Create skill loading tests — ETF-4 (routing through craft_stack.skills_for)
- [x] T27 — Write skill integration tests — ETF-4
- [x] T28 — Run skill test suite — ETF-4 (scripts/frontend_skill_test.py green)

## Session 5 — Review Lens Testing

State: done · Covers: ETF-5

- [x] T29 — Create review lens test suite — ETF-5 (checkpoint session 5)
- [x] T30 — Write component lens tests — ETF-5
- [x] T31 — Write accessibility lens tests — ETF-5
- [x] T32 — Write performance lens tests — ETF-5 (performance items live in the component lens checklist and frontend_performance_standards; no separate lens shipped)
- [x] T33 — Create lens integration tests — ETF-5 (resolution over all four frontend stacks)
- [x] T34 — Write reviewer integration tests — ETF-5 (lens files are routed by review-protocol)
- [x] T35 — Run review lens test suite — ETF-5 (scripts/frontend_lens_test.py green)

## Session 6 — Gate Testing

State: done · Covers: ETF-6

- [x] T36 — Create gate testing framework — ETF-6 (checkpoint session 6)
- [x] T37 — Write component gate tests — ETF-6 (violations + decide)
- [x] T38 — Write bundle gate tests — ETF-6 (thresholds exercised via analyze_bundle)
- [x] T39 — Write accessibility gate tests — ETF-6 (lens routing + axe verification section)
- [x] T40 — Create gate hook tests — ETF-6 (hooks.json registration asserted)
- [x] T41 — Write gate integration tests — ETF-6 (gate against the generated sample component)
- [x] T42 — Run gate test suite — ETF-6 (scripts/component_gate_test.py green)

Gate A: `bin/craft-spec trace --session 6` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - testing framework)

Resume: The frontend rewrite is implemented and verified end to end.
