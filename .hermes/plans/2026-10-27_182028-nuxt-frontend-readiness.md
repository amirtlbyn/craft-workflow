# Nuxt-First Frontend Readiness Plan for craft-workflow

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make craft-workflow production-ready for frontend development, with Nuxt 4 as the first fully-supported frontend stack: first-class Nuxt detection, a `stacks/nuxt` pack, real frontend skills and standards (replacing today's dangling references), and Nuxt-shaped money/auth paths.

**Architecture:** The plugin already has the right seams — `stacks/<id>/stack.json` packs loaded by `scripts/craft_stack.py`, framework/build detection in `frontend/stacks/detection.py` and `frontend/build/detection.py`, and lens files per stack. This plan fills those seams for Nuxt instead of building new machinery. A `nuxt` stack pack (priority above `vue`) plus `nuxt` entries in both detectors make Nuxt a first-class stack; the vue/react/angular packs keep working as generic fallbacks. Skills and standards referenced by the packs are created as real files so `bin/craft-stack skills` stops pointing at nothing.

**Tech Stack:** Python 3 stdlib (detectors, no new deps), JSON stack packs, Markdown skills/lenses/standards, pytest.

**Current context (verified 2026-10-27):**
- Branch `mrz/frontend-stack`; untracked: `frontend-rewrite-plan.md`, `frontend-technical-spec.md`, `tasks/`. Preserve them.
- `bin/craft-stack detect` in a Nuxt app reports only `vue` (no `nuxt` entry anywhere in detectors).
- `stacks/vue/stack.json` references skills `component-design`, `state-management`, `styling-discipline` and standards `component_design_standards`, `frontend_performance_standards`, `accessibility_standards` — none exist on disk.
- `scripts/craft_stack.py` already merges frontend detection with stack packs (test `test_craft_stack_prefers_frontend_pack_over_node` passes); no rewiring needed.
- All 32 tests pass: `/home/amir/venv/bin/python -m pytest tests/ -q`.
- Generated mirrors (`.agents/`, `.codex/`, `.zcode-plugin/agents/`, `AGENTS.md`) must be regenerated with `bin/craft-sync-codex --write` after touching `skills/`, `commands/`, or `agents/` — never hand-edited.

---

## Phase A — Nuxt as a first-class stack (highest value)

### Task A1: Detect `nuxt` framework in `frontend/stacks/detection.py`

**Objective:** A project with `nuxt` in package.json reports framework `nuxt`, not `vue`.

**Files:**
- Modify: `frontend/stacks/detection.py` (FRAMEWORK_PACKAGES, BUILD_TOOL_FILES, priority map)
- Test: `tests/test_frontend_detection.py`

**Step 1: Write failing tests** (append to `tests/test_frontend_detection.py`)

```python
def test_nuxt_project_reports_nuxt_framework(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0", "vue": "^3.5.0"}}),
        "nuxt.config.ts": "export default defineNuxtConfig({})",
    })
    result = detect_frontend(root)
    assert [(item.framework, item.build_tools) for item in result] == [("nuxt", ())]


def test_nuxt_without_vue_dep_still_detected(tmp_path):
    root = project(tmp_path, {"package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0"}})})
    assert [item.framework for item in detect_frontend(root)] == ["nuxt"]
```

Note: Nuxt 4 apps list `nuxt` in dependencies; `vue` may or may not appear. Priority must put `nuxt` above `vue` so a Nuxt app is never misreported.

**Step 2: Run to verify failure**

Run: `/home/amir/venv/bin/python -m pytest tests/test_frontend_detection.py -q`
Expected: 2 failed (framework reports `vue`).

**Step 3: Minimal implementation** in `frontend/stacks/detection.py`

```python
FRAMEWORK_PACKAGES = {
    "react": ("react",),
    "vue": ("vue",),
    "nuxt": ("nuxt", "nuxt-nightly", "@nuxt/framework"),
    "angular": ("@angular/core",),
}
```

and extend the priority map inside `_framework`:

```python
priority = {"nuxt": 4, "angular": 3, "vue": 2, "react": 1}
```

**Step 4: Verify pass** — same pytest command, expect 6 passed in this file.

**Step 5: Commit** `feat(detect): recognize nuxt as its own frontend framework`

### Task A2: Detect `nuxt.config.*` as a build tool

**Objective:** `nuxt` appears in `build_tools` and in `frontend/build/detection.py` results.

**Files:**
- Modify: `frontend/stacks/detection.py` (BUILD_TOOL_FILES) and `frontend/build/detection.py` (CONFIG_FILES)
- Test: `tests/test_frontend_detection.py`

**Step 1: Failing test**

```python
def test_build_detection_reports_nuxt_config(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0"}}),
        "nuxt.config.ts": "export default defineNuxtConfig({})",
    })
    assert [(item.name, item.config) for item in detect_build(root)] == [("nuxt", "nuxt.config.ts")]
```

**Step 2: Verify failure** — expected FAIL (empty list).

**Step 3: Implementation**

- `frontend/build/detection.py` CONFIG_FILES: `"nuxt": ("nuxt.config.js", "nuxt.config.mjs", "nuxt.config.ts", "nuxt.config.mts")` — placed FIRST in the dict (iteration order is the reported priority; Nuxt's own bundler beats vite/webpack evidence).
- `frontend/stacks/detection.py` BUILD_TOOL_FILES: add the same tuple, also first.
- Additionally: if `"nuxt"` is in dependencies and no config file exists, still report build tool `nuxt` (Nuxt 4 works config-less). Implement in `frontend/build/detection.py::detect` after the config scan: `if "nuxt" in dependencies and not any(r.name == "nuxt" for r in results): results.append(BuildToolResult("nuxt", "", "nuxt dependency"))`. Cover with a test asserting `("nuxt", "")` for a dep-only project.

**Step 4: Verify pass** — `pytest tests/test_frontend_detection.py -q`, all green.

**Step 5: Commit** `feat(detect): detect nuxt.config and dependency-only nuxt builds`

### Task A3: Create the `stacks/nuxt` pack

**Objective:** Nuxt projects get their own stack pack: Nuxt-aware checks, paths, tests, lenses.

**Files:**
- Create: `stacks/nuxt/stack.json`
- Create: `stacks/nuxt/lenses.md`
- Test: `tests/test_frontend_detection.py` (integration-style, following `test_craft_stack_prefers_frontend_pack_over_node`)

**Step 1: Failing test**

```python
def test_craft_stack_prefers_nuxt_pack_over_vue(tmp_path):
    project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0"}}),
        "nuxt.config.ts": "export default defineNuxtConfig({})",
    })
    found = craft_stack.detect(str(tmp_path))
    assert [item["id"] for item in found] == ["nuxt"]
```

**Step 2: Verify failure** — expected FAIL (no `nuxt` pack yet; reports `vue`).

**Step 3: Create `stacks/nuxt/stack.json`** (model on `stacks/vue/stack.json`, key deltas below)

```json
{
  "id": "nuxt",
  "label": "Nuxt",
  "emoji": "🟩",
  "language": "javascript",
  "priority": 85,
  "detect": { "any_contains": [{ "files": ["package.json"], "pattern": "\"nuxt\"\\s*:" }] },
  "source_extensions": [".vue", ".ts", ".js", ".mjs"],
  "tests": {
    "globs": ["*.spec.ts", "*.test.ts", "tests/**", "__tests__/**", "e2e/**"],
    "extensions": [".vue", ".ts", ".js"],
    "id_rule": "Put the criterion ID first in the test name."
  },
  "checks": {
    "tests": [
      { "when_script": "test", "run": "{pm} test" },
      { "when_dependency": "@nuxt/test-utils", "run": "npx vitest run" },
      { "when_dependency": "vitest", "run": "npx vitest run" },
      { "run": "npm test" }
    ],
    "lint": [
      { "when_script": "lint", "run": "{pm} run lint" },
      { "when_dependency": "eslint", "run": "npx eslint ." }
    ],
    "format": [{ "when_dependency": "prettier", "run": "npx prettier --check ." }],
    "types": [{ "when_dependency": "vue-tsc", "run": "npx nuxt typecheck" }]
  },
  "paths": {
    "money": ["composables/use*cart*.ts", "composables/use*checkout*.ts", "composables/use*payment*.ts", "server/api/**/payment*", "server/api/**/billing*", "utils/money*.ts"],
    "auth": ["middleware/*auth*.ts", "server/middleware/*", "composables/use*auth*.ts", "utils/token*.ts", "server/api/**/auth/**"],
    "migrations": ["server/database/migrations/**", "drizzle/**", "prisma/migrations/**"],
    "models": ["server/database/**/*.ts", "types/**/*.ts", "prisma/schema.prisma"],
    "views": ["app/**/*.vue", "pages/**/*.vue", "components/**/*.vue", "layouts/**/*.vue"]
  },
  "skills": ["component-design", "state-management", "styling-discipline", "nuxt-ssr-data"],
  "standards": ["component_design_standards", "frontend_performance_standards", "accessibility_standards"],
  "lenses": "stacks/nuxt/lenses.md"
}
```

Path-glob rationale: in Nuxt 4 the money/auth surface lives in `composables/` and `server/api|middleware`, not `*/migrations/*` — fix the backend-shaped globs the vue pack inherited. Verify `bin/craft-stack globs money` from a Nuxt fixture lists the composables globs.

**Create `stacks/nuxt/lenses.md`** (expand from vue's two short lenses; these are the reviewer's Nuxt-specific checklist):

```markdown
## SSR Safety Lens
- No `window`/`document` access outside `onMounted`, a client plugin, or `.client.ts`.
- State shared across requests lives in `useState`, never module-level `ref`s.
- Components that break SSR are wrapped in `<ClientOnly>` with a fallback.

## Data Fetching Lens
- Page data uses `useFetch`/`useAsyncData` with a stable key; no bare `onMounted` fetching that gates first paint.
- Duplicate keys across sibling calls are avoided; payloads are awaited at setup, not chained after mount.

## Route & Hydration Lens
- Dynamic routes declare their params; middleware redirects are SSR-aware.
- Hydration mismatches: no `Date.now()`/`Math.random()` in rendered output.

## Component Lens
- Composition API state is local unless sharing is justified.
- Derived values use `computed`; watchers are reserved for side effects.
- Props and emits are typed, documented, and validated.

## Accessibility Lens
- Templates use semantic elements, labels, visible focus, and keyboard support.
- Dynamic announcements and dialogs expose an appropriate accessible name.
```

**Step 4: Verify** — pytest green, plus end-to-end in a fixture:

```bash
cd /tmp && rm -rf nuxt-fix && mkdir nuxt-fix && cd nuxt-fix
printf '{"dependencies":{"nuxt":"^4.0.0"}}' > package.json
printf 'export default defineNuxtConfig({})' > nuxt.config.ts
/home/amir/projects/gitrepo/future-ideas/craft-workflow/bin/craft-stack detect --json   # expect primary "nuxt"
/home/amir/projects/gitrepo/future-ideas/craft-workflow/bin/craft-stack checks         # expect nuxt checks
/home/amir/projects/gitrepo/future-ideas/craft-workflow/bin/craft-stack lens ssr --paths .   # expect the SSR Safety Lens text
```

**Step 5: Commit** `feat(stacks): add nuxt stack pack with ssr/data-fetching lenses`

### Task A4: Tighten the vue pack to be a fallback, not a Nuxt alias

**Objective:** Vue pack no longer claims Nuxt-shaped paths; detection preference makes `nuxt` win when both apply.

**Files:**
- Modify: `stacks/vue/stack.json` (priority 80 → 75 is unnecessary — nuxt's 85 already wins; only fix `paths` and `checks.types`)

**Steps:**
1. In `stacks/vue/stack.json`: replace backend-shaped globs — remove `"*/migrations/*"` from `paths.migrations`, remove `"balance*.py"` from `paths.money`, add `.vue`-shaped money/auth globs (`composables/use*payment*.ts`, `stores/*auth*.ts`, `*/payment*/*.vue`).
2. Change vue `checks.types` first entry to `{ "when_file": "tsconfig.json", "run": "npx vue-tsc --noEmit" }` only when `vue-tsc` is a dependency: `{ "when_dependency": "vue-tsc", "run": "npx vue-tsc --noEmit" }` (a plain `tsconfig.json` Nuxt-less Vue project may not have vue-tsc).
3. Verify: `bin/craft-stack detect --json` in a vue-only fixture still returns `vue`; in the nuxt fixture returns `nuxt`.
4. Commit: `fix(stacks): vue pack globs and typecheck for real Vue projects`

### Task A5: Register Nuxt ignore dirs and selftest fixtures

**Files:**
- Modify: `scripts/craft_stack.py:57` (already ignores `.nuxt` — add `.output`, `dist` if missing)
- Test: `tests/` selftest touchpoint — run `scripts/stack_selftest.py` if it enumerates packs.

**Steps:**
1. `grep -n '\.output\|\.nuxt' scripts/craft_stack.py` — add `.output` (Nuxt 4 build dir) to the ignore list next to `.nuxt`.
2. Add a nuxt fixture case to any selftest that enumerates stacks (`scripts/stack_selftest.py`, `scripts/craft_selftest.py` — check with grep for `stacks/vue`).
3. Verify: `/home/amir/venv/bin/python scripts/stack_selftest.py` and full pytest green.
4. Commit: `chore(stacks): ignore .output and cover nuxt in selftest`

---

## Phase B — Make the referenced skills and standards real

Order: standards first (A-packs reference them by name), then skills, then regenerate mirrors once at the end.

### Task B1: Frontend standards files

**Objective:** `bin/craft-stack skills`/review flows resolve the standards the packs name.

**Files:**
- Create: `standards/component_design_standards.ai.md`
- Create: `standards/frontend_performance_standards.ai.md`
- Create: `standards/accessibility_standards.ai.md`
- Check first: `standards/SOURCE.lock` and `standards/README.md` — follow the vendoring convention; if standards are vendored from upstream with lock hashes, register the new files the way existing entries are registered.

**Steps:**
1. Read `standards/node_standards.ai.md` and `standards/README.md` to copy the house format (sections, length, tone).
2. Author each file (~80–150 lines): component design (props/emits contracts, composition, slots, typed generics for Nuxt auto-imported components), performance (hydration cost, lazy components, payload size, image/font discipline, prefetch rules), accessibility (WCAG AA basics, focus management, dialogs, forms, contrast, keyboard traps).
3. Verify: `bin/craft-std list` (or whatever `bin/craft-std` exposes — check `bin/craft-std --help`) lists the new files.
4. Commit: `feat(standards): component design, performance, accessibility standards`

### Task B2: The three referenced skills as plugin skills

**Objective:** `bin/craft-stack skills` output resolves to loadable skills.

**Files:**
- Create: `skills/component-design/SKILL.md`
- Create: `skills/state-management/SKILL.md`
- Create: `skills/styling-discipline/SKILL.md`
- Create: `skills/nuxt-ssr-data/SKILL.md` (new — Nuxt-specific, referenced by the nuxt pack)

**Steps:**
1. Read an existing short skill (`skills/minimal-code/SKILL.md`, `skills/node-practices/SKILL.md`) for frontmatter format (`name`, `description`, house style).
2. Author each SKILL.md (concise, checklist-driven; Nuxt 4 specifics in `nuxt-ssr-data`): 
   - `component-design`: props down / emits up, single responsibility, auto-imported components naming, typed `defineProps`/`defineEmits`, slot design.
   - `state-management`: `useState` keys, Pinia for cross-cutting store, server state vs client state, avoid module-scope shared refs (SSR leak).
   - `styling-discipline`: one styling approach per repo (utility CSS or scoped), design tokens, no inline layout hacks, responsive breakpoints convention.
   - `nuxt-ssr-data`: `useFetch`/`useAsyncData` keys, `useLazyFetch` tradeoffs, `refreshNuxtData`, ClientOnly boundaries, payload serialization limits.
3. **Regenerate mirrors:** `bin/craft-sync-codex --write` (never hand-edit `.agents/`, `.codex/`, `.zcode-plugin/agents/`, `AGENTS.md`).
4. Verify: from the nuxt fixture, `bin/craft-stack skills` prints the four names and each exists as `skills/<name>/SKILL.md`; `bin/craft-sync-codex` (no flag) reports no drift.
5. Commit: `feat(skills): component, state, styling, and nuxt-ssr-data skills`

### Task B3: Stop printing nonexistent skills/standards

**Objective:** `skills_for` never recommends a skill that does not exist on disk — turn today's silent dangling references into a guard.

**Files:**
- Modify: `scripts/craft_stack.py:309` (`skills_for`) — filter names to those with an existing `skills/<name>/SKILL.md`; emit a warning line (or an `unknown` list in `--json`) for the rest.
- Test: `tests/test_frontend_detection.py` or a new `tests/test_craft_stack_skills.py`

**Step 1: Failing test**

```python
def test_skills_for_drops_missing_skill_dirs(tmp_path, monkeypatch):
    import craft_stack
    monkeypatch.setattr(craft_stack, "detect", lambda cwd=None: [{"id": "nuxt", "dir": "", "evidence": "x"}])
    skills = craft_stack.skills_for(cwd=str(tmp_path), with_concurrency=False)
    assert "nonexistent-skill" not in skills
```

(Make the nuxt pack's skill list contain one real name; assert only existing dirs survive.)

**Step 2: Verify failure, implement filter, verify pass.**

**Step 3: Commit:** `fix(craft-stack): only recommend skills that exist`

---

## Phase C — Review depth and gates (from the spec's phases 2–4)

Ship in this order; each is independently useful. These can land after A+B — the workflow is already Nuxt-usable once A and B are done.

### Task C1: Wire the nuxt/vue lens files into the reviewer path
- Verify `bin/craft-stack lens <name>` resolves each lens section in `stacks/nuxt/lenses.md` from a Nuxt path (ssr, data, hydration, component, accessibility). Fix the lens-name mapping in `scripts/craft_stack.py` if sections don't resolve (check how `cmd_lens` parses `##` headers).
- Extend `agents/` reviewer prompt (and regenerate mirrors) to read the stack lens next to the generic lens — follow the existing instruction text in `agents/` for the django/php packs.
- Commit: `feat(review): stack lenses reach the reviewer agents`

### Task C2: Frontend Gate A proof commands in `bin/craft-check`
- Confirm `bin/craft-check -- npx vitest run` records a pass in a fixture project with a trivial vitest test. If `craft-check` assumes a single stack's commands, verify it honors `--stack nuxt`.
- Add an eval fixture: `evals/nuxt-simple/` with a minimal package.json + one passing test, mirroring existing eval dirs.
- Commit: `test(evals): nuxt fixture proves Gate A checks`

### Task C3: Accessibility + bundle gates (spec Phase 4) — defer unless needed
- `hooks/`-enforced a11y/bundle gates are the last mile and need an axe-core/lighthouse runner decision. Recommend: start as *checks* entries (conditional on dependencies `@axe-core/playwright`, `@nuxtjs/lighthouse` etc. via `when_dependency`) rather than new hooks. Revisit after A–C2 ship.

---

## Validation (whole plan)

1. Unit: `/home/amir/venv/bin/python -m pytest tests/ -q` — all pass (32 baseline + new).
2. Selftests: `python3 scripts/stack_selftest.py` (and `craft_selftest.py`) green.
3. Fixture end-to-end in `/tmp/nuxt-fix`:
   - `bin/craft-stack detect --json` → primary `nuxt`
   - `bin/craft-stack checks` → vitest/eslint/prettier/nuxt typecheck
   - `bin/craft-stack skills` → 4 skills, all existing on disk
   - `bin/craft-stack lens ssr --paths .` → SSR Safety Lens body
   - `bin/craft-stack globs money` → composables/server-api globs
4. Drift: `bin/craft-sync-codex` (no flag) → no drift.
5. Vue fallback: fixture with only `vue` dep → `vue` pack, fixed globs.

## Risks / tradeoffs / open questions

- **standards/SOURCE.lock convention**: if standards are vendored with lock hashes, B1 must follow that process; check before authoring.
- **`bin/craft-stack skills` exists-check location**: skills live in `skills/` at plugin root; `craft_stack.py` may run from an installed plugin — resolve skill paths relative to the repo root the same way `lenses` keys do (`stacks/vue/lenses.md` pattern).
- **Priority collisions**: `nuxt` priority 85 beats `vue` 80; keep react/angular unchanged. Angular+Nuxt hybrids are pathological — priority map already orders them deterministically.
- **Scope control**: Phases C3+ (bundle/a11y hooks) are deliberately deferred; A+B alone make Nuxt projects fully workflow-supported.
- **Generated mirrors**: every `skills/`, `agents/`, `commands/` change requires `bin/craft-sync-codex --write` — batch it once per task that touches sources.
