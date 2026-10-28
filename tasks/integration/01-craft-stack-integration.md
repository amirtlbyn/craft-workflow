# TASKS: craft-stack Integration with Frontend

Spec: frontend-technical-spec.md · Key: CSI-1 · Route: project · State: done

Checkpoint: `bin/craft-check -- python3 scripts/craft_stack_integration_test.py`

Frontend stacks integrate through the same pack system as the backend stacks:
`stacks/<id>/stack.json` plus `stacks/<id>/lenses.md`. `frontend/stacks/
detection.py` feeds the framework detail; `scripts/craft_stack.py` routes
detect, skills, checks, lenses, globs, and path ownership.

## Session 1 — craft-stack Extension

State: done · Covers: CSI-1

- [x] T1 — Modify `bin/craft-stack` to detect frontend stacks — CSI-1 (pack-based: react/vue/nuxt/angular stack.json)
- [x] T2 — Implement frontend stack priority system — CSI-1 (priority fields; nuxt 85 beats vue 80 by language priority)
- [x] T3 — Create frontend stack detection in existing detection logic — CSI-1 (`frontend/stacks/detection.py` + pack `detect` rules)
- [x] T4 — Update stack reporting to include frontend stacks — CSI-1 (detect output shows frontend packs with evidence)
- [x] T5 — Implement mixed stack detection (fullstack projects) — CSI-1 (checkpoint: django + react, path ownership per directory)
- [x] T6 — Write integration tests for frontend stack detection — CSI-1 (checkpoint + `scripts/frontend_unit_detection_test.py`)
- [x] T7 — Test with sample fullstack project — CSI-1

## Session 2 — craft-stack skills Integration

State: done · Covers: CSI-2

- [x] T8 — Extend `bin/craft-stack skills` for frontend — CSI-2 (packs list the frontend skills)
- [x] T9 — Implement frontend skill routing based on stack — CSI-2
- [x] T10 — Create frontend skill loading logic — CSI-2 (skills_for only names skills whose SKILL.md exists)
- [x] T11 — Update skill selection algorithm — CSI-2 (path ownership routes per-directory)
- [x] T12 — Write tests for frontend skill routing — CSI-2 (checkpoint)
- [x] T13 — Test with React project skill selection — CSI-2
- [x] T14 — Test with Vue project skill selection — CSI-2

## Session 3 — craft-stack checks Integration

State: done · Covers: CSI-3

- [x] T15 — Extend `bin/craft-stack checks` for frontend — CSI-3 (pack checks with when_script/when_dependency/when_file)
- [x] T16 — Implement frontend check commands — CSI-3 (npm/pnpm/yarn/bun manager resolution)
- [x] T17 — Create bundle size check integration — CSI-3 (`frontend/build/analyzer.py analyze_bundle`, thresholds from spec §7.1)
- [x] T18 — Implement accessibility check integration — CSI-3 (accessibility lens + axe command in Verification)
- [x] T19 — Update check command resolution — CSI-3 (unchanged resolution path, pack-driven)
- [x] T20 — Write tests for frontend check commands — CSI-3 (checkpoint)
- [x] T21 — Test check execution with frontend project — CSI-3

## Session 4 — craft-stack lens Integration

State: done · Covers: CSI-4

- [x] T22 — Extend `bin/craft-stack lens` for frontend — CSI-4 (component/accessibility sections in each frontend pack's lenses.md)
- [x] T23 — Implement frontend lens note retrieval — CSI-4 (lens_addendum exact + keyword fallback)
- [x] T24 — Create stack-specific lens customization — CSI-4 (per-stack notes in lenses/component.md, lenses/accessibility.md)
- [x] T25 — Update lens path resolution — CSI-4 (`--paths` ownership routing, unchanged)
- [x] T26 — Write tests for frontend lens integration — CSI-1 (scripts/frontend_lens_test.py)
- [x] T27 — Test lens loading with frontend stack — CSI-4 (verified: react project resolves component + accessibility)

## Session 5 — Backward Compatibility

State: done · Covers: CSI-5

- [x] T28 — Ensure existing backend stacks continue working — CSI-5 (checkpoint: django, go detection unchanged)
- [x] T29 — Implement feature flags for frontend features — CSI-5 (component gate is session-gated and CRAFT_HOOKS=off killable, same as every hook)
- [x] T30 — Create migration path for existing users — CSI-5 (no config change required; detection is additive)
- [x] T31 — Update documentation for new features — CSI-5 (README stack table already routes nuxt/vue; lenses documented in review-protocol)
- [x] T32 — Write backward compatibility tests — CSI-5 (checkpoint session 5)
- [x] T33 — Test mixed project detection — CSI-5
- [x] T34 — Validate no regression in backend detection — CSI-5 (full pytest suite green)

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - core integration)

Resume: craft-stack integration verified; ready for e2e testing framework
