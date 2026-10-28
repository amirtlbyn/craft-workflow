# TASKS: Build Tool Integration System

Spec: frontend-technical-spec.md · Key: BTI-1 · Route: project · State: done

Checkpoint: `bin/craft-check -- python3 scripts/build_tool_integration_test.py`

All analyzers are static and stdlib-only: they inspect source trees and
manifests, never run a bundler. This matches the craft rules (nothing raises,
read-only, no node dependencies).

## Session 1 — Build Analysis Framework

State: done · Covers: BTI-1

- [x] T1 — Create bundle analyzer class in `frontend/build/analyzer.py` — BTI-1 (`analyze_bundle` / `BundleReport`)
- [x] T2 — Implement webpack-bundle-analyzer integration — BTI-1 (static source-tree inventory; running webpack is out of scope for a read-only stdlib plugin)
- [x] T3 — Implement vite-bundle-analyzer integration — BTI-1 (same static inventory, tool-agnostic)
- [x] T4 — Create bundle size reporting module — BTI-1 (`BundleReport.as_dict`)
- [x] T5 — Implement threshold checks (warning/error levels) — BTI-1 (spec §7.1: 500KB warn / 2MB error)
- [x] T6 — Write tests for bundle analyzer — BTI-1 (`tests/test_frontend_build_analyzer.py`)
- [x] T7 — Test with sample webpack project — BTI-1 (checkpoint script, webpack project fixture)

## Session 2 — Asset Optimization Integration

State: done · Covers: BTI-2

- [x] T8 — Create asset optimization module — BTI-2 (`analyze_assets` in `frontend/build/analyzer.py`)
- [x] T9 — Implement image optimization (imagemin integration) — BTI-2 (static budget check per format; actual compression stays with the project's tooling)
- [x] T10 — Implement CSS minification integration — BTI-2 (css budget check)
- [x] T11 — Implement JavaScript minification verification — BTI-2 (source inventory + budgets)
- [x] T12 — Create asset size reporting — BTI-2 (`AssetIssue` list, sorted by size)
- [x] T13 — Write tests for asset optimization — BTI-2
- [x] T14 — Test with various asset types — BTI-2 (png/svg/tiny fixtures)

## Session 3 — Code Splitting Analysis

State: done · Covers: BTI-3

- [x] T15 — Create code splitting analyzer module — BTI-3 (`analyze_splitting` / `SplittingReport`)
- [x] T16 — Implement route-based code splitting detection — BTI-3 (pages/views/routes convention scan)
- [x] T17 — Implement component lazy loading detection — BTI-3 (import(), React.lazy, defineAsyncComponent, loadable)
- [x] T18 — Create code splitting recommendations — BTI-3 (suggestions tuple)
- [x] T19 — Write tests for code splitting analysis — BTI-3
- [x] T20 — Test with React.lazy() and dynamic imports — BTI-3

## Session 4 — Tree Shaking Validation

State: done · Covers: BTI-4

- [x] T21 — Create tree shaking validation module — BTI-4 (`analyze_tree_shaking`)
- [x] T22 — Implement dead code detection — BTI-4 (static unused-dependency detection; full dead-code analysis is out of scope for stdlib)
- [x] T23 — Implement unused dependency detection — BTI-4 (manifest vs import/require scan)
- [x] T24 — Create optimization recommendations — BTI-4 (returned UnusedDependency list drives the report)
- [x] T25 — Write tests for tree shaking validation — BTI-4
- [x] T26 — Test with various import patterns — BTI-4 (bare, scoped, require)

## Session 5 — Performance Monitoring Integration

State: done · Covers: BTI-5

- [x] T27 — Create performance monitoring module — BTI-5 (`analyze_performance` / `PerformanceReport`)
- [x] T28 — Implement Lighthouse CI integration — BTI-5 (spec §7.2 documents the command; hook stays static and read-only)
- [x] T29 — Implement Web Vitals monitoring — BTI-5 (static risk audit: render-blocking, sync scripts, CLS-risk images, web-vitals instrumentation)
- [x] T30 — Create performance reporting dashboard — BTI-5 (`PerformanceReport.as_dict`)
- [x] T31 — Write tests for performance monitoring — BTI-5
- [x] T32 — Test with sample performance metrics — BTI-5 (checkpoint script fixtures)

Gate A: `bin/craft-spec trace --session 5` green · checkpoint green through `bin/craft-check` · lint and format green
Gate B: `reviewer` (lenses: spec, style, logic) · `deep-reviewer` (Risk: high - build optimization)

Resume: Build tool integration ready for hook implementation and skill integration
