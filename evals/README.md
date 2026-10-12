# evals/ — what this plugin claims, measured

This plugin demands tests of everything else. This directory is where it is held
to the same rule.

Each case is a directory: a `prompt.md` holding a request a developer would
really type, and one or more graders under `graders/`. Each case runs three
times with the plugin loaded and three times without it. The report gives `WITH`,
`W/OUT` and **`Δ`**, and `Δ` is the only number that matters. A case that scores
1.00 in both arms proves the base model already does that, and the prose that
claims it is spending tokens for nothing.

**Every run is a real model call on your account.** Read [Cost](#cost) before you
run the suite.

---

## The cases

| Case | What it proves |
|---|---|
| `routes-quick-typo` | A docstring typo takes the cheapest route |
| `quick-spawns-no-agent` | A quick fix spawns no subagent, so it costs one session |
| `routes-task-endpoint` | A new endpoint with a business rule takes `task`, not `quick` |
| `routes-project-migration` | A schema migration forces `project`, whatever the size |
| `routes-promote-money` | A one-line change that touches a balance is promoted, never `quick` |
| `spec-gate-holds` | A spec with acceptance criteria is presented for approval, and no source or test file is written first |
| `omission-block-present` | The "Not tested, and why" block appears |
| `human-owned-refused` | An edit to a `*.human.md` document is refused, and the fragment is reported |
| `no-false-done` | With a checkpoint command that cannot run, the report says `blocked`, never `done` |
| `negative-unrelated` | A request this workflow does not own loads no skill at all |

Three of them measure a hook rather than prose:

- `human-owned-refused` measures `protect_human_owned`.
- `spec-gate-holds` measures `gate_spec`.
- `no-false-done` measures what `verify_gates` corrects. Its
  `no-unproven-done-claim` grader uses the same pattern the hook uses, so the
  eval and the hook agree on what a false claim looks like.

Run the suite before and after you change a hook. The enforcement should show up
in `Δ`.

---

## Run it

From the plugin root:

```bash
claude plugin eval . \
  --trust-plugin \
  --scaffold \
  --allow-tools Write Edit Bash \
  --json results.json \
  --threshold 0.8 \
  --model claude-sonnet-5 \
  --judge-model claude-haiku-4-5 \
  --no-publish \
  --max-cost-usd 20
```

Three flags are not optional for this suite:

- **`--allow-tools Write Edit Bash`.** `Write`, `Edit` and `Bash` are never
  granted by a case's own `allowed_tools`. Without the grant they are removed
  from the session, so `spec-gate-holds` and `human-owned-refused` prove
  nothing: the model could not have written the file even if it wanted to, in
  either arm. `Bash` lets the with-arm run `bin/craft-spec new`, which is what
  shuts the spec gate.
- **`--scaffold`.** `human-owned-refused` needs a real `*.human.md` file in the
  workspace. Its `scaffold.sh` writes one. Without the flag the edit fails
  because the file is absent, not because it was refused, and both arms pass for
  the wrong reason.
- **`--threshold 0.8`.** The default is `1.0`, which fails a suite on one flaky
  run out of thirty.

Every run starts in an empty working directory, so each prompt carries the code
it talks about. `human-owned-refused` is the one case that needs a file on disk.

### CI does not run this suite

`.gitlab-ci.yml` makes no model call. The runner has no `ANTHROPIC_API_KEY` and
no route to the API, so a paid suite could never work there. CI runs
`scripts/validate_evals.py` instead, which reads every case and every grader and
reports the mistakes that would otherwise only show up after a paid run: an
unknown frontmatter key, a pattern that does not compile, a grader whose body is
ignored, a negative `Skill` grader that is silently excluded from the score.

```bash
python3 scripts/validate_evals.py
python3 scripts/validate_evals.py --json
```

It is free, offline and stdlib-only. Run it after you touch a case, and before
you spend money on a real run.

The suite itself is a developer's tool: run it by hand, on a machine that can
reach the API, when you change a hook, a skill, or a routing rule.

### One case, cheaply

```bash
claude plugin eval . --case routes-promote-money --runs 1 --ablation none
```

A single run is noisy. Confirm anything you learn from it at the default three
runs before you believe it.

---

## Cost

**Check your usage limit before a full run.** The run of 2026-09-18 hit the
account's session limit after the first two cases. Every later run ended at turn
1 with `You've hit your session limit`, so its overall score of 0.44 and its
`Δ` of 0.03 measure the limit, not the plugin. Start with one case at one run,
then the full suite when the limit has reset.

A full pass is 10 cases × 3 runs × 2 arms = **60 agent runs**. No case uses an
`llm` or `baseline` grader, so no judge model is called and the
`--judge-model` flag above only covers a grader someone adds later. Every grader
here is `regex`, `tool_used` or `tool_order`, which are computed from the
transcript and cost nothing.

`--max-cost-usd 20` is a ceiling, not an estimate. Once it is spent nothing
further starts and the command exits 2 with partial results.

To halve the cost while you work on a grader, add `--ablation none`. You lose
`Δ`, which is the point of the suite, so use it only while iterating.

---

## How the graders are scored

A case's score is the fraction of its graders that passed, averaged over its
runs. Two rules change what counts:

- A `tool_used` grader whose `tool` is `Skill` is **excluded from the score** in
  a two-arm run, and reported in the with-arm as an indicator. A check like "the
  craft skill fired" can never pass without the plugin, so scoring it would
  push the without-arm toward zero and inflate `Δ`. The `craft-skill-fired` and
  `criteria-skill-fired` graders here are indicators.
- `arm: both` forces a grader to be scored in both arms anyway. Every
  "this must **not** happen" grader carries it: `no-skill-invoked`,
  `no-code-file-written`, `no-code-file-edited`, `no-agent-spawned`,
  `human-owned-file-not-edited`, `human-owned-file-not-overwritten`. Without it
  they would be excluded and the negative cases would measure nothing.
- `arm: with-only` excludes a grader from scoring but keeps it visible.
  `craft-before-spec` carries it, because an ordering between two skill loads
  cannot hold in an arm that has no skills.

## Adding a case

```bash
claude plugin eval init --bare <case-name>
```

Then write the prompt and the graders by hand. Two habits keep the scores
steady:

1. **Prefer `regex`, `tool_used` and `tool_order` over `llm`.** They are free and
   they answer the same way every time. Every grader in this suite is one of the
   three. An `llm` grader asks a model for a verdict, and the verdict moves.
2. **Give each case one grader on the result and one on how Claude got there.**
   Together they tell you whether the answer was right *and* whether this plugin
   is what produced it.

Grader files carry frontmatter and no body. Only `llm` and `baseline` graders
read the body, so a body anywhere else is either ignored or wrong. The grader's
name is its filename.

`results/` is written by every run and is in `.gitignore`. Do not commit it.
