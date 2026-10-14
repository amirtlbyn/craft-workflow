# craft-workflow

A spec-driven, cost-routed engineering workflow for Claude Code, packaged as a
plugin, for any backend stack: 🐍 Django, ⚡ FastAPI, 🐹 Go, ☕ Java, 🟩 Node, 🐘 PHP (🟥 Laravel, 🎼 Symfony).

It answers four questions on every request: **how much process does this
deserve**, **what exactly are we building**, **what code should not be written
at all**, and **who checks it, at what cost**.

---

## What it gives you

**Three cost routes.** Not every change deserves a spec and a reviewer. `quick`
fixes a typo inline and spawns nothing. `task` handles one merge request. `project`
adds a design and splits the work into sessions. The router picks, says why in
one line, and only ever promotes.

**A spec as the source of truth.** On `task` and `project`, the first artifact
is `spec.md`: the problem, the non-goals, acceptance criteria in EARS form
(`WHEN ..., THE ... SHALL ...`), the invariants, the contracts, and a risk tier.
The developer approves it once. Each criterion gets exactly one test that names
its ID, so `bin/craft-spec trace` can prove the mapping. The spec replaces the
old separate test-scenario list. Since 0.8.0 the developer also approves the
concrete scenarios of each criterion before any test is written (see below).

**A spec gate that is a hook, not a request.** Until the spec is approved, no
source or test file can be written on `task` or `project`. The approval is
bound to the SHA-256 of `spec.md`. Change the spec and the gate shuts again
until the developer approves the delta. The approval is not bound to a Claude
session, so work resumes after a usage-limit reset without a second approval.

**A scenario gate for test files.** After the spec approval, source files are
open. Test files stay closed until the developer approves `scenarios.md`: one
`Given ..., when ..., then ...` line per scenario, grouped by criterion. Claude
drafts them, presents them, and stops. The approval is bound to the SHA-256 of
`scenarios.md` and of `spec.md`.

**Gates derived from the spec.** Nothing is `done` because the code is written.
**Gate A — spec verified**: every criterion has its test, the checkpoint ran
through `bin/craft-check` and passed, lint and format pass. **Gate B — review
green**: every routed lens ran, and no Confirmed Critical or High finding is
open. The `Stop` hook refuses a `done` that no recorded check supports.

**One reviewer, several lenses.** A single `reviewer` pass (Sonnet) reads the
diff once and applies the lenses the diff earns: `spec` conformance, `style`,
`logic`, `security`, `query`. `deep-reviewer` (Opus) runs only when the spec
says `Risk: high`, and only for `logic` and `security`. Re-review covers the
fix delta, not the whole diff again.

**Built to be cheap.** Agents read standards by section with `bin/craft-std`,
never whole files. Developer English uses a one-page card, not an 18 KB skill.
Test output goes through `bin/craft-check`, which prints the summary or the
failures and keeps the full log on disk. A `SessionStart` hook prints where the
active spec stands, so a new session resumes from the spec instead of
re-exploring the repository. See [Cost](#cost).

**Three discipline skills.** `minimal-code`, `validation-discipline` and `test-discipline` stop
the most expensive AI habit: writing code nobody asked for. `minimal-code` is a
"laziness ladder" (reuse, stdlib, framework, dependency, one line, then build
the minimum), after the `ponytail` plugin. Their decisions go
into the spec, where the developer sees what was left out and why.

**A health check and a toolchain installer.** `/craft-doctor` verifies the
plugin's own wiring. `/craft-toolchain` finds the linter, formatter, test runner
and type checker a repository needs, and asks before installing anything.

**🧩 Every backend stack (0.7).** `bin/craft-stack` detects Django, FastAPI,
Go, Java, Node, and PHP (Laravel, Symfony; 0.9), per directory in a monorepo. The stack picks the skills,
the Gate A commands, the path globs that set risk, and the reviewer's lens
notes. `bin/craft-spec trace` finds criterion IDs in every language's tests.

**🧵 High concurrency only where the system is built for it (0.7).** The
`concurrency` skill reads the model a service runs (sync Django on WSGI,
async-native FastAPI, goroutines, Spring MVC, virtual threads, reactive, the
Node event loop, PHP-FPM or long-lived PHP workers) and says `ready`, `limited`, or `not-ready`. `fastapi-async`
and `go-concurrency` hold the patterns for systems that are ready. A system
that is not ready gets a cheaper fix, a background job, or a `project` that
changes the model on purpose, never async as a side effect.

**🧠 AI deciders, free ones too (0.7).** The routing questions go to Jev, to a
free tier (OpenRouter's free router, Groq, Gemini, Cerebras, Mistral, GitHub
Models, Cloudflare), to a local model (Ollama, LM Studio), or to Claude Haiku,
one at a time or as a council. The rules floor applies to all of them.

**🎛️ A Claude Code mod (0.7).** The status at the top of the screen, a 🗂 craft
board with tabs for the spec, tasks, gates, review, 💰 cost per agent, and
deciders, commands that cost no tokens, and the spec gate as a question you
answer with one key.

---

## Install

```bash
git clone https://github.com/amirtlbyn/craft-workflow.git \
  ~/.claude/plugins/craft-workflow
```

Then enable it in Claude Code. Or install it from its own marketplace, in a
Claude Code session:

```
/plugin install craft-workflow --marketplace https://github.com/amirtlbyn/craft-workflow.git
```

Verify with `/craft` — it should classify a request and name a route — and
`/craft-status`, which answers from the mod with no Claude turn. The mod needs
Claude Code 2.1.287 or later; on an older one, or in ZCode, everything except
the mod works as before. Upgrading from 0.2? Read [CHANGELOG.md](CHANGELOG.md)
first.

To develop the mod: `claude --plugin-dir .` hot-reloads it, `claude plugin
validate .` checks it, and `claude plugin test` runs `tests/`.

## Use

```
/craft   <anything>    classify, then run the right route
/quick   <small fix>   inline, no spec, no subagent
/task    <one MR>      spec → approval → implement inline → one review pass
/project <big thing>   spec → approval → design and sessions → coder per session
```

Or drive the steps yourself:

```
/spec  /plan  /implement  /review  /fix-review  /progress  /finish
/design-brainstorm  /arch  /debug  /test-audit
/minimal-audit  /minimal-gain      find over-engineered code, measure what a change added
/jev on | off | status | test     optional: let Jev make the routing decisions
/decide status | use | council    choose the deciders: Jev, free tiers, local models, Haiku
/stack  /concurrency              the stacks of this repository, and its concurrency verdict
```

From the mod, with no Claude turn and no tokens:

```
/craft-board    🗂 the board: 📋 spec · ✅ tasks · 🚦 gates · 🔍 review · 💰 cost · 🧠 deciders
/craft-status   🛠️ where the spec stands, in a few lines
/craft-cost     💰 what each agent cost on this spec
/craft-gates    🚦 Gate A and Gate B, check by check
/craft-trace    🔗 map each criterion to its test now
```

A `task`, end to end:

```
you     /task add a daily withdrawal limit per tier
craft   Route: task — new business rule, one merge request, no design question.
        bin/craft-spec new --route task --title "Daily withdrawal limit per tier"
        ... writes spec.md: 5 criteria (WDL-1..5), 4 non-goals, Risk: high
        ... shows the criteria table and stops
you     approve, and add: a cancelled withdrawal does not count
craft   adds WDL-6 [developer], bin/craft-approve  → source files are open
        bin/craft-scenarios draft, adds 1+ scenario per criterion, shows them
you     approve
craft   bin/craft-approve --scenarios              → test files are open
        ... implements, one test per criterion, "WDL-3: ..." in each docstring
        bin/craft-check -- docker compose exec web pytest apps/wallet -q
        bin/craft-spec trace                        → 6 of 6 criteria have a test
        reviewer (spec, style, query) ∥ deep-reviewer (logic, security)
        ... adjudicates, fixes one High, delta re-review, logs both gates
        State: done. Gate A and Gate B green.
```

The commands behind it:

```
bin/craft-spec new|status|trace|close   create, inspect, trace, and close a spec
bin/craft-approve                        record the developer's approval of spec.md
bin/craft-approve --scenarios            record the approval of scenarios.md
bin/craft-scenarios status|draft         the scenarios state, make scenarios.md from the spec
bin/craft-scenarios add|set|remove       add, replace, or delete one scenario of a criterion
bin/craft-check -- <command>             run a check, record its exit code, print a summary
bin/craft-std --list | <file> <section>  read one section of a standard
bin/craft-jev on|off|status|test|decide  the optional Jev decision layer
bin/craft-doctor  bin/craft-toolchain    health check, toolchain installer
bin/craft-stack [checks|concurrency|…]   the stacks, their checks, the concurrency verdict
bin/craft-decide status|use|council|…    the AI deciders
bin/craft-ui-state                       the JSON the mod draws
```

`bin/` means the plugin's `bin/` directory, `"${CLAUDE_PLUGIN_ROOT}"/bin/`.
Run the commands from the host repository.

---

## The spec on disk

```
<repo>/.claude/specs/
├── ACTIVE                       one line: the active spec directory
└── 2026-09-23-daily-withdrawal-limit-tier/
    ├── spec.md                  WHAT and WHY. Approved. Stable
    ├── design.md                HOW. project route only
    ├── scenarios.md             Given/When/Then lines per criterion. Approved second
    ├── tasks.md                 the checklist, its state, the checkpoint
    └── log.md                   append-only: approvals, gates, reviews, deltas
```

`skills/spec/examples/withdrawal-limit.spec.md` is a finished task spec. The
templates are in `skills/spec/templates/`.

When the code shows the spec is wrong, the workflow stops and proposes a **spec
delta**: the rows to add, change, or remove. After the developer approves it,
`spec.md` changes, `log.md` records why, and `bin/craft-approve` opens the gate
again. The spec stays true for the life of the change.

`bin/craft-scenarios draft` makes `scenarios.md` with one `## <criterion ID>`
section per criterion. It keeps every line already there. It moves the section
of a removed criterion under `## Retired`. It writes no scenario: Claude adds
them with `add`, and the developer can change them with `set` and `remove`.
`bin/craft-approve --scenarios` refuses while a criterion has no scenario.
Changing `scenarios.md` or `spec.md` afterward makes the scenarios `stale`, and
the gate closes test files again. `skills/spec/templates/scenarios.md` shows the
format.

---

## Stacks

| Stack | Detected by | Tests name the ID in | Gate A | Concurrency |
|---|---|---|---|---|
| 🐍 Django | `manage.py`, Django in the dependencies | the docstring | §6 of `config/workflow.md` | sync: Celery, not async views |
| ⚡ FastAPI | FastAPI in the dependencies | the docstring | `pytest`, `ruff check`, `ruff format --check`, `mypy` | `fastapi-async` when ready |
| 🐹 Go | `go.mod` | `t.Run("WDL-3 …")` or `// WDL-3:` | `go test`, `go test -race`, `go vet`, `golangci-lint`, `gofmt` | `go-concurrency` |
| ☕ Java | `pom.xml`, `build.gradle*` | `@DisplayName("WDL-3: …")` | `./mvnw test` or `./gradlew test`, Spotless, Checkstyle | the model the report names |
| 🟩 Node | `package.json` | `it('WDL-3: …')` | `pnpm test`, ESLint, Prettier, `tsc --noEmit` | the event loop, bounded |
| 🟥 Laravel, 🎼 Symfony, 🐘 PHP | `artisan` or `laravel/framework`; `symfony/framework-bundle`; any `composer.json` | `it('WDL-3: …')`, `#[TestDox('WDL-3: …')]`, or a `//` comment above the test | `composer test`, `vendor/bin/pest`, `php artisan test` (Laravel) or `phpunit`; PHPStan or Psalm; Pint (Laravel) or PHP-CS-Fixer | the report names it: process per request, long-lived workers, or event loop |

`bin/craft-stack checks` prints the commands it resolved for this repository.
A host `.claude/craft.md` overrides any of them. To add a stack, see
[CUSTOMIZE.md](CUSTOMIZE.md#add-a-stack).

## The craft mod

What Claude Code looks like with it:

```
🛠️ craft  📦 task · WDL Daily withdrawal limit            ← the board's header, top right
🐹 go  🔴 risk high  🧵 ready  🧠 council
📋 ✅ approved  🅰️ 🔗❌ 🧪✅ 🏁✅ 🎨❌  🅱️ ⏳ in review
💰 $1.84  ⏱ 5h ████░░░░░░ 42%  🧠 ctx 61%
1 📋 Spec  2 ✅ Tasks  3 🧪 Scenarios  4 🚦 Gates  5 🔍 Review  6 💰 Cost  7 🧠 Deciders
```

- **Status at the top.** In a wide fullscreen terminal the board docks beside
  the transcript, so its header is the status at the top of the screen. Where
  there is no room, the same status is a band above the prompt. Set
  `status` to `prompt` or `both` in `/plugin` → craft-workflow → options.
- **💰 Cost per agent.** Every model request is counted under its agent: the
  main session, `reviewer`, `deep-reviewer`, `coder`, Explore, and the
  deciders. Priced with `config/prices.json`, kept per spec across sessions,
  with the engine's own ledger beside it.
- **The spec gate as a question.** Before the spec is approved, a write to
  source asks you: 👀 open the spec, ✅ approve it, or 🚫 keep it blocked.
- **Findings you can act on.** The Review tab confirms or rejects a finding
  with one key, and Gate B follows.
- **🧪 The Scenarios tab (key 3).** It lists every criterion with its text and
  its numbered scenarios, and marks a criterion that has none. `j` and `k` move
  the selection (or press a row). `e` edits the selected scenario, `i` adds one
  to its criterion, and `x` deletes it after a confirm. Enter saves; an empty
  Enter closes the field. `a` approves the scenarios, after a confirm. The tab runs
  `bin/craft-scenarios` and `bin/craft-approve --scenarios`. It decides nothing.
- **📄 A document viewer.** `o` on the Spec or Tasks tab opens the spec's
  files in a pane of their own: `s` spec.md, `d` design.md, `t` tasks.md,
  `l` log.md, `n` scenarios.md. Template comments are removed, and a table too
  wide for the pane is drawn as one block per row. `a` approves, after the same
  confirm as the board. Esc closes it.
- **◀ ▶ Sideways scroll.** When a row's text is wider than the board, `h` and
  `l` shift the long text of every row on the tab. The IDs and glyphs stay in
  place. A new tab starts at the left edge.

### The status line

The mod cannot replace Claude Code's status line: that line is the
`statusLine` command in `settings.json`. Point it at `bin/craft-statusline`:

```json
"statusLine": {
  "type": "command",
  "command": "python3 /path/to/craft-workflow/bin/craft-statusline --detail",
  "refreshInterval": 60
}
```

```
🛠 Opus · high · ⎇ main │ craft task · CSL ✓ approved · A trace ✓ tests ✗ · B ○ · 3/7
🧠 ctx ███░░░░░ 42% 84k/200k │ ⏱ 5h ██████░┃░░ 62% ↻1h10m pace 77% │ 📅 7d ██░┃░░░░░░ 18% ↻4d6h pace 39%
💰 $1.23 · $2.11/h · 35m (api 12m) · +120 −8 · in 1.2M out 45k · cache 93%
```

The `S` glyph shows the scenarios state next to `A` and `B`.
The `┃` in a usage bar is the pace: where usage would be if it grew evenly over
the window. `⚠ full in 40m` shows when the current rate reaches 100% before
the window resets. `--detail` adds the third line.

- `--theme=` `craft` (default), `minimal`, `neon`, `ocean`, `dracula`, `nord`,
  `catppuccin`, `gruvbox`, `tokyo-night`, `mono`
- `--bar=` `gradient-pill`, `pill`, `gradient`, `blocks`, `smooth`, `dots`,
  `line`, `squares`, `braille`, `ascii` (default: the theme's own)
- `CRAFT_STATUSLINE_THEME`, `CRAFT_STATUSLINE_BAR`, `CRAFT_STATUSLINE_DETAIL=1`,
  `NO_COLOR` do the same from the environment; a flag wins.

`bin/craft-statusline --preview` prints every theme and bar style on sample data.

The mod draws what `bin/craft-ui-state` reports. It never decides a gate. The
Python hooks still enforce every rule, so the VS Code panel, `claude -p`,
ZCode, and Codex keep them. The mod's drawings show in the terminal and in the
Desktop app's Code tab.

## Deciders — Jev and the others

Since 0.7, Jev is one of several deciders. `bin/craft-decide` picks them:

```bash
bin/craft-decide status                    # free? local? may keep prompts? key found?
bin/craft-decide use ollama                # the most private: nothing leaves the machine
bin/craft-decide council jev,groq,ollama   # ask together, average the answers
bin/craft-decide test all                  # one tiny question to each
bin/craft-decide discover openrouter-free --free
```

A free tier that may keep prompts gets no request text unless you set
`send_request_text true` for it. The rest of this section describes Jev, the
default.

## Jev — optional typed decisions

[Jev](https://openrouter.ai/typesafe/jev-1.13) is TypeSafe's "System One"
decision model. It does not write text and it does not call tools. It answers
typed questions — yes/no with a probability, or one choice from a list with
calibrated confidence — in about 0.7 to 1.3 seconds in practice, for about $0.04 per
million input tokens. This plugin reaches it through OpenRouter's Decisions API.

With `/jev on`, Jev makes the routing decisions Claude otherwise makes by
reading prose:

| Stage | Jev decides | Used for |
|---|---|---|
| `route` | route, risk tier, implementer model (haiku / sonnet / opus), which skills to load | The route line, the spec header, the `coder` model, the skill loads |
| `review` | risk tier, whether the `logic`, `security`, and `query` lenses apply | Which lenses `reviewer` and `deep-reviewer` get |

Four rules keep it safe:

- **A rules floor.** Path globs from `config/paths.json` and keywords for money,
  auth, migrations, concurrency, and integrations set a minimum route, risk
  tier, model, and lens set. Jev can raise a decision above the floor, never
  lower it.
- **A confidence threshold.** A choice below 0.7 is undecided, and Claude decides.
- **Fail open.** No key, a timeout (one retry with backoff), or an HTTP error
  means `rules only`. The work never stops for Jev.
- **Little leaves the machine.** Jev gets the request text (skip it with
  `--no-request-text`), changed paths, and line counts, never file contents.
  The request asks providers not to collect data.

Set it up once:

```bash
export OPENROUTER_API_KEY=sk-or-...        # or write it to ~/.config/craft-workflow/openrouter.key
/jev on                                     # this repository only. CRAFT_JEV=on|off overrides it
/jev test                                   # one call: the answer, the latency, the cost
```

Tune the questions in `config/jev.json`. Every decision goes into
`.claude/craft/jev-log.jsonl`, without the request text, so you can see where
Jev and you disagree before you trust it with more.

**Change the endpoint or the model** for one repository, without editing plugin
files that an update would overwrite:

```bash
bin/craft-jev set endpoint https://<host>/api/alpha/decisions
bin/craft-jev set model typesafe/jev-1.13
bin/craft-jev unset endpoint                 # back to config/jev.json
bin/craft-jev status                         # shows each value and where it came from
```

`CRAFT_JEV_URL` and `CRAFT_JEV_MODEL` override both for one shell. Only
`https://` endpoints are accepted, so the key never travels in clear text.

### Tool-call approval — `/jev approve on`

A second, separate switch lets Jev approve tool calls that would otherwise
prompt you, so work in `default` permission mode runs with fewer
interruptions. It is off until you run `/jev approve on`, and it needs Jev on.

It can only turn a prompt into an approval. When it does not approve, it stays
silent and Claude Code asks you as usual:

| Check, in order | Result |
|---|---|
| `bypassPermissions` or `plan` mode | does nothing |
| `protect_human_owned` or the spec gate would deny | does nothing, they deny |
| `deny_patterns`: `rm -rf /`, `mkfs`, `curl … \| sh`, `dd of=/dev/…` | **denied** |
| `ask_patterns`: git push and history rewrites, installs, network tools, credentials, databases, `python -c`, deploys, `craft-approve`, `CRAFT_HOOKS=off` | you are asked |
| `ask_path_patterns`: `.env`, `.ssh/`, keys, `.git/`, the craft state files, anything outside the repository | you are asked |
| Jev: `allow` at ≥ 0.90, "irreversible" < 0.30, "sends data out" < 0.30 | **approved** |
| Anything else, a timeout, or an error | you are asked |

Secrets in a command (bearer tokens, `sk-…`, `password=…`, AWS keys,
`user:pass@` in URLs) are redacted before the call. File contents are never
sent. Every decision is logged in `.claude/craft/jev-approvals.jsonl`. Each
eligible call waits about 0.7 to 1.3 seconds in practice for Jev, or up to 3 seconds when
it times out.

The lists live in the `approve` block of `config/jev.json`. Add your own
must-ask commands there. Keep your own deny rules in Claude Code's settings
too: this hook is a convenience, not your last line of defence.

---

## Layout

```
.claude-plugin/plugin.json   the manifest
config/workflow.md           ← the file you edit
config/paths.json            the glob sets the hooks and trace read
config/toolchain.json        the tools craft-toolchain looks for
config/jev.json              the decider questions, and Jev's model, endpoint, thresholds
config/deciders.json         the decider providers, the mode, the order, the council
config/prices.json           the price table for cost per agent
stacks/<id>/                 a stack pack: stack.json and lenses.md
hooks/mod.json, hooks/mod/   the Claude Code mod (craft.tsx, view.ts)
types/index.d.ts             the mod's state contract
tests/                       the mod's tests, for claude plugin test
standards/                   vendored code style and engineering standards
skills/                      the skills the workflow loads
skills/spec/templates/       spec.md, design.md, tasks.md, log.md
skills/review-protocol/lenses/  spec, style, logic, security, query
agents/                      coder, reviewer, deep-reviewer
commands/                    the slash commands
hooks/                       the rules the workflow enforces, not requests
bin/                         craft-spec, craft-approve, craft-check, craft-std,
                             craft-jev, craft-session, craft-doctor,
                             craft-toolchain, craft-sync-codex
scripts/                     hook implementations, state library, self-test, CI checks
evals/                       measures the plugin's own claims, with and without it
.agents/skills/, .codex/agents/, .zcode-plugin/agents/, AGENTS.md
                             generated by bin/craft-sync-codex — never hand-edit these
```

## Skills

| Skill | Loads when |
|---|---|
| `craft` | Any coding request. Picks the route |
| `spec` | Writing, approving, or changing a spec |
| `planner` | Turning an approved project spec into a design and sessions |
| `python-style` / `django-practices` | Python / Django work |
| `fastapi-practices`, `go-practices`, `java-practices`, `node-practices`, `php-practices` | Work in that stack. `bin/craft-stack skills` names them |
| `concurrency` | Concurrent code for throughput, or a request for async, parallel, or "high concurrency" |
| `fastapi-async` / `go-concurrency` | Async FastAPI / goroutines, when the concurrency report says ready |
| `minimal-code` | Writing any new function, class, module, helper, or dependency |
| `validation-discipline` | Adding a check, guard, validator, or constraint |
| `test-discipline` | Choosing criteria, writing or auditing tests |
| `review-protocol` | Acting as a reviewer, or adjudicating findings |
| `debugging` | Diagnosing a bug |
| `git-hygiene` | Diff hygiene and merge-request text |
| `system-design` | Unsettled architecture |
| `arch-assistant` | A second opinion on shape. Advisory — you always decide |
| `asd-ste100` | Rewriting a long developer document. Short text uses `references/card.md` |
| `toolchain` | A check cannot run because the tool is not installed |
| `jev` | `/jev`, or a routing decision while Jev is on |

## Review

| Agent | Model | Runs | Lenses |
|---|---|---|---|
| `reviewer` | sonnet | Every `task` and `project` review | The routed lenses. On `Risk: high`, all except `logic` and `security` |
| `deep-reviewer` | opus | Only on `Risk: high` | `logic` and `security`, focused on the spec's invariants |

| Lens | Ceiling | Confidence | Owns |
|---|---|---|---|
| `spec` | High | 0.7 | Criteria implemented and tested, nothing extra, non-goals held |
| `style` | Medium | 0.8 | Naming, developer English, docstrings, idiom. Not formatting |
| `logic` | Critical | 0.6 | Correctness, money, concurrency, transactions, migrations, tests |
| `security` | Critical | 0.5 | Application security only |
| `query` | High | 0.7 | Database access cost only |
| `concurrency` | High | 0.6 | Concurrent code for throughput, and whether the system is built for it |

Each lens keeps the old reviewer's checklist, severity ceiling, and confidence
threshold. Every checklist item must be answered, including the ones that do not
apply. Findings are adjudicated before you see them: every Critical and High is
verified against the code. Say "full review" to spawn one reviewer per lens
instead.

---

## Cost

A rough model of one `/task` with one fix round, built from this plugin's own
file sizes. The 0.3.0 entry of [CHANGELOG.md](CHANGELOG.md) lists what each
agent loads. It counts the instructions each agent loads at
the start, plus 40 KB for each agent that re-reads the repository from cold. It
ignores the turns after that, so real usage is higher in both columns. The
weighting assumes Opus draws about five times the quota of Sonnet.

| | 0.2.2 | 0.3.0, `Risk: low` | 0.3.0, `Risk: high` |
|---|---|---|---|
| Agents started, with the main session | 11 | 3 | 4 |
| Opus runs | 4 | 0 | 2 |
| Start-up input | ~233k tokens | ~47k tokens (−80%) | ~58k tokens (−75%) |
| Quota-weighted | ~448k | ~47k (−89%) | ~139k (−69%) |

Where the savings come from:

- `task` implements in the main session. It already holds the context, so no
  `coder` re-reads it.
- One `reviewer` pass instead of four. Opus runs only on `Risk: high`.
- Re-review is the fix delta and only the reviewer with a Critical or High, not
  every reviewer on the whole diff again.
- Standards by section (`bin/craft-std`) instead of whole 20–25 KB files.
- A one-page writing card instead of the 18 KB `asd-ste100` skill on every
  comment.
- `quick` spawns no reviewer. The linters and one self-read are enough for a typo.
- `bin/craft-check` keeps test output out of the context.
- The `SessionStart` hook resumes from the spec instead of re-exploring.

---

## Codex CLI

Claude Code discovers this plugin through `skills/`, `commands/`, `agents/`,
and the global `CLAUDE.md`. Codex CLI has no equivalent plugin system, so
`bin/craft-sync-codex` generates a Codex-native mirror from that same source:
a `.agents/skills/<name>/SKILL.md` for every skill and every command, a
`.codex/agents/<name>.toml` for every subagent, and an `AGENTS.md` for this
repository itself. That mirror is already generated and committed here —
installing for Codex means making it visible where Codex looks, not
regenerating it.

### Install for Codex

```bash
git clone https://github.com/amirtlbyn/craft-workflow.git \
  ~/.claude/plugins/craft-workflow
```

Skip that clone if you already did it for Claude Code — the same checkout
serves both. Codex has no plugin loader that can reference a clone, so
symlink its generated skills and agents into one of the two places Codex
actually scans. Pick one:

**Every repository** — Codex's user-level directories:

```bash
mkdir -p ~/.agents/skills ~/.codex/agents
for dir in ~/.claude/plugins/craft-workflow/.agents/skills/*/; do
  ln -s "$dir" ~/.agents/skills/"$(basename "$dir")"
done
for file in ~/.claude/plugins/craft-workflow/.codex/agents/*.toml; do
  ln -s "$file" ~/.codex/agents/"$(basename "$file")"
done
```

**One repository** — that repository's own directories instead:

```bash
cd /path/to/your-repo
mkdir -p .agents/skills .codex/agents
for dir in ~/.claude/plugins/craft-workflow/.agents/skills/*/; do
  ln -s "$dir" .agents/skills/"$(basename "$dir")"
done
for file in ~/.claude/plugins/craft-workflow/.codex/agents/*.toml; do
  ln -s "$file" .codex/agents/"$(basename "$file")"
done
```

Verify by starting `codex` in a repository the symlinks reach, then running
`$craft <anything>` — it should classify the request and name a route, the
same way `/craft` does in Claude Code.

The symlinks reference files this repository already generated and
committed, so a plain `git pull` in the clone keeps Codex's view current.
Only someone editing `skills/`, `commands/`, or `agents/` in this plugin
needs to run `bin/craft-sync-codex --write` (see [Layout](#layout))
afterward.

**What is not covered yet.** The hooks — the spec gate, `*.human.md`
protection, the done/Gate-A verification at session end, and the session-start
status — run only under Claude Code and ZCode today. The `bin/` commands
(`craft-spec`, `craft-approve`, `craft-check`, `craft-std`) work under Codex
too. Codex's exact hook payload
schema cannot be verified from documentation alone, so `.codex/hooks.json` is
separate, later work, checked against a real Codex session rather than
assumed from docs. A Codex session can still follow the workflow as prose,
but nothing blocks it from skipping a gate the way the Claude Code hooks do.
See [CUSTOMIZE.md](CUSTOMIZE.md#codex-cli-support) for the full mapping.

---

## Enforcement

Most of this workflow is prose, and prose can drift. Four hooks in
`hooks/hooks.json` do not, and they read state kept in the host repository's
`.claude/craft/` and `.claude/specs/`:

| Hook | Event | What it makes real |
|---|---|---|
| `gate_spec.py` | `PreToolUse` on Write/Edit/MultiEdit/NotebookEdit | On `task` and `project`, no source or test file is written until `spec.md` is approved at its current SHA-256. No test file is written until `scenarios.md` is approved too |
| `protect_human_owned.py` | `PreToolUse` on Write/Edit/MultiEdit/NotebookEdit | A `*.human.md` document cannot be edited by an agent |
| `verify_gates.py` | `Stop` | A claim of `done` or Gate A needs a green checkpoint, an approved spec, and a green `craft-spec trace` |
| `session_context.py` | `SessionStart` | A new session sees the active spec, its state, and the next task, in a few lines |

`bin/craft-spec new` starts the session. `bin/craft-approve` records the
approval. `bin/craft-check` records each check with the exit code the command
really returned. Without a session, every hook except `protect_human_owned` is
inert, and a repository that does not use the workflow pays nothing.

Every hook fails open — a crash, a missing file, or malformed JSON lets the call
through — and `CRAFT_HOOKS=off` disables all of them at once.
`python3 scripts/craft_selftest.py` exercises every hook and command against
synthetic repositories. Full detail, including known limits, is in
[`hooks/README.md`](hooks/README.md).

## Measuring the claims

`evals/` runs each documented behavior — a route choice, the spec gate, the
human-owned refusal, the false-`done` correction — with the plugin loaded and
without it, and reports the delta. It is a real, billed model call, run by hand:

```bash
claude plugin eval . --trust-plugin --scaffold --allow-tools Write Edit Bash \
  --threshold 0.8 --model claude-sonnet-5 --judge-model claude-haiku-4-5 \
  --no-publish --max-cost-usd 20
```

CI (`.gitlab-ci.yml`) does not run that suite — no runner here holds an API key.
It runs free, deterministic checks instead: `craft_selftest.py` against the
hooks, `stack_selftest.py` against the stacks, the trace, the checks, and the
deciders, `sync_codex_selftest.py` against the Codex generator,
`validate_evals.py` against every eval case and grader, and
`craft-doctor --skip commands` against the plugin's own wiring. They use the
standard library on Python 3.11+; Python 3.10 installs the small `tomli`
compatibility dependency declared in `requirements.txt` when pip is available,
and otherwise skips the one TOML parse case that needs it. See
[`evals/README.md`](evals/README.md).

---

## Customizing

See [CUSTOMIZE.md](CUSTOMIZE.md). Short version: edit `config/workflow.md`, add or
delete directories under `skills/`, add a lens file, and replace `standards/` to
retarget the workflow to another language.

## Credits

`skills/asd-ste100/` is vendored from an MIT-licensed skill. Its `LICENSE` is kept
intact. `standards/*.human.md` are human-owned documents — agents may propose
changes to them but must never edit them, and `protect_human_owned.py` enforces
that instead of just asking for it.

This plugin itself is MIT-licensed — see [`LICENSE`](LICENSE).
