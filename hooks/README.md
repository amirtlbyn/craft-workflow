# hooks/ — the rules this workflow enforces, instead of requesting

Every other rule in this plugin is prose. A model under context pressure, a
different model, or the same model after a compaction can drift away from prose,
and the plugin cannot notice. These hooks are the rules that a session cannot
drift away from.

The rule that decides what belongs here: **what must not be broken becomes a
hook. What needs judgement stays prose.**

**Claude Code and ZCode only.** Codex CLI has its own hook system, but this
plugin does not generate a `.codex/hooks.json` yet — Codex's exact hook payload
schema cannot be verified from documentation alone, and a wrong guess would
silently fail to enforce a gate rather than loudly refuse to run. A Codex
session gets the skills, commands, subagents, and `bin/` commands (see
[CUSTOMIZE.md](../CUSTOMIZE.md#codex-cli-support)), but the rules below are
only requested there, as prose.

**The mod is not enforcement.** `hooks/mod.json` loads the craft mod
(`hooks/mod/craft.tsx`) in Claude Code 2.1.287 and later: the status at the top,
the craft board, cost per agent, and the spec gate as a question. It reads the
same state these hooks read, and it never decides a gate. When the developer
approves the spec from the mod's question, the mod runs `bin/craft-approve`,
and `gate_spec.py` still runs after it and checks the hash. Without the mod
(ZCode, the VS Code panel, `claude -p`, `--safe-mode`) every rule below holds.
ZCode reads `hooks/hooks.json` only, through `.zcode-plugin/plugin.json`.

---

## The hooks

| Script | Event | What it makes real |
|---|---|---|
| `scripts/gate_spec.py` | `PreToolUse` on `Write\|Edit\|MultiEdit\|NotebookEdit` | On `task` and `project`, no source or test file is written until the developer approves `spec.md` at its current SHA-256, and no test file until `scenarios.md` is approved too |
| `scripts/protect_human_owned.py` | `PreToolUse` on `Write\|Edit\|MultiEdit\|NotebookEdit` | A `*.human.md` document cannot be edited by an agent |
| `scripts/verify_gates.py` | `Stop` | A claim of `done` or Gate A needs a green checkpoint, an approved spec, and a green trace |
| `scripts/session_context.py` | `SessionStart` | A new session sees the active spec, its state, and its next task |
| `scripts/jev_approve.py` | `PreToolUse` on `Bash\|Write\|Edit\|MultiEdit\|NotebookEdit` | Optional, off by default. With `craft-jev on` and `craft-jev approve on`, Jev approves routine calls. It never approves what the lists in `config/jev.json` say to ask about, and it stays silent whenever another craft hook would deny |

### `jev_approve`

This is the one hook that may answer `permissionDecision: "allow"`, which
skips the developer's prompt. That is why it is off by default, needs two
switches, and checks in this order: permission mode, the other craft hooks,
`deny_patterns`, `ask_patterns` and `ask_path_patterns`, and only then Jev, at
confidence 0.9 with both risk questions below 0.3. Every other outcome is
silence, so the normal permission rules apply. It is also the one hook that
reaches the network. It uses `scripts/jev_client.py`, with a 3-second timeout
and no retry.

### `gate_spec`

Denies a `Write`, `Edit`, `MultiEdit`, or `NotebookEdit` call. It is inert
unless **all** of these hold:

1. `<repo>/.claude/craft/session.json` exists.
2. Its `route` is `task` or `project`. On `quick` the hook does nothing.
3. The target path is inside the host repository and outside `<repo>/.claude/`.
   Spec files, craft state, and files outside the repository are never gated.
4. The active spec is not `approved`: there is none, it was never approved, or
   `spec.md` changed after its approval (`stale`).

The denial names the state and the way through: `bin/craft-spec new`, the
developer's approval, then `bin/craft-approve`.

**The test-file check.** When the spec is approved, the hook checks one more
thing for a test file. It finds test files with the test globs and
extensions of the detected stack, the same `test_spec()` that `craft-spec trace`
uses. It denies the write until `scenarios.md` is approved. The approval records
the SHA-256 of `scenarios.md` and of `spec.md`. Both must match the files on
disk.

- A missing `scenarios.md` denies. The denial names the state, runs
  `bin/craft-scenarios draft`, and lists each criterion without a scenario.
- A `scenarios.md` that exists and cannot be read fails open: the write is allowed.
- A source file needs the spec approval only.

An approval is bound to the SHA-256 of `spec.md`, not to a Claude session. A new
session, for example after a usage-limit reset, keeps the gate open. An edit to
`spec.md` shuts it, because an edited spec is a spec delta the developer has not
seen.

### `protect_human_owned`

Denies a write whose target matches the `human_owned` globs in
`config/paths.json`, which today is `*.human.md`. This is the one hook that runs
with no craft session. Ownership is a property of the file, not of the session.

### `verify_gates`

Blocks the `Stop` when the final assistant message claims `done` or claims Gate A
passed, and one of these is true:

- `session.json` holds no check that exited 0. When the session names a
  checkpoint command, only a green check that names it counts.
- A spec is active on `task` or `project`, and it is not approved, or it changed
  after approval.
- A spec is active, and no `craft-spec trace` is recorded, or the last one failed.

What counts as a claim, in plain words:

- `` `done` `` in backticks, which is how `config/workflow.md` writes a state
- `status: done`, `is done`, `now done`, `marked done`, `set to done`,
  `moved to done`
- a line that is only the word `done`
- `Gate A` within 80 characters of `passed`, `green`, `met`, `complete`,
  `satisfied` or `cleared`

"I am done reading the diff" is not a claim and does not block a stop. The hook
allows the second stop attempt, so a block never loops.

### `session_context`

Prints up to eight lines when a craft session or an active spec exists: the
spec title, route, risk, approval state, task progress, next task, and the last
check. Claude Code adds a `SessionStart` hook's output to the context. It prints
nothing in a repository that does not use the workflow, and it never blocks.

---

## The state it reads

State lives in the **host repository**, never in this plugin.

```
<repo>/.claude/craft/
├── session.json     route, spec, session id, checkpoint command, checks with exit codes
├── approval.json    the spec and scenario approvals the developer gave, each with a SHA-256
├── findings.json    adjudicated review findings
├── logs/            full output of every bin/craft-check run
└── archive/         sessions that were ended

<repo>/.claude/specs/
├── ACTIVE           the active spec directory name
└── <dir>/           spec.md, scenarios.md, design.md, tasks.md, log.md
```

`scripts/craft_state.py` is the only module the hooks use to touch these files.
It writes through a temporary file and `os.replace`, so a reader never sees half
a file.

The commands that feed the state:

```bash
bin/craft-spec new --route task --title "Daily withdrawal limit"   # spec + session
bin/craft-approve                                                   # approval of spec.md
bin/craft-check -- docker compose exec web pytest apps/wallet -q
bin/craft-spec trace                                                # criteria → tests
bin/craft-spec status
bin/craft-spec close                                                # end the session
```

`bin/craft-session record-check --command "..." --exit-code N` stays as a manual
fallback for a check that ran where `craft-check` cannot reach.

---

## The kill switch

```bash
CRAFT_HOOKS=off <your command>
export CRAFT_HOOKS=off          # for the rest of the shell session
```

Every hook reads `CRAFT_HOOKS` first, before any other logic, and exits 0 when it
is `off`. Use it when a hook misfires and you need to keep working. Then say
which hook misfired, and on which path.

## How to disable one hook

Open `hooks/hooks.json` and delete that hook's object from the `hooks` array of
its event. Deleting the whole `PreToolUse` or `Stop` key is fine too. The file is
plain JSON, and `bin/craft-doctor` reports whether it still parses.

To disable the whole set, disable the plugin. Do not add a `"hooks"` key that
names `hooks/hooks.json` to `.claude-plugin/plugin.json`: the host loads that
file on its own, and a second reference stops the plugin from loading.

---

## How to check them without a live session

```bash
python3 scripts/craft_selftest.py
python3 scripts/craft_selftest.py --verbose
```

It builds throwaway repositories under the system temporary directory, feeds each
hook synthetic payloads, and asserts every decision. It runs four layers: the
`decide()` functions, the state library, each hook as a real process with real
bytes on standard input, and the `bin/` commands against a throwaway repository.
It exits 0 when every case passes.

```bash
bin/craft-doctor          # standards, skills, agents, commands, hooks
bin/craft-doctor --json
```

`craft-doctor` reports whether `hooks.json` parses and whether every script it
names exists and is executable.

---

## How a hook answers

Read this before you change one.

**Allow is silence.** A hook that allows prints nothing and exits 0. It does
**not** print `permissionDecision: "allow"`. That form bypasses the permission
system and would auto-approve a write the developer would otherwise be asked
about. Silence keeps the normal rules in force.

**Deny says the same thing three ways**, because each one is enough on its own
and the three together survive a change in any single channel:

1. JSON on standard output. For `PreToolUse`:
   `hookSpecificOutput.permissionDecision: "deny"` with
   `permissionDecisionReason`. For `Stop`:
   `hookSpecificOutput.decision: "block"` with `reason`.
2. The same text on standard error.
3. Exit code 2, which blocks on both events whatever the JSON says.

**Every denial names the next step.** A blocked write that does not say what to do
produces an attempt to work around it, and that is worse than no hook at all.

---

## The rules these scripts follow

1. **Fail open, always.** Any exception, missing file, malformed JSON, unreadable
   config or unexpected payload lets the call through. Every entry point is
   wrapped, and every public function in `craft_state.py` returns a safe default
   instead of raising. A hook that crashes must never block work.
2. **Inert unless a craft session is active.** `session.json` absent means every
   hook except `protect_human_owned` returns immediately. `session_context`
   also speaks when a spec is active with no session.
3. **The kill switch is checked first**, before anything else.
4. **Standard library only**, and only `json`, `os`, `sys`, `re`, `pathlib`,
   `fnmatch`, `datetime` and `hashlib`. No third-party package. No import that
   costs time.
5. **No network. No `git`. No write outside `.claude/craft/`.** The hooks only
   read `.claude/specs/`. The `bin/` commands write there.
6. **Fast.** Each hook returns in about 40 ms on this machine, and most of that
   is Python starting up. `craft_selftest.py` prints the four slowest runs and
   warns above 250 ms.

## How paths are matched

`config/paths.json` holds the glob sets. It is the machine mirror of the path
rules that `config/workflow.md` states in prose. **`workflow.md` stays the source
and wins every disagreement**: change it first, then change `paths.json` to
match.

Matching uses `fnmatch`, so `*` crosses a directory separator. Write `*/tests/*`
and `tests/*` as two patterns when you mean both. A glob with no `/` in it is
also matched against the file name alone, so `test_*.py` matches
`apps/wallet/tests/test_limit.py`.

Two of the seven sets are read today: `human_owned` by `protect_human_owned`,
and `tests` by `bin/craft-spec trace`, which uses it to find the test files. The
spec gate needs no glob set: it gates every path outside `.claude/`. Its
test-file check uses the stack's test globs, as `trace` does. The other
five are recorded for a route guard that is not wired yet.

---

## Known limits

- **The spec gate watches the file tools, not the shell.** A `Bash` command that
  writes a file is not gated. The old scenario gate had the same limit.
- **The test-file check matches globs.** A test path the globs miss (a symlinked
  directory, a case difference, a stack deeper than the detector looks) is not
  gated. A source file that matches a test glob (`factories.py`, `ab_test.py`) is
  gated. `.claude/craft/stack.json` is agent-writable and changes the globs.
- **The hook cannot tell who approved.** `bin/craft-approve` records what the
  model runs. The `spec` skill forbids recording an approval the developer did
  not give, and `log.md` keeps every approval with its note.
- **A green check does not expire.** A checkpoint that passed before the last
  code change still counts. Run it again after the last fix.
- **Two Claude sessions in one repository share one `session.json`.** The
  failure direction is a denial, never a false approval.
