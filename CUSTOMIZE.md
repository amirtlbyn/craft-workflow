# Customizing this workflow

Everything here is plain Markdown. You change behavior by editing files, not by
writing code. Nothing regenerates or compiles on the Claude Code side.

One exception: the Codex CLI mirror (`.agents/skills/`, `.codex/agents/`,
`AGENTS.md`) is generated from `skills/`, `commands/`, and `agents/` by
`bin/craft-sync-codex`. Any change below that adds, removes, or edits a skill,
a command, or an agent needs `bin/craft-sync-codex --write` afterward, or the
Codex side drifts from what you just changed. See "Codex CLI support" below.

## The one file most people edit

`config/workflow.md`. It holds every routing decision:

| Section | Controls |
|---|---|
| §1 Standards | Which documents define "correct code" |
| §2 Routes | How much process each request size gets |
| §2 Risk tier | When `deep-reviewer` (Opus) runs |
| §3 Review routing | Which lens runs on which diff, and on which model |
| §4 Specs | Where specs live on disk, and how the gates derive from them |
| §5 Active skills | Which skills the router loads |
| §6 Verification | The real test, lint, and format commands |
| §7 Overrides | Per-repository rules |

Change a row and the behavior changes. Delete a row and the step stops running.

## Add a stack

Eight stacks ship in `stacks/`: `django`, `fastapi`, `go`, `java`, `node`,
`laravel`, `symfony`, `php`. To add
one, for example Rust:

1. Copy `stacks/go/` to `stacks/rust/` and edit `stack.json`:
   - `detect.any_file`: `["Cargo.toml"]`. `any_contains` for a dependency name.
   - `language` and `priority`: one pack per language wins in a directory.
   - `tests.globs` and `tests.extensions`, and `id_rule`: where a test names
     its criterion ID. Add the language to `TEST_DEFS` in `bin/craft-spec` when
     its test declaration is new to the trace.
   - `checks`: a list of candidates per label (`tests`, `lint`, `format`,
     `types`, ...), the first that applies wins. Conditions: `when_file`,
     `when_any_file`, `when_contains`, `when_script`, `when_dependency`.
   - `paths`: globs for `money`, `auth`, `migrations`, `models`, `views`. They
     feed the rules floor and the lens routing.
   - `toolchain`, `skills`, `standards`, `concurrency.skill`, `lenses`.
2. Write `skills/rust-practices/SKILL.md`, and `standards/rust_standards.ai.md`
   with `##` sections so `bin/craft-std` can read it by section.
3. Write `stacks/rust/lenses.md` with one `## <lens>` section per lens that needs
   stack-specific items.
4. When the stack has its own concurrency model, add an analyzer to
   `ANALYZERS` in `scripts/craft_stack.py` that returns a verdict.
5. Add the skill rows to `config/workflow.md` §5 and the stack to §9.
6. `bin/craft-doctor --skip commands` checks the pack. `python3
   scripts/stack_selftest.py` proves detection, checks, and trace.
7. `bin/craft-sync-codex --write`.

To force a stack in one repository, `bin/craft-stack set <id>`.

The routes, the spec, the spec gate, the discipline skills, and the reviewer
protocol carry no language assumptions. The `*.human.md` standards and the
core lens files are Django's. Every other stack adds its notes beside them.

## Choose the deciders

`config/deciders.json` lists the providers. `bin/craft-decide` writes a
repository's choice to `.claude/craft/deciders.json`. To add a provider that
speaks the OpenAI chat API, add an entry with `type: "openai"`, `base_url`,
`model`, `key_env`, and its privacy fields (`trains_on_data`,
`send_request_text`). Only `https://`, or `http://` to this machine.

## The mod

`hooks/mod/craft.tsx` is a Claude Code mod. `.claude-plugin/plugin.json`
names `hooks/mod.json`, which names the module. Its options (`/plugin` →
craft-workflow): `status` (`top`, `prompt`, `both`), `auto_check`, and
`gate_question`. After a change: `claude plugin validate .`, `claude plugin
test`, and `claude --plugin-dir .` to see it. Keep every `$` call in
`craft.tsx`; `view.ts` holds pure helpers only.

## Add your own skill

```
skills/<your-skill>/SKILL.md
```

```markdown
---
name: your-skill
description: "One sentence saying when to load it. Write it as a trigger, not a summary — this is what the model matches on."
---

# your-skill

...
```

Then add a row to `config/workflow.md` §5 so the router knows when to load it,
and run `bin/craft-sync-codex --write` so Codex CLI users get it too.

## Remove a skill you do not want

Delete its directory and its row in §5. Then check nothing references it:

```bash
rg -n '<skill-name>' skills agents commands config
```

The workflow degrades cleanly — a missing optional skill is skipped, never fatal.
Run `bin/craft-sync-codex --write` afterward — otherwise `craft-doctor` reports
the now-orphaned generated file under its `codex` group.

## Change the review

Review has two parts. The **agents** (`agents/reviewer.md`,
`agents/deep-reviewer.md`) set the model and the order of work. The **lenses**
(`skills/review-protocol/lenses/<lens>.md`) set the domain, the severity
ceiling, the confidence threshold, what to read, and the checklist.

To make review cheaper, change `model:` in `agents/reviewer.md`, or raise a
lens's confidence threshold. To make it stricter, lower the threshold. To send
more changes to Opus, widen the risk-tier rule in `config/workflow.md` §2.

To add a lens:

1. Write `skills/review-protocol/lenses/<name>.md`: ceiling, confidence, what it
   reads, and a checklist.
2. Add a row to the Lens table in `config/workflow.md` §3 saying when it runs.
3. Add it to the lens table in `skills/review-protocol/SKILL.md`, so the other
   lenses know it owns that domain.
4. Run `bin/craft-sync-codex --write`, then `bin/craft-doctor --skip commands`.
   The doctor fails when a routed lens has no file.

**Step 3 matters.** One defect belongs to one lens. Skipping it produces
duplicate findings.

To go back to one agent per lens for a single review, say "full review". The
main session spawns `reviewer` once per routed lens, in parallel.

## Change the spec template

The templates are in `skills/spec/templates/`. `bin/craft-spec new` fills
`{title}`, `{key}`, `{route}`, `{date}`, and `{checkpoint}`. Keep the
"Acceptance criteria" heading and the `| ID |` first column: `bin/craft-spec
trace` reads them. Keep state out of `spec.md`, because every change to it
closes the gate.

## Per-repository rules without forking

Put `.claude/craft.md` in the host repository. It wins over `config/workflow.md`.
Use it for repository-specific route rules, extra checklist items, or a different
test command.

## Suppress a false positive

When a reviewer repeatedly raises something your team has decided is fine, record
it in the host repository's reviewer-memory file, conventionally
`aidocs/reviewer-memory.md`:

```markdown
### L-<short-id>
kind: suppress
applies-to: <path or glob>
rule: <what not to flag, and what still counts as a real defect>
why: <the decision behind it>
source: <where this was decided, and when>
```

Reviewers read it and honor `suppress` rules.

## Codex CLI support

Claude Code discovers this plugin through `skills/`, `commands/`, `agents/`,
and the global `CLAUDE.md`. Codex CLI has no equivalent plugin system, so
`bin/craft-sync-codex` generates a Codex-native mirror instead:

| Claude Code source | Generated for Codex |
|---|---|
| `skills/<name>/SKILL.md` | `.agents/skills/<name>/SKILL.md` |
| `commands/<name>.md` | `.agents/skills/<name>/SKILL.md` (skipped when the name collides with an existing skill) |
| `agents/<name>.md` | `.codex/agents/<name>.toml` |
| (this repository, for a contributor working on it) | `AGENTS.md` |

Run `bin/craft-sync-codex --write` after any change to `skills/`, `commands/`,
or `agents/`. Run `bin/craft-sync-codex` with no flag to check whether the
generated files are stale — `craft-doctor`'s `codex` group does this for you.
Never hand-edit a generated file. The next `--write` overwrites it.

**Wiring Codex to use this plugin.** Codex discovers skills at
`~/.agents/skills/<name>` (user-level, every repository) or
`<repo>/.agents/skills/<name>` (one repository), and subagents the same way
under `.codex/agents/`. There is no Codex equivalent of "enable this plugin
globally" the way Claude Code has. Symlink or copy this repository's
generated `.agents/skills/*` and `.codex/agents/*` entries into whichever of
those locations fits how you want to use the plugin.

**What is not covered yet.** The hooks — the spec gate, `*.human.md`
protection, the done/Gate-A verification at session end, and the session-start
status — run only under Claude Code and ZCode. The `bin/` commands work under
Codex too. Codex's exact hook
payload schema cannot be verified from documentation alone, so
`.codex/hooks.json` is a separate, later piece of work, checked against a
real Codex session rather than assumed from docs. A Codex session can follow
the same workflow as prose, but nothing blocks it from skipping a gate the
way the Claude Code hooks do.

## Keep the standards current

```bash
./scripts/sync-standards.sh /path/to/source-repo
```

It copies the four files verbatim and shows a diff. It never edits them.

## What you should not change

- The **ownership banners** in `standards/*.human.md`. Those files are
  human-owned. An agent reports a suggested change. It never applies one.
- The **spec gate**, unless you want agents writing code before you agreed what
  it should do. That gate is the point. `CRAFT_HOOKS=off` turns it off for one
  command when you need to.
- The **hash binding** of the approval. It is what makes a quiet edit to an
  approved spec visible.
- The **adjudication step** in `review-protocol`. Removing it sends raw reviewer
  output, including false positives, straight to the developer.
