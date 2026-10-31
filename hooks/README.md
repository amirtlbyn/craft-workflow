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
| `scripts/gate_spec.py` | `PreToolUse` on `Write\|Edit\|MultiEdit\|NotebookEdit` and `Bash` | On `task` and `project`, no source or test file is written until the developer approves `spec.md` at its current SHA-256, and no test file until `scenarios.md` is approved too. A Bash write form counts as a write |
| `scripts/gate_bash_after.py` | `PostToolUse` and `PostToolUseFailure` on `Bash` | `approval.json` changed by a Bash call is put back. While the spec gate is shut, a file that a Bash call changed is reported with the one command that restores it |
| `scripts/agent_gate.py` | `PreToolUse` on `Agent\|Task` | Records each reviewer spawn in `session.json` `spawns`, so Gate B counts a review round only when a reviewer it names was really spawned. It never denies |
| `scripts/protect_approval.py` | `PreToolUse` on `Bash` and `Write\|Edit\|MultiEdit\|NotebookEdit` | Only the developer approves and turns hooks off: no tool call runs `craft-approve`, sets `CRAFT_HOOKS`, writes `.claude/craft/` or `.claude/specs/ACTIVE`, runs a `bin/` subcommand that changes trusted state, puts an off-switch in `.claude/settings*.json`, disables the plugin, or writes the plugin's own files |
| `scripts/protect_human_owned.py` | `PreToolUse` on `Write\|Edit\|MultiEdit\|NotebookEdit` | A `*.human.md` document cannot be edited by an agent |
| `scripts/verify_gates.py` | `Stop` | A claim of `done` or Gate A needs a green checkpoint, an approved spec, and a green trace. A stop is refused up to three times while a file that a Bash call changed with the gate shut is not restored |
| `scripts/session_context.py` | `SessionStart` | A new session sees the active spec, its state, and its next task |

### `gate_spec`

Denies a `Write`, `Edit`, `MultiEdit`, or `NotebookEdit` call. It is inert
unless **all** of these hold:

1. `<repo>/.claude/craft/session.json` exists.
2. Its `route` is `task` or `project`. On `quick` the hook does nothing.
3. The target path is inside the host repository and outside `<repo>/.claude/`.
   Spec files, craft state, and files outside the repository are never gated.
4. The active spec is not `approved`: there is none, it was never approved, or
   `spec.md` changed after its approval (`stale`).

The denial names the state and the way through: `bin/craft-spec new`, then the
developer's approval. It asks the developer to type
`! "<plugin root>/bin/craft-approve"` in the prompt, or to press `a` on the
board. It never tells Claude to run `craft-approve`.

**Bash.** On a `Bash` call the hook reads the command text with
`craft_state.bash_effects()`. It finds the common write forms: `>`, `>>`, `tee`,
`sed -i`, `perl -i`, `cp`, `mv`, `rm`, `touch`, `truncate`, `ln`, `install`,
`dd of=`, `patch`, `git apply`, `git checkout --`, `git restore` (not
`--staged` alone), and Python, Node, Perl, or Ruby code in `-c`, `-e`, or a
heredoc that writes a file. It drops comments, and it follows `bash -c`,
`eval`, `if`/`then`, `{ ... }`, `sudo`, `env`, and `xargs`. A write whose path
it cannot see counts as a write to the current directory: a pipe into `sh` or
`python3`, `xargs rm`, `find -delete`, `os.system`, `subprocess`,
`child_process`, `patch`, or `git apply`. A path that starts with a variable
that is not set (`"$TMPDIR/x"`) has no known place, so the after-check covers
it. A variable later in a relative path (`app/$NAME.py`) stays in the
repository. A `$` inside single quotes is literal. After `cd X`, a command
joined by `&&` or `|` runs in X only. After `;`, `||`, or inside parentheses,
the `cd` may not have happened, so a relative path is checked against both
directories. Symlinks are resolved. The hook denies the call when a target is inside the
repository and outside `.claude/`. A read, a write under `.claude/`, to
`/dev/null`, or outside the repository is allowed. A command whose text cannot
be split into words (an open quote) is denied when it holds a redirection or a
command that can write a file.

Before an allowed Bash call in a craft session, on any route, the hook stores a
snapshot in `.claude/craft/snapshots/<tool use id>.json`: the content of
`approval.json`, and, while the gate is shut, the changed files of the
repository (`git status`, with a SHA-256 of each, or size and time above 1 MB)
and which of them are untracked. Each tracked changed file up to 1 MB gets a
copy in `.claude/craft/backups/<sha256>`, written once, at most 20 MB per call.
An untracked file is never copied: it may hold a secret. Snapshot files older
than an hour are removed.

A file that a Bash call changed while the gate was shut may be written again
only to restore it: `git checkout -- <path>` or `git restore` from the index or
HEAD for a file that was clean, `rm <path>` for a file that was absent,
`cp <its backup> <path>` for a tracked file that held uncommitted work, or a
`Write` whose content is the content before the call. `Edit` is denied on it.

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

### `gate_bash_after`

The backstop for what the text checks cannot see. It reads and removes the
snapshot that `gate_spec` stored for this tool call. It runs on `PostToolUse`
and on `PostToolUseFailure`, so a call that exits non-zero or times out is
checked too. When both events reach it for one call, the second finds no
snapshot and does nothing.

- **approval.json.** The snapshot holds its bytes and its mode. When it changed
  during the call, by any route (a glob, a variable, `find -exec`, a symlink,
  `chmod`, bytes that are not UTF-8), the hook writes back its bytes and mode
  from before the call, or deletes a file the call created, and reports
  "forged approval reverted". A file that cannot be read now counts as
  changed. When the earlier file itself could not be read, a changed file is
  deleted, because its old bytes are unknown. The developer's `!` command and the board's `a` key are
  not Bash tool calls, so they never reach it. An approval the developer gives
  on the board while a long Bash call runs is reverted too, and the report says
  to approve again.
- **Source files, while the gate is shut.** It runs `git status` again. Each
  file inside the repository and outside `.claude/`, not ignored by git, that
  changed during the call goes into `session.json` `gated_writes`, with how it
  was before (clean, absent, deleted, tracked with uncommitted work and its
  backup, or untracked), the time, and the spec. The report gives the one
  command that restores each file: `git restore --source=HEAD --staged
  --worktree -- <path>` for a clean file, so a staged copy is reset too, `rm`
  for an absent one, `cp <backup> <path>` for uncommitted work. A file with
  uncommitted work is never restored with `git checkout`. The report also
  says: if the developer edited the file during the command, tell the
  developer instead. A file with no backup (untracked, over 1 MB, or past the
  20 MB a call copies) is reported, and it never refuses a stop.
  The hook never restores a source file itself.

A restored file leaves `gated_writes`. A record counts only while its spec is
active and no spec approval came after it, so a later spec delta never asks to
undo approved work. When the gate is open, `gated_writes` is cleared. A backup
that no record names is deleted when a record leaves. Outside a git work tree
there is no file check.

### `protect_approval`

Runs in every repository, with or without a craft session. It denies:

- a Bash command whose text holds `craft-approve` when any command in it is not
  read-only. The read-only commands are `rg`, `grep`, `cat`, `less`, `head`,
  `tail`, `wc`, `ls`, `file`, `stat`, `sed -n`, `git log|show|diff|grep|blame|status`,
  `echo` and a few more, with no redirect except to `/dev/null`. So
  `rg craft-approve skills/` is allowed, and `bin/craft-approve`,
  `eval 'bin/craft-approve'`, `echo bin/craft-approve | sh`, and
  `if true; then bin/craft-approve; fi` are denied. To write a file that names
  it, use the `Write` tool.
- a Bash command that assigns `CRAFT_HOOKS`
- a `Write`, `Edit`, `MultiEdit`, or `NotebookEdit` call, or a Bash write form,
  whose target is `.claude/craft/` or under it, symlinks resolved. This covers
  `approval.json`, `session.json`, `findings.json`, `reviews.json`, and a copy
  into the directory. The `bin/` commands still write there, run as programs.
  The rule is strict, as for `craft-approve`. It applies when a craft session
  is active or the text names `.claude`. When one pipeline names a craft path
  (`.claude/craft`, `craft/session.json` and the other state files,
  `specs/ACTIVE`), directly or through a variable set to one, and runs a
  command that is neither read-only (`jq` counts), nor an honest `bin/` program
  run (`craft-check`, `craft-spec status|trace|lenses`, `craft-session
  status|record-finding|record-review|finding --state fixed`,
  `craft-scenarios`, `craft-stack`, `craft-std`, `craft-ui-state`), nor
  `git add`, nor the `cp <backup> <path>` that a restore command gives, it is
  denied. So a Python one-liner that edits `.claude/craft/session.json`, or
  `F=.claude/craft/session.json; sed -i ... $F`, is denied, and
  `jq . .claude/craft/session.json` is allowed. A file named `session.json`
  elsewhere in the repository is not a state file. To read state, use `cat`,
  `jq`, or `bin/craft-spec status`.
- a write to `.claude/specs/ACTIVE`. `bin/craft-spec new` still sets it, as a
  program
- `CRAFT_HOOKS`, `disableAllHooks`, or `craft-workflow` set to `false` in
  `enabledPlugins`, written to a `.claude/settings.json` or
  `.claude/settings.local.json`, by a write tool or by Bash. Content that
  parses as JSON is read as JSON, and `\uXXXX` escapes are decoded. A
  settings file written by `cp`, `mv`, `tee`, or the like is denied, because
  the command does not show its content
- `claude plugin disable`, `uninstall`, or `remove`, and `claude plugin
  marketplace remove`, also after `env`, `time`, or `nice`
- a `bin/` subcommand that changes trusted state on Claude's behalf:
  `craft-session start` that changes a `task` or `project` route;
  `craft-session end` or `craft-spec new` while a file a Bash call changed with
  the gate shut still blocks the stop; `record-check` by hand, through
  `craft-session` or `scripts/craft_state.py`; `craft-session finding ID
  --state` with any state but `fixed`. Each denial names the `!` line or the board key
  the developer uses instead. `craft-check` records a check as a program and
  stays allowed, and `finding ID --state fixed` stays allowed
- a write under the plugin root, when the plugin root is outside the
  repository. When the repository is the plugin itself, this rule is off.
- a Bash command whose text cannot be split into words, when it holds one of
  the words this hook looks for. This is a decision on unreadable text, not an
  error path: an exception inside the hook still allows the call.

The denial for `craft-approve` prints the exact
`! "<plugin root>/bin/craft-approve"` line for the developer. A `!` command
from the developer does not reach the hook. A commit or tag message, a pytest
`-k` or `-m` selector, and the text of `echo` or `printf` not piped into a
shell are data, so `git commit -m 'document craft-approve'` is allowed. A Bash
command that holds none of `craft`, `CRAFT_HOOKS`, `disableAllHooks`,
`approval.json`, `plugin`, `settings`, or `ACTIVE` costs one regular
expression search.

### `protect_human_owned`

Denies a write whose target matches the `human_owned` globs in
`config/paths.json`, which today is `*.human.md`. This is the one hook that runs
with no craft session. Ownership is a property of the file, not of the session.

### `verify_gates`

Blocks the `Stop` when the final assistant message claims `done` or claims Gate A
passed, and one of these is true:

- `session.json` holds no check that exited 0. When the session names a
  checkpoint command, only a green check whose command equals it counts
  (whitespace collapsed; `pytest apps -q -k one` is not `pytest apps -q`).
- The newest matching check is stale. `bin/craft-check` records a fingerprint of
  the tree with each check: a SHA-256 over the content of every tracked and
  untracked, non-ignored file outside `.claude/`. The Stop hook compares it
  with the tree now. Committing the tested code does not change it. A check
  with no fingerprint (not a git work tree, or recorded before 0.10.0) is
  current. Git runs only in `craft-check`, this hook, and `craft-ui-state`.
- A spec is active on `task` or `project`, and it is not approved, or it changed
  after approval.
- A spec is active, and no `craft-spec trace` is recorded, or the last one failed.

It also blocks any stop, with or without a claim, while the spec gate is shut
and a file in `gated_writes` still differs from its content before the Bash
call that changed it. The block names each file and its restore command. It
does not stop at `stop_hook_active`: it refuses up to three stops in a row, and
the fourth goes through with a warning to the developer. The count starts again
when a stop is allowed. When the gate is open again, it clears `gated_writes`.

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
├── session.json     route, spec, session id, checkpoint command, checks with exit codes,
│                    gated_writes and the Stop refusal count while the spec gate is shut
├── approval.json    the spec and scenario approvals the developer gave, each with a SHA-256
├── findings.json    adjudicated review findings
├── logs/            full output of every bin/craft-check run
├── snapshots/       the state before one Bash call, one file per tool call, kept up to an hour
├── backups/         copies of files with uncommitted work, named by SHA-256
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
bin/craft-approve                                                   # approval of spec.md, by the developer
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
which hook misfired, and on which path. Only the developer sets it, in the
developer's own environment. `protect_approval` denies a Bash command from
Claude that assigns it.

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
   hook except `protect_human_owned` and `protect_approval` returns
   immediately. `session_context` also speaks when a spec is active with no
   session.
3. **The kill switch is checked first**, before anything else.
4. **Standard library only**, and only `json`, `os`, `sys`, `re`, `pathlib`,
   `fnmatch`, `datetime`, `hashlib`, `shlex` and `subprocess`. No third-party
   package. No import that costs time.
5. **No network. No write outside `.claude/craft/`.** The hooks only read
   `.claude/specs/`. The `bin/` commands write there. git runs read-only:
   `status`, `ls-files`, and `cat-file`. It runs only while a craft session on
   `task` or `project` has the spec gate shut, on a Bash call or a restoring
   `Write`, and at Stop when `gated_writes` is not empty.
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

- **The Bash check reads text, not a shell.** It finds the common write forms
  only. A form it misses (a script that writes, an alias, a renamed binary)
  runs, and `gate_bash_after` reports the changed files after the call. Outside
  a git work tree there is no after-check for source files. The test-file check
  (scenarios) applies to the file tools only.
- **The unrestored-file refusal ends after three stops.** The fourth stop goes
  through with a warning, so a block never loops forever.
- **Not a defence against a determined script.** The hooks run as the same OS
  user as Claude, so code Claude runs can rewrite what they trust. They stop a
  well-meaning model's shortcuts and make tampering visible. Writes from a
  background or delayed process, a script that rewrites the snapshots, and
  unusual routes to disable the plugin (`npx claude ...`, the plugin registry)
  are accepted limits.
- **The test-file check matches globs.** A test path the globs miss (a symlinked
  directory, a case difference, a stack deeper than the detector looks) is not
  gated. A source file that matches a test glob (`factories.py`, `ab_test.py`) is
  gated. `.claude/craft/stack.json` changes the globs. Only `bin/craft-stack`
  writes it: `protect_approval` denies a tool write under `.claude/craft/`.
- **The hook cannot tell who approved.** `protect_approval` denies the forms it
  can read, and `gate_bash_after` puts `approval.json` back after any Bash call
  that changed it. A renamed copy of `craft-approve` run by a script still
  writes `approval.json`, and the after-check undoes it. `log.md` keeps every
  approval with its note.
- **Settings are read as written.** A settings change made through a variable
  or a script is not read before the call.
- **A green check expires when file content changes.** A check recorded outside
  a git work tree, or before 0.10.0, has no fingerprint and never expires.
- **The fingerprint is taken after the run.** Taking it before would make a file
  the tests create a permanent stale loop. Edits inside submodules and nested
  repositories are not seen. One deadline of about 4 seconds covers the
  fingerprint, and another of 4 seconds the lens floor at Stop; past it, it is skipped for that path or `None`, and the check
  stays current.
- **A checkpoint counts only from the repository root, and only its newest run.**
  A run from a subdirectory (`--cwd`, or a Bash cwd that moved) is recorded with
  its `cwd` and never counts. A red run after a green one on the same tree
  refuses the claim. An environment prefix such as `PYTEST_ADDOPTS` can narrow a
  run; that is deliberate tampering and a non-goal.
- **A stale claim is refused once per stop.** `stop_hook_active` lets the next
  attempt through, as for every claim block.
- **Two Claude sessions in one repository share one `session.json`.** The
  failure direction is a denial, never a false approval.
