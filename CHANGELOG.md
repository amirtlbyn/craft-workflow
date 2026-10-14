# Changelog

## 0.9.0 — 2026-10-14 — PHP: Laravel, Symfony, and plain PHP

### What changed for the developer

- **Three new stacks.** `bin/craft-stack` detects 🟥 Laravel (`artisan`, or
  `laravel/framework`), 🎼 Symfony (`symfony/framework-bundle`), and 🐘 PHP (any
  `composer.json`). Laravel and Symfony win over plain PHP in the same
  directory. A monorepo gets one stack per service, as before.
- **Checks come from `composer.json`.** Tests run `composer test` when the
  project has a `test` script, else `vendor/bin/pest` with Pest, else
  `php artisan test` on Laravel, else `vendor/bin/phpunit`. Types run PHPStan
  (or Larastan on Laravel), else Psalm. Format runs Pint on Laravel, else
  PHP-CS-Fixer. Each check runs only when its tool is a dependency, and
  `bin/craft-check` records them.
- **Trace forms.** `bin/craft-spec trace` finds a criterion ID in a Pest
  `it('PAY-3: ...')` title, in `#[TestDox('PAY-3: ...')]`, and in a `//` comment
  directly above a PHPUnit method.
- **The scenario gate covers PHP tests.** `tests/`, `*/tests/`, and `*Test.php`
  count as test files: they stay closed until you approve the scenarios.
- **Paths.** Money, auth, migration, model, and controller globs for PHP raise
  risk and route lenses, for example a `Voter`, a `Policy`, or `database/migrations/`.
- **Concurrency verdicts.** PHP-FPM runs one process per request: `limited`.
  Octane, RoadRunner, Swoole, and FrankenPHP keep workers alive between
  requests: `limited`, with a warning about state that leaks between requests.
  ReactPHP and Amp run an event loop: `ready`. There is no PHP concurrency skill.
- **Toolchain.** `bin/craft-toolchain` checks `php`, `composer`, and PHPStan.
- **New skill `php-practices`** and **new standard `php_standards.ai.md`**
  (bot-maintainable until a team renames it to `.human.md`). Lens notes for
  each stack are in `stacks/<id>/lenses.md`.

### What did not change

- Django, FastAPI, Go, Java, and Node behave as in 0.8.0.
- The routes, the two approvals, and the gates are the same. No PHP tool is
  required to use the other stacks.

## 0.8.0 — 2026-10-14 — the scenario gate returns

### What changed for the developer

- **Two approvals on `task` and `project`.** You approve the spec. Then Claude
  drafts the test scenarios, one or more `Given ..., when ..., then ...` lines
  per criterion, including the failure story. Claude shows them grouped by
  criterion and stops. You approve, and only then can Claude write test files.
  Source files open with the spec approval, as before.
- **The approval is bound to content.** It records the SHA-256 of `scenarios.md`
  and of `spec.md`. A change to either file makes the scenarios stale, and test
  files close again.
- **You can edit on the board.** The Scenarios tab (key 3, after Tasks) keeps
  one selected row (`j`/`k`). `e` edits it, `i` adds a scenario to its
  criterion, `x` deletes it after a confirm, and `a` approves after a confirm.
  Only one text field shows at a time, and an empty Enter closes it.
- **The board scrolls sideways.** `h` and `l` (or `◀` `▶`) shift long row text
  on every tab. The IDs and glyphs stay in place. The viewer shows `scenarios.md` with `n`. The status line shows an
  `S` glyph next to `A` and `B`.
- **A denied test write explains itself.** The reason names the state, the
  `craft-scenarios draft` step, and each criterion without a scenario.

### Why it returns

0.3.0 removed the separate scenario gate. It folded the test list into the
spec, so one approval covered the criteria and the tests. That did not let you
see the concrete cases before a test existed. A criterion says what must hold.
A scenario says which input, which state, and which result. You want to read
and change those cases first. One approval of the criteria did not give you that.
The gate returns, narrower: it covers test files only.

0.3.0 removed the scenario gate to cut cost and to have one approval instead of
two. 0.8.0 accepts one more approval per task. The board's Scenarios tab and
the status-line `S` keep that cost to one screen and one key.

### New

- `bin/craft-scenarios status|draft|add|set|remove`.
- `bin/craft-approve --scenarios`. It refuses while a criterion has no scenario,
  and while the spec has no criterion.
- `skills/spec/templates/scenarios.md`. `craft-spec new` copies it.
- `scenarios.md` in the spec directory, and `kind: scenarios` approvals in
  `approval.json`.

### Known limits

- The gate watches the file tools. A `Bash` command can still write a test file.
- Test files are found by glob. A test path the globs miss is not gated. A
  source file that matches a test glob is gated.
- `.claude/craft/stack.json` is agent-writable and changes which files count as
  tests. The hook cannot tell who approved. It trusts `bin/craft-approve`.
- These risks are accepted in the design of the spec
  `2026-10-12-test-scenarios-drafted-criterion-edited-board`.
- Only the skill rule and `log.md` stop Claude from running
  `craft-approve --scenarios` itself. The board's confirm is the developer's
  own path.
- A hook that cannot read an existing `scenarios.md` allows the write.

## 0.7.0 — 2026-10-10 — every backend stack, the concurrency gate, AI deciders, and a mod

### 🧩 Stack packs: one workflow, any backend language

- **`stacks/<id>/stack.json`** for 🐍 `django` (the reference, unchanged), ⚡
  `fastapi`, 🐹 `go`, ☕ `java` (Spring, Maven or Gradle, Kotlin too), and 🟩
  `node` (TypeScript, Express, Fastify, NestJS). A pack says how to detect the
  stack, where its tests are and how a test names a criterion, its Gate A
  commands, its path globs for money, auth, migrations, models, and entry
  points, its skills, its standard, and its lens notes.
- **`bin/craft-stack`** detects the stacks at the root and two levels below, so
  a monorepo gets one stack per service. `checks`, `skills`, `concurrency`,
  `lens`, `globs`, `for`, `set`, `unset`, `list`. `CRAFT_STACK=go` overrides.
- **`bin/craft-spec trace` is language-neutral.** It finds criterion IDs in
  Python docstrings, Go comments and `t.Run` names, Java `@DisplayName`, Kotlin
  backtick names, and TypeScript test titles. It writes `.claude/craft/trace.json`.
- **`bin/craft-check`** reads every runner's own summary (pytest, go test,
  gotestsum, Maven, Jest, Vitest, `node --test`, mocha, ruff, ESLint,
  golangci-lint, tsc, the race detector) and records it with the check.
  `--junit PATH|auto` reads JUnit XML and names the failing tests.
- **`bin/craft-toolchain`** checks and installs each stack's tools (`go install`
  for Go tools). Django keeps `config/toolchain.json`.
- **The rules floor** of `bin/craft-jev` uses every detected stack's globs, so
  a Go wallet handler or a Spring `SecurityConfig` raises risk the way a Django
  `permissions.py` does.
- New skills: `fastapi-practices`, `go-practices`, `java-practices`,
  `node-practices`. New standards: `fastapi_standards.ai.md`,
  `go_standards.ai.md`, `java_standards.ai.md`, `node_standards.ai.md`
  (bot-maintainable until a team renames one to `.human.md`). Lens notes per
  stack in `stacks/<id>/lenses.md`, printed by `bin/craft-stack lens`.
- `config/workflow.md`: §1 per-stack standards, §2 a change of concurrency model
  forces `project`, §3 the `concurrency` lens and stack notes, §5 the new
  skills, §6 per-stack commands, and a new §9 Stacks.

### 🧵 The concurrency readiness gate

- **New skill `concurrency`.** It separates concurrency for correctness (always
  required) from concurrency for throughput (gated). `bin/craft-stack
  concurrency` reads the model a system runs and gives a verdict: `ready`,
  `limited`, or `not-ready`, with evidence, an allowed list, and an avoid
  list. A `not-ready` system gets no async, threads, or worker pools on any
  route but `project`.
- **New skill `fastapi-async`**, with `references/patterns.md` and
  `references/testing.md`: the event-loop rule, one client per lifespan, one
  `AsyncSession` per task, bounded fan-out with `TaskGroup` and a Semaphore,
  timeouts and cancellation, `run_in_threadpool`, owned background tasks, and
  tests that prove the bound and the timeout.
- **New skill `go-concurrency`**, with `references/patterns.md` and
  `references/testing.md`: the four questions for every `go` statement,
  `errgroup.SetLimit`, worker pools, semaphores, rate limits, leak-free
  timeouts, pipelines, graceful shutdown, the database as the guard of money,
  `-race`, `goleak`, and `testing/synctest`. The patterns compile, pass
  `go vet`, and pass `go test -race`.
- **New lens `concurrency`** (ceiling High), routed when the diff adds
  concurrent code in any stack. `/concurrency`, `/stack`: new commands.

### 🧠 Deciders: Jev, free tiers, local models, Claude Haiku

- **`scripts/deciders.py` and `config/deciders.json`.** Jev is one provider.
  The others are OpenAI-compatible chat models asked for strict JSON in Jev's
  answer shape: OpenRouter's free router, Groq, Gemini, Cerebras, Mistral,
  GitHub Models, Cloudflare Workers AI, Ollama and LM Studio locally, and
  Claude Haiku through `claude -p --safe-mode` on your own plan.
- **Two modes.** `first`: the first provider that answers. `council`: ask
  several in parallel and average their probabilities; a split council comes
  out undecided, and Claude decides, never below the floor.
- **Privacy per provider.** `send_request_text: false` (the default for free
  tiers that may keep prompts) keeps the request text local. Secrets are
  redacted. File contents never go. Only `https://`, or `http://` to this machine.
- **`bin/craft-decide`**: `status`, `on`, `off`, `use`, `council`, `mode`,
  `approve-with`, `set`, `unset`, `reset`, `test`, `discover`. `/decide`.
- `bin/craft-jev decide` and the `jev_approve` hook ask the chosen deciders.
  With the default config (`order: ["jev"]`) they behave as in 0.6. Approval of
  tool calls uses only `approve_providers`, default `jev`.

### 🎛️ The craft mod (Claude Code 2.1.287+)

- **`hooks/mod.json` → `hooks/mod/craft.tsx`**, named by the manifest's
  `hooks` field, so ZCode keeps reading only `hooks/hooks.json`. The Python
  hooks stay the enforcement everywhere.
- **The status at the top**: the 🗂 craft board's header, docked at the top
  right of a wide fullscreen terminal: route, stack, risk, the concurrency
  verdict, the spec state, every Gate A check, Gate B, 💰 cost, the 5-hour
  limit, and context. Where the board has no room, the same status is a band
  above the prompt. `userConfig` `status`: `top`, `prompt`, or `both`.
- **The board**: 📋 Spec (criteria with their tests, approve, re-trace, read
  `spec.md`), ✅ Tasks, 🚦 Gates, 🔍 Review (confirm or reject a finding), 💰
  Cost, 🧠 Deciders (the last decision, each member's vote, mode toggle, ping).
- **💰 Cost per agent**: every model request, main loop and subagents, priced
  with `config/prices.json`, per spec, kept across sessions, with the engine's
  own ledger beside it.
- **Zero-token commands**: `/craft-board`, `/craft-status`, `/craft-cost`,
  `/craft-gates`, `/craft-trace`. They answer at once, with no Claude turn.
- **The spec gate as a question**: when Claude tries to write code before the
  spec is approved, you get open the spec, approve it, or keep it blocked. The
  approval is a key you press, not a command Claude runs.
- **`auto_check`** (off by default) sends test commands through `craft-check`.
- `claude plugin validate .` passes, `tsc` is clean, and `claude plugin test`
  runs 11 tests over the terminal and desktop surfaces.

### Machinery

- `bin/craft-ui-state`: one JSON snapshot for the mod, about 70 ms.
- `bin/craft-session record-finding`, `finding`, `record-review`: findings and
  review rounds as state, so Gate B is visible. `adjudication.md` says when.
- `craft-doctor`: new `stacks`, `mod`, and `deciders` groups.
- `scripts/stack_selftest.py`: 105 cases, in CI beside the 269 of
  `craft_selftest.py`.
- The `SessionStart` status names the stack and its concurrency verdict.

Not verified here: a live call to any hosted decider (the sandbox has no
network to them; the client ran against a local mock and Claude Haiku ran for
real), and the interactive terminal drawing (the kit tests the trees; run
`claude --plugin-dir .` once to see them).

## 0.6.0 — 2026-09-28 — minimal-code discipline

- **New skill `minimal-code`.** A "laziness ladder" that runs before new code:
  does it need to exist, is it in the codebase, does the stdlib, the framework,
  or an installed dependency do it, can it be one line, and only then build the
  minimum. It never removes authorization, money, transaction, or
  state-machine code, and it never trades performance for fewer lines: indexes,
  bulk paths, bounds, retries, and lock scope are exempt. The idea comes from
  the `ponytail` plugin, which suits small projects; the skill is our own
  version for a large system under load, with no external dependency.
- **`/minimal-audit`** scans code for over-engineering and proposes removals.
  **`/minimal-gain`** measures a change from the real diff. It reports no
  "percent saved" figure, because that needs a baseline we do not have.
- Wired into `config/workflow.md` §5, the `craft` task route, the `coder`
  agent, the README, and the `style` review lens (structure item 5).

## 0.5.1 — 2026-09-26 — negation-aware Stop hook, less strict Jev approval

- **`verify_gates` ignores negated claims.** The Stop hook blocked messages
  such as "Gate A has not passed" and "It is not `done` until Gate B is green".
  Now a match counts only when its clause has no negation word (`not`, `no`,
  `until`, `blocked`, `failed`, and others). A clause ends at `. ! ? ; : ,` or a
  new line. The hook still fails open on any error.
- **Jev approval is less strict on safe calls.** In a real session, read-only
  commands (`git status`, `git diff origin/...`, `craft-std`, `craft-spec`) got
  verdict `allow` at 0.97 to 0.99, but `sends_data_out` at 0.40 to 0.51, so
  they were not approved. The `sends_data_out` and `irreversible` questions had
  no criteria. They have criteria now. The `allow` criterion now also covers the
  session's own scratch files, `docker ps`, `logs`, and `inspect`, tests in a
  local container, and the workflow's read-only commands. `python3 - <<'EOF'`
  and the same form for `node`, `perl`, `ruby`, and `php` are now always asked.
  The thresholds did not change.
- The latency claim was wrong. Eligible calls wait about 0.7 to 1.3 seconds in
  practice, not 0.2 to 0.5 seconds.
- Self-test: new cases for negated claims and for `python3 - <<'EOF'`.

## 0.5.0 — 2026-09-26 — Jev endpoint overrides and tool-call approval

- **`craft-jev set endpoint <url>` and `set model <id>`**, with `unset`. The
  override lives in the repository's `.claude/craft/jev.json`, so a plugin
  update does not reset it. `CRAFT_JEV_URL` and `CRAFT_JEV_MODEL` still win.
  `status` shows each value and its source. Only `https://` endpoints are
  accepted. A chosen endpoint is used alone. The fallback applies only to the
  default.
- **`/jev approve on | off`** and the `jev_approve` `PreToolUse` hook. With Jev
  on and approval on, routine tool calls that would prompt are approved when Jev
  says `allow` at confidence 0.9 and both risk questions are below 0.3. Deny and
  always-ask lists in `config/jev.json` come first and need no model. The hook
  is silent in `bypassPermissions` and `plan` mode, and whenever another craft
  hook would deny. Secrets are redacted before sending. Decisions go to
  `.claude/craft/jev-approvals.jsonl`.
- `scripts/jev_client.py` holds the OpenRouter client that `bin/craft-jev` and
  the hook share.
- Self-test: 258 cases, including the approval hook against the mock server.

Not verified: a live call, and how Claude Code's own `deny` rules in settings
interact with a hook `allow`. Keep important deny rules in both places.

## 0.4.0 — 2026-09-24 — optional Jev decisions

- **`/jev on | off | status | test`** and the `jev` skill. Jev is TypeSafe's
  System One decision model (`typesafe/jev-1.13`), reached through OpenRouter's
  Decisions API at `https://openrouter.ai/api/alpha/decisions`. It is off by
  default and per repository. `CRAFT_JEV=on|off` overrides the switch.
- **`bin/craft-jev decide --stage route|review`** asks the questions in
  `config/jev.json`: route, risk tier, implementer model, skills to load, and
  review lenses. Jev cannot call tools. It returns typed answers, and Claude acts.
- **A rules floor** from `config/paths.json` globs and request keywords. Jev can
  raise a decision above it, never lower it. The `money`, `auth`, `migrations`,
  `models`, and `views` glob sets now have a reader.
- **Fail open.** A missing key, a timeout, or an HTTP error gives a rules-only
  decision. One retry with backoff on 429, 5xx, and timeouts. A 404 tries the
  fallback endpoint in `config/jev.json`.
- **Privacy.** Only the request text, paths, and line counts are sent. Never file
  contents. `--no-request-text` sends only paths. `provider.data_collection` is
  `deny`. The key is read from `OPENROUTER_API_KEY` or
  `~/.config/craft-workflow/openrouter.key` and never written.
- `.claude/craft/jev-log.jsonl` records every decision without the request text.
- The self-test runs `craft-jev` against a local mock of the Decisions API:
  retry, fallback, timeout, the floor, and the privacy rules.

Not verified: a live call. The development sandbox cannot reach OpenRouter.
Run `/jev test` once with your key.

## 0.3.0 — 2026-09-23 — spec-driven, and cheaper to run

The workflow changes from goal-driven to spec-driven. The gates stay. They are
now derived from an approved spec, not defined at the end of the work. The
second aim of this release is cost: a `/task` used to start eleven agents, four
of them on Opus, and developers hit the usage limit in the middle of the work.

### What changed for the developer

- **The spec comes first.** `task` and `project` start with
  `.claude/specs/<date>-<slug>/spec.md`: problem, non-goals, EARS acceptance
  criteria, invariants, contracts, validation decisions, standards that apply,
  and a risk tier. `/spec` writes it. `bin/craft-spec new` scaffolds it.
- **One approval, not two.** The acceptance criteria are the test scenarios.
  `/test-scenarios` and `TEST_SCENARIOS.md` are gone. A criterion the developer
  adds is still REQUIRED and marked `[developer]`.
- **The approval is bound to the spec's SHA-256, not to the Claude session.**
  A changed spec closes the gate until the developer approves the delta. A new
  session after a usage-limit reset needs no second approval.
- **The spec gate covers all source, not only tests.** Before approval, on
  `task` and `project`, only files under `.claude/` can be written.
- **Traceability.** Each criterion gets exactly one test, with its ID first in
  the docstring. `bin/craft-spec trace` maps criteria to tests. Gate A needs it
  green, and the `Stop` hook checks it.
- **Spec deltas.** When the code shows the spec is wrong, the workflow stops and
  proposes the rows to change. It never builds unapproved behavior.
- `.claude/plans/` becomes `.claude/specs/`. `PLAN.md` becomes `design.md` and
  the sessions in `tasks.md`. `PROGRESS.md` and `REVIEW.md` merge into the
  append-only `log.md`.

### What changed in the machinery

| Before (0.2.2) | After (0.3.0) |
|---|---|
| `coder` spawned on every `task` | `task` implements in the main session. `coder` runs per session on `project` only, and reads the spec instead of re-exploring |
| Four reviewers, two on Opus, every `task` | One `reviewer` (Sonnet) applies the routed lenses in one pass. `deep-reviewer` (Opus) runs only on `Risk: high`, for `logic` and `security` |
| `/fix-review` re-ran every reviewer on the whole diff | Re-review runs only after a confirmed Critical or High, only that reviewer, only on the fix delta |
| `style-reviewer` (Haiku) read 55 KB of standards, and checked formatting the linters already check | The `style` lens covers what linters cannot: naming, English, docstrings, idiom. It reads sections on demand |
| Agents read whole standards: 12–26 KB each | `bin/craft-std <file> <section>` prints one section. `bin/craft-std --list` is the 6 KB index |
| `asd-ste100` (18 KB) loaded before every comment | `skills/asd-ste100/references/card.md`, one page. The full skill is for long documents |
| `quick` ran `style-reviewer` | `quick` spawns nothing. The linters and one self-read against the `style` lens |
| Adjudication re-opened every finding | Every Critical and High is verified. Medium and Low are verified when the line is not already in context |
| `pytest -v` output went straight into the context | `bin/craft-check` records the real exit code, prints the summary or the failures, and keeps the full log in `.claude/craft/logs/` |
| Nothing recorded a check automatically | `bin/craft-check` records every check it runs. `bin/craft-session record-check` stays as a manual fallback |
| A new session re-explored the repository | The `SessionStart` hook prints the active spec, its state, and the next task |

### The cost model behind the numbers in the README

Instruction bytes each agent loads at the start of one `/task` with one fix
round, plus 40 KB for each agent that re-reads the repository. Tokens are bytes
divided by 4. The quota weight assumes Haiku 0.33, Sonnet 1, Opus 5.

**0.2.2** — main session 75 KB; `coder` 142 KB, twice; `style-reviewer` (Haiku)
107 KB, twice; `logic-reviewer` (Opus) 73 KB, twice; `security-reviewer` (Opus)
52 KB, twice; `query-reviewer` 55 KB, twice. Total 933 KB, about 233k tokens,
448k quota-weighted, 11 agents.

**0.3.0, `Risk: low`** — main session 89 KB, `reviewer` with all lenses 65 KB,
delta re-review 35 KB. Total 189 KB, about 47k tokens, 47k quota-weighted.

**0.3.0, `Risk: high`** — main session 89 KB, `reviewer` 60 KB, `deep-reviewer`
(Opus) 56 KB, delta re-review by `deep-reviewer` 26 KB. Total 231 KB, about 58k
tokens, 139k quota-weighted.

The model ignores every turn after the first, so it understates real usage in
both versions. It is a comparison, not a forecast. The way to measure real
usage is the same real task, run once on each version.

### Defects fixed from the 0.2.0 hardening notes

- **D1** — the reviewer-memory path is `aidocs/reviewer-memory.md` everywhere.
- **D2** — the `logic` lens reads the "Django logic and style" section when it
  judges transactions. Scope isolation no longer depends on hiding documents.
- **D3** — every lens states what it reads.
- **D5** — `plugin.json`, `marketplace.json`, and `.zcode-plugin/plugin.json`
  carry the same description.
- Roadmap item "context surgery" is done without editing a `*.human.md` file:
  `bin/craft-std` slices the standards at read time.
- Roadmap item "the toolchain skill is not routed": `config/workflow.md` §5 now
  routes it.
- Hook gap "nothing starts a session" and "nothing records a check": closed by
  `bin/craft-spec new` and `bin/craft-check`.
- The `PreToolUse` matcher was `Write|Edit`, so `MultiEdit` and `NotebookEdit`
  bypassed `protect_human_owned`. The matcher now names all four.
- `bin/craft-doctor` now checks `agents/coder.md`, every routed lens file, the
  `bin/` commands, and `.claude/specs/ACTIVE`.

### Upgrading from 0.2

1. Pull, then run `bin/craft-doctor --skip commands`. It should report no FAIL.
2. A plan in progress under `.claude/plans/` still works as prose: `/progress`
   reads a legacy `ACTIVE` plan. New work goes through `/spec`.
3. An old `session.json` on route `task` or `project` with no spec now shuts
   the gate for every source file. Run `bin/craft-session end`, or start a spec
   with `bin/craft-spec new`.
4. Codex and ZCode users: the mirrors are regenerated. Re-run the symlink loop
   in the README, because agents were renamed.
5. Run the eval suite once, at a time your usage limit allows it. The run of
   2026-09-18 stopped at the session limit after two cases, so it measured
   nothing.

### Known limits

- The spec gate watches the file tools. A `Bash` command that writes a file is
  not gated. The same was true of the old scenario gate.
- `bin/craft-approve` records an approval the model runs. The hook cannot tell
  whether the developer really said approve. The skill forbids recording an
  approval the developer did not give, and `log.md` keeps the record.
- A green checkpoint recorded before the last code change still counts for
  Gate A. Run the checkpoint again after the last fix.
- Two Claude sessions in one repository share one `session.json`.

## 0.2.2 and earlier

The hardening pass of 0.2.0 added: the three hooks, the
state library, the health check, the toolchain installer, and the eval suite.
