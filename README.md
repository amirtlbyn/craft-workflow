# craft-workflow

A spec-driven engineering workflow for Claude Code, packaged as one plugin.
It works on any backend stack: 🐍 Django, ⚡ FastAPI, 🐹 Go, ☕ Java,
🟩 Node, and 🐘 PHP (🟥 Laravel, 🎼 Symfony).

You install it once. It then gives every repository the same discipline:

- Each request gets only as much process as it needs.
- You approve a written spec before any code is written.
- A change is `done` only when its tests ran green and a review found no
  open Critical or High finding.
- Hooks enforce these rules. The model cannot skip them.

---

## Contents

- [Quick start](#quick-start)
- [How a request runs](#how-a-request-runs)
- [You stay in control](#you-stay-in-control)
- [Gates and enforcement](#gates-and-enforcement)
- [Standards per project](#standards-per-project)
- [Stacks](#stacks)
- [The board, the status line, and themes](#the-board-the-status-line-and-themes)
- [Command reference](#command-reference)
- [Review](#review)
- [Codex CLI and ZCode](#codex-cli-and-zcode)
- [Develop and test the plugin](#develop-and-test-the-plugin)
- [Customize](#customize)

---

## Quick start

Install from this repository's marketplace. Run these two commands in Claude Code:

```
/plugin marketplace add amirtlbyn/craft-workflow
/plugin install craft-workflow@craft
```

To install from a local clone instead, give the clone's path:

```bash
git clone https://github.com/amirtlbyn/craft-workflow.git ~/src/craft-workflow
claude plugin marketplace add ~/src/craft-workflow
claude plugin install craft-workflow@craft
```

A local clone is read in place. Change the checked-out branch, and the
plugin changes with it in the next session.

Check the install:

1. Start a new Claude Code session in any repository.
2. Type `/craft add a health-check endpoint`. Claude names a route and gives
   one reason.
3. Type `/craft-status`. The mod answers at once, with no Claude turn.

The mod needs Claude Code 2.1.287 or later. On an older version, everything
except the mod still works.

Put this line in your global `~/.claude/CLAUDE.md` so every coding request
starts in the workflow:

```
Start any coding request with /craft.
```

---

## How a request runs

### Three routes

`/craft` reads the request and picks a route. It states the route and one
reason, then continues. It never asks you to confirm the route. Say
"use route X" to change it.

| Route | For | What happens |
|---|---|---|
| `quick` | A typo, a rename, a one-line fix | Claude edits in the main session, runs the focused checks, and reads its own diff once. No spec, no subagent. |
| `task` | One merge request | Spec → your approval → scenarios → your approval → code → Gate A → one review → Gate B. |
| `project` | Work that needs several sessions | As `task`, plus `design.md` and a plan of sessions in `tasks.md`. A `coder` subagent implements each session. |

A route only goes up. A `quick` request that touches money, authentication,
authorization, a migration, concurrency, or an external contract runs as
`task`.

### The steps of a `task`

```
you     /task add a daily withdrawal limit per tier
craft   Route: task — new business rule, one merge request.
        Asks each open question as multiple choice (you can also type your own answer).
        Writes spec.md: criteria WDL-1..5, non-goals, invariants, Risk: high. Stops.
you     ! craft-approve                               → source files open
craft   Writes scenarios.md: Given/When/Then lines for each criterion. Stops.
you     ! craft-approve --scenarios                   → test files open
craft   Picks a model for the work, implements, writes one test per criterion.
        craft-check -- pytest apps/wallet -q          → Gate A
        craft-spec trace                              → 5 of 5 criteria have a test
        reviewer ∥ deep-reviewer                      → Gate B
        Fixes confirmed findings. Logs both gates. State: done.
```

### The spec on disk

Each spec lives in the host repository:

```
<repo>/.claude/specs/
├── ACTIVE                         the active spec directory, one line
└── 2026-09-23-daily-withdrawal-limit/
    ├── spec.md                    WHAT and WHY. You approve it.
    ├── scenarios.md               Given/When/Then per criterion. You approve it.
    ├── design.md                  HOW. Project route only.
    ├── tasks.md                   Sessions, tasks, models, the checkpoint
    └── log.md                     Approvals, gates, reviews, deltas. Append-only.
```

`spec.md` holds acceptance criteria in EARS form
(`WHEN …, THE … SHALL …`). Each criterion has an ID such as `WDL-3`. Each
criterion gets exactly one test, and that test names the ID.
`craft-spec trace` proves the mapping.

When the code shows that the spec is wrong, Claude stops and proposes a
**spec delta**. You approve the delta, and the spec stays true for the life
of the change.

---

## You stay in control

**Only you approve.** Claude writes the spec, then stops. You record the
approval yourself, with the `!` prefix or with the `a` key on the board:

```
! "<plugin root>/bin/craft-approve"              approve spec.md
! "<plugin root>/bin/craft-approve" --scenarios  approve scenarios.md
```

The approval is bound to the SHA-256 of the file. When `spec.md` changes,
the gate shuts until you approve again. Claude cannot run `craft-approve`,
edit the approval state, or set `CRAFT_HOOKS=off`. A hook refuses each of
these.

**No assumptions in a spec or design.** Before Claude drafts `spec.md` or
`design.md`, it asks each open question with two to four options. The
recommended option comes first. You can always type your own answer. Each
answer goes into the spec as `<answer> (developer, <date>)`.
`craft-approve` refuses a spec that has a question with no answer from you.

**The model fits the work.** Claude picks a model for each session and writes
it in `tasks.md`:

| Model | When |
|---|---|
| haiku | Mechanical, low-risk, and well specified |
| sonnet | Normal work |
| opus | Security boundaries, cross-cutting or subtle logic, hard debugging |

Between sonnet and opus, Claude picks opus when a session spans more than one
app, or touches a security boundary, money, or concurrency. A spec with
`Risk: high` never gets haiku, and a hook refuses a haiku `coder` there.

---

## Gates and enforcement

### The two gates

| Gate | Passes when |
|---|---|
| **A — spec verified** | Every criterion has its test (`craft-spec trace`). The full checkpoint ran through `craft-check`, from the repository root, and passed. Lint and format pass. |
| **B — review green** | A review round is recorded, and a reviewer subagent really ran. No Confirmed Critical or High finding is open. The reviewed lenses cover the lens floor of the diff (`craft-spec lenses`). |

A recorded check expires when the code changes after it ran. A commit of the
same code does not expire it. On `quick`, Gate A is the focused checks, and
Gate B is Claude's own read of its diff.

### The hooks

| Hook | Event | Rule |
|---|---|---|
| `gate_spec.py` | Before Write, Edit, and Bash | Until `spec.md` is approved, no source file is written. Until `scenarios.md` is approved too, no test file is written. Shell writes count. |
| `gate_bash_after.py` | After Bash, also on failure | Finds files a shell command changed while the gate was shut. The Stop hook then asks Claude to restore them, and refuses to stop up to three times in a row. |
| `protect_approval.py` | Before Write, Edit, and Bash | Only you can approve, change the approval state, or turn the hooks off. |
| `protect_human_owned.py` | Before Write and Edit | No agent edits a `*.human.md` file. |
| `agent_gate.py` | Before Agent and Task | Records reviewer spawns for Gate B. Refuses a haiku `coder` on `Risk: high`. |
| `verify_gates.py` | Stop | Refuses a `done` or Gate A claim that the recorded checks, the trace, and the review do not support. |
| `session_context.py` | SessionStart | Shows where the active spec stands, so a new session resumes from the spec. |

Without an active spec, every hook except `protect_human_owned` and
`protect_approval` does nothing. A repository that does not use the workflow
pays nothing. Every hook fails open: a crash or bad input lets the call
through.

The hooks stop the shortcuts a well-meaning model takes. They do not stop a
determined script that runs as your user. [`hooks/README.md`](hooks/README.md)
lists the known limits.

---

## Standards per project

Every skill and reviewer reads standards through one command, `craft-std`.
It prints one section of a standard, not the whole file. It finds each
standard in three layers. The closest layer that has the name wins, and its
file replaces the same-named file below it.

| Layer | Directory | Use it for |
|---|---|---|
| project | `<repo>/aidocs/` | The team's own rules. Committed and reviewed with the code. |
| profile | `~/.config/craft-workflow/profiles/<name>/` | Rules that several of your repositories share, such as one company's. |
| plugin | `<plugin root>/standards/` | The defaults that ship with the plugin. |

Every top-level `*.md` file in a layer is a standard, except `README.md`. In
one layer, `.human.md` wins over `.ai.md`. A file that is a symlink to a place
outside its layer is ignored.

### Pick a profile

Map repositories to profiles in `~/.config/craft-workflow/profiles.json`. The
first rule that matches wins. A rule matches the `origin` remote URL or the
repository path:

```json
{
  "rules": [
    {"remote": "*git.example.com/backend/*", "profile": "company"},
    {"path": "/home/me/Project/*", "profile": "personal"}
  ]
}
```

A repository can also pin its profile for the whole team, in a committed
`aidocs/craft.json`. This file wins over `profiles.json`:

```json
{"profile": "company"}
```

A profile name uses only `a-z`, `0-9`, `_`, and `-`. A bad name, a missing
profile directory, or a file that does not parse prints one warning. The
other layers still answer.

### See and seed the standards

```bash
craft-std --where                # the three layers, the profile, and why it was picked
craft-std --list                 # every standard and its sections, with the layer of each file
craft-std django Views           # one section ("django" finds django_standards)
craft-std init                   # copy the defaults of this repo's stacks into aidocs/ as .ai.md
```

`init` never overwrites a file. When the team takes ownership of a copied
file, rename it from `.ai.md` to `.human.md`. From then on, no agent can edit
it. An agent that finds a gap reports the fragment it suggests, and you
decide.

---

## Stacks

`craft-stack` finds the stacks of a repository, per directory in a monorepo.
The stack picks the skills Claude loads, the Gate A commands, the paths that
raise risk, and the reviewer's notes.

| Stack | Found by | A test names its criterion ID in | Gate A |
|---|---|---|---|
| 🐍 Django | `manage.py`, Django in the dependencies | the docstring | `config/workflow.md` §6 |
| ⚡ FastAPI | FastAPI in the dependencies | the docstring | `pytest`, `ruff check`, `ruff format --check`, `mypy` |
| 🐹 Go | `go.mod` | `t.Run("WDL-3 …")` or `// WDL-3:` | `go test`, `go test -race`, `go vet`, `golangci-lint`, `gofmt` |
| ☕ Java | `pom.xml`, `build.gradle*` | `@DisplayName("WDL-3: …")` | `./mvnw test` or `./gradlew test`, Spotless, Checkstyle |
| 🟩 Node | `package.json` | `it('WDL-3: …')` | the package's test script, ESLint, Prettier, `tsc --noEmit` |
| 🟥 Laravel, 🎼 Symfony, 🐘 PHP | `artisan`, `symfony/framework-bundle`, `composer.json` | `it('WDL-3: …')`, `#[TestDox('WDL-3: …')]`, or a comment | Pest or PHPUnit, PHPStan or Psalm, Pint or PHP-CS-Fixer |

`craft-stack checks` prints the commands it found for this repository.
`craft-stack set <id>` overrides the detection.

**Concurrency only where the system is built for it.** The `concurrency`
skill reads the model a service runs, such as sync Django on WSGI, async
FastAPI, goroutines, or the Node event loop. It says `ready`, `limited`, or
`not-ready`. A service that is not ready gets a simpler fix or a background
job. Async code never arrives as a side effect.

---

## The board, the status line, and themes

### The board

The mod adds a 🗂 craft board beside the transcript:

```
🛠️ craft  📦 task · WDL Daily withdrawal limit
🐹 go  🔴 risk high  🧵 ready
📋 ✅ approved  🅰️ 🔗✅ 🧪✅ 🏁✅  🅱️ ⏳ in review
💰 $1.84  ⏱ 5h ████░░░░░░ 42%  🧠 ctx 61%
1 📋 Spec  2 ✅ Tasks  3 🧪 Scenarios  4 🚦 Gates  5 🔍 Review  6 💰 Cost  7 🎨 Theme
```

- **Spec and Tasks** show the spec, its sessions, and the model of each session.
  Press `o` to read the spec files in their own pane.
- **Scenarios** lets you edit, add, and delete scenarios. Press `a` to approve them.
- **Gates** shows Gate A and Gate B, check by check.
- **Review** confirms or rejects a finding with one key.
- **Cost** shows what each agent cost on this spec.
- **Theme** shows every theme in its own colours.

The mod only draws. The Python hooks enforce every rule, so the rules also
hold in VS Code, in `claude -p`, and in ZCode.

### The status line

Point Claude Code's status line at `craft-statusline` in `settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "python3 /path/to/craft-workflow/bin/craft-statusline --detail",
  "refreshInterval": 60
}
```

```
🛠 Opus · high · ⎇ main │ craft task · WDL ✓ approved · A trace ✓ tests ✗ · B ○ · 3/7
🧠 ctx ███░░░░░ 42% 84k/200k │ ⏱ 5h ██████░┃░░ 62% ↻1h10m pace 77% │ 📅 7d ██░┃░░░░░░ 18%
💰 $1.23 · $2.11/h · 35m · +120 −8 · cache 93%
```

The `┃` in a usage bar marks the pace: where usage would be if it grew evenly
over the window.

### Change the theme

There are ten themes: `craft`, `minimal`, `neon`, `ocean`, `dracula`, `nord`,
`catppuccin`, `gruvbox`, `tokyo-night`, and `mono`. The status line and the
board both use the theme you pick. Pick it in any of three places:

1. **The picker.** Type `/craft-theme`, or press `7` on the board. Move with
   `j` and `k`. Press `a` to apply.
2. **The plugin options.** `/plugin` → craft-workflow → options → `theme`
   and `bar`.
3. **The command line.**
   ```bash
   craft-statusline --set-theme nord
   craft-statusline --set-bar dots
   craft-statusline --unset
   craft-statusline --preview      # every theme and bar on sample data
   ```

All three write `~/.config/craft-workflow/statusline.json`. The latest change
wins.

---

## Command reference

### Slash commands

```
/craft   <request>     classify the request, then run its route
/quick   <small fix>   edit inline, no spec, no subagent
/task    <one MR>      spec → approvals → implement → one review
/project <big change>  spec → approvals → design and sessions → coder per session

/spec /plan /implement /review /fix-review /progress /finish
/design-brainstorm /arch /debug /test-audit /minimal-audit /minimal-gain
/stack /concurrency /craft-doctor /craft-toolchain
```

### Mod commands (no Claude turn, no tokens)

```
/craft-board    the board
/craft-status   where the active spec stands
/craft-gates    Gate A and Gate B, check by check
/craft-trace    each criterion and its test
/craft-cost     what each agent cost on this spec
/craft-theme    the theme picker
```

### `bin/` commands

Run these from the host repository. `bin/` is the plugin's own directory,
`"${CLAUDE_PLUGIN_ROOT}"/bin/`.

```
craft-spec new|status|trace|lenses|close   create, inspect, trace, and close a spec
craft-approve [--scenarios]                record your approval (you run it, not Claude)
craft-scenarios status|draft|add|set|remove
craft-check -- <command>                   run a check, record its exit code, print a summary
craft-std --where | --list | init | <name> <section>
craft-stack [checks|skills|concurrency|set]
craft-session record-review|record-finding|finding
craft-statusline                           the status line and its theme
craft-doctor                               check the plugin's own wiring
craft-toolchain                            find and install the tools a repository needs
craft-sync-codex [--write]                 regenerate the Codex and ZCode mirror
craft-ui-state                             the JSON the mod draws
```

---

## Review

| Agent | Model | Runs | Lenses |
|---|---|---|---|
| `reviewer` | sonnet | Every `task` and `project` review | The lenses the diff needs. On `Risk: high`, all except `logic` and `security`. |
| `deep-reviewer` | opus | Only on `Risk: high` | `logic` and `security`, aimed at the spec's invariants |
| `coder` | per session | Each `project` session, and a `task` that needs a different model | None. It implements and tests. |

| Lens | Highest severity | Covers |
|---|---|---|
| `spec` | High | Criteria implemented and tested, nothing extra, non-goals held |
| `style` | Medium | Naming, developer English, docstrings, idiom |
| `logic` | Critical | Correctness, money, concurrency, transactions, migrations, tests |
| `security` | Critical | Application security |
| `query` | High | Database access cost |
| `concurrency` | High | Concurrent code, and whether the system is built for it |

`craft-spec lenses` computes the lens floor from the changed paths. Claude
can add lenses but cannot go below the floor. Claude verifies each finding
before you see it. Only a Critical or High fix gets a second review, and that
review covers only the fix.

### Cost

The workflow keeps cost low on purpose:

- One `reviewer` pass per round. `deep-reviewer` runs only on `Risk: high`.
- `task` implements in the main session when its model fits the work.
- Agents read standards by section, not whole files.
- `craft-check` keeps long test output out of the context.
- A new session resumes from the spec instead of exploring the repository again.

---

## Codex CLI and ZCode

`bin/craft-sync-codex --write` generates a mirror of the skills, commands, and
agents for other tools: `.agents/skills/`, `.codex/agents/`,
`.zcode-plugin/agents/`, and `AGENTS.md`. The mirror is committed, so do not
edit it by hand.

To use the workflow in Codex, symlink the mirror where Codex looks:

```bash
mkdir -p ~/.agents/skills ~/.codex/agents
for dir in /path/to/craft-workflow/.agents/skills/*/; do
  ln -s "$dir" ~/.agents/skills/"$(basename "$dir")"
done
for file in /path/to/craft-workflow/.codex/agents/*.toml; do
  ln -s "$file" ~/.codex/agents/"$(basename "$file")"
done
```

Then run `$craft <request>` in Codex. The `bin/` commands work in Codex. The
hooks do not run there yet, so Codex follows the workflow as instructions,
and nothing blocks a skipped gate. ZCode runs the hooks.

---

## Develop and test the plugin

```bash
claude --plugin-dir .                        # load this checkout, with hot reload of the mod
python3 scripts/craft_selftest.py            # every hook and command, on synthetic repositories
python3 scripts/stack_selftest.py            # stack detection, checks, and trace
python3 -m pytest tests -q                   # the gate, lens, model, standards, and status line tests
claude plugin test                           # the mod's tests
claude plugin validate .                     # the manifest and the mod
bin/craft-doctor                             # the plugin's wiring
bin/craft-sync-codex                         # the generated mirror has no drift
```

CI (`.gitlab-ci.yml`) runs these free, deterministic checks. The evals in
`evals/` measure each claimed behavior, with the plugin and without it. They
make real, billed model calls, so you run them by hand. See
[`evals/README.md`](evals/README.md).

### Layout

```
config/workflow.md       the file you edit: routes, gates, lenses, checks
config/paths.json        the path globs the hooks read
stacks/<id>/             one stack pack: stack.json and lenses.md
standards/               the default standards (the plugin layer)
skills/                  the skills the workflow loads
agents/                  coder, reviewer, deep-reviewer
commands/                the slash commands
hooks/                   hooks.json, and the mod in hooks/mod/
scripts/                 the hook code, the state library, and the self-tests
bin/                     the craft-* commands
tests/                   pytest and mod tests
evals/                   behavior evals
```

---

## Customize

- Change routes, gates, lenses, and checks in `config/workflow.md`. A
  repository can override it in `.claude/craft.md`.
- Give a project its own standards in `aidocs/`, or share them through a
  profile. See [Standards per project](#standards-per-project).
- Add a stack with a new `stacks/<id>/` pack.

[CUSTOMIZE.md](CUSTOMIZE.md) has the details. [CHANGELOG.md](CHANGELOG.md)
lists every release.

## License

MIT. See [LICENSE](LICENSE). `skills/asd-ste100/` is vendored from an
MIT-licensed skill, and its own `LICENSE` is kept.
