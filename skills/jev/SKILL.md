---
name: jev
description: "Optional fast routing decisions from AI deciders: Jev (TypeSafe's System One model on OpenRouter), free tiers (OpenRouter's free router, Groq, Gemini, Cerebras, Mistral, GitHub Models, Cloudflare), local models (Ollama, LM Studio), or Claude Haiku, one at a time or as a council. Use it when the user runs /jev or /decide, asks to let a decider pick the route, risk tier, implementer model, skills, or review lenses, asks for free or local deciders, or when the deciders are on and the craft router needs one of those decisions."
---

# jev — typed decisions instead of Claude's judgement, when you want them

Jev is a decision model. It answers typed questions with calibrated
probabilities in about 0.7 to 1.3 seconds in practice, and costs about $0.04 per million
input tokens with free output. It never writes text and **it does not call
tools**. In this workflow it answers the routing questions, and Claude acts on
the answers.

Jev is **off by default**. When it is off, nothing in this skill runs, and the
workflow routes with Claude's own reading of `config/workflow.md`.

## Every decider, not only Jev

Since 0.7, Jev is one of several **deciders**. `bin/craft-decide` chooses them,
and `bin/craft-jev decide` asks whichever are chosen. The rules floor, the
confidence threshold, and fail-open apply to all of them.

```bash
<plugin root>/bin/craft-decide status                  # every provider: free? local? may keep prompts? ready?
<plugin root>/bin/craft-decide use ollama,groq,jev     # mode first: the first that answers
<plugin root>/bin/craft-decide council jev,groq,ollama # mode council: ask together, average them
<plugin root>/bin/craft-decide test all                # one tiny question to each
<plugin root>/bin/craft-decide discover openrouter-free --free
<plugin root>/bin/craft-decide set groq model openai/gpt-oss-20b
```

| Provider | Cost | Privacy | Key |
|---|---|---|---|
| 🦉 `jev` | about $0.04 per million input tokens | `data_collection: deny` | `OPENROUTER_API_KEY` |
| 🆓 `openrouter-free` | free (`openrouter/free`) | the upstream may log: no request text by default | `OPENROUTER_API_KEY` |
| ⚡ `groq` | free tier | no retention by default | `GROQ_API_KEY` |
| 💎 `gemini` | free tier | may train: no request text by default | `GEMINI_API_KEY` |
| 🧠 `cerebras` | free tier | no training | `CEREBRAS_API_KEY` |
| 🌬️ `mistral` | free Experiment plan | may log: no request text by default | `MISTRAL_API_KEY` |
| 🐙 `github` | free, rate-limited | Microsoft terms | `GITHUB_TOKEN` |
| ☁️ `cloudflare` | free daily allowance | no training | `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` |
| 🦙 `ollama`, 🖥️ `lmstudio` | free | 🔒 nothing leaves the machine | none |
| ✳️ `claude` | your plan's usage | Anthropic's terms | none: `claude -p --safe-mode` |

**Which to pick.** For a free setup, `council ollama,groq,openrouter-free`. For
the most private one, `use ollama`. For the most accurate one, `use jev` or
`use claude`. A council's confidence is the members' average probability of the
winning choice, so a split council is undecided, and you decide with
`config/workflow.md` §2, never below the floor.

**Approval of tool calls** asks only `approve_providers` (default `jev`).
Widening it is the developer's decision: `bin/craft-decide approve-with
<providers>`, typed by them.

## The switch

```bash
<plugin root>/bin/craft-jev on        # this repository only
<plugin root>/bin/craft-jev off
<plugin root>/bin/craft-jev status
<plugin root>/bin/craft-jev test      # one tiny paid call: answer, latency, cost
```

`CRAFT_JEV=on` or `CRAFT_JEV=off` in the environment overrides the switch.

To point this repository at another endpoint or model, without editing plugin
files that an update would overwrite:

```bash
<plugin root>/bin/craft-jev set endpoint https://<host>/api/alpha/decisions
<plugin root>/bin/craft-jev set model typesafe/jev-1.13
<plugin root>/bin/craft-jev unset endpoint        # back to config/jev.json
```

`CRAFT_JEV_URL` and `CRAFT_JEV_MODEL` override both for one shell. A chosen
endpoint is used alone: the fallback endpoints apply only to the default. The
OpenRouter key comes from `OPENROUTER_API_KEY` or from
`~/.config/craft-workflow/openrouter.key`. Never write the key into the
repository, a spec, a log, or this conversation's output.

## What Jev decides

| Stage | When | Questions | What Claude does with the answer |
|---|---|---|---|
| `route` | Step 2 of the `craft` router, before the route line | `route`, `risk_high`, `implementer_model`, `skill_*` | Uses the route, the risk tier for the spec header, the model for `coder`, and the skills to load |
| `review` | Before Gate B | `risk_high`, `lens_logic`, `lens_security`, `lens_query` | Spawns `reviewer` and `deep-reviewer` with exactly the lenses it lists |

The questions and their criteria live in `config/jev.json`. Edit them there.

## How to use a decision

1. Run the stage. On `route`, pass the developer's request in their words:

   ```bash
   <plugin root>/bin/craft-jev decide --stage route --request "<the request>"
   <plugin root>/bin/craft-jev decide --stage review --base <review base>
   ```

2. Read the output. Every value is already combined with the **rules floor**:
   path globs from `config/paths.json` and keywords for money, auth,
   migrations, concurrency, and integrations. Jev can raise a value above the
   floor. It can never lower one.
3. Apply it:
   - **route** — state it in the route line and name Jev as the source:
     `Route: task — Jev 0.91, floor task (money word "withdraw").` When the
     output says `UNDECIDED` or `rules only`, decide with `config/workflow.md`
     §2 as usual, never below the floor it prints.
   - **risk** — write it into the spec header. `high` from either source wins.
   - **implementer** — on the project route, pass it as the `model` of the
     `coder` subagent when the host lets you choose one. On `task` and `quick`
     the main session implements, and the value is only advice.
   - **load skills** — load the listed skills. You may load more when the work
     shows a need. Do not skip a skill that `config/workflow.md` §5 requires.
   - **lenses, reviewer, deep-reviewer** — spawn exactly these. You may add a
     lens when the diff shows a need. Never remove one.
4. The developer's words win over Jev. "use route X" is final.

## When Jev fails

`decide` never blocks the work. A missing key, a timeout, an HTTP error, or a
malformed answer gives `rules only — Jev failed: <why>`, and the rules floor
still applies. Say in one line that Jev was not reached, then continue with
Claude's own routing. Do not retry in a loop: the command already retries once
with backoff.

## Tool-call approval — `/jev approve on`

A separate, second switch lets the `jev_approve` hook approve tool calls that
would otherwise prompt the developer. It needs Jev on as well. It is the
developer's choice alone: never run `craft-jev approve on` unless the developer
asked for it in this conversation, and never to get past a prompt.

What it does, in order:

1. Nothing in `bypassPermissions` or `plan` mode.
2. Nothing when `protect_human_owned` or the spec gate would deny the call.
3. Denies commands on `deny_patterns` (`rm -rf /`, `mkfs`, `curl | sh`).
4. Stays silent, so Claude Code asks as usual, for `ask_patterns` and
   `ask_path_patterns`: git push and history rewrites, installs, network tools,
   credentials, databases, `python -c` and other inline code, deploys, and any
   command that changes this workflow's gates (`craft-approve`,
   `craft-session record-check`, `craft-jev on|approve|set`, `CRAFT_HOOKS=off`).
5. Otherwise asks Jev. It approves only a verdict of `allow` at confidence 0.9
   or more, with both "irreversible" and "sends data out" below 0.3.
   Anything else, a timeout, or an error means silence and the normal prompt.

When a call you expected to run is prompted instead, that is the design. Do not
rephrase the command to get it approved. Each decision is logged in
`.claude/craft/jev-approvals.jsonl`.

## What leaves the machine

The request text (unless `--no-request-text`), the changed paths, and line
counts. Never file contents. The request asks providers not to collect data.
When a request contains a secret or customer data, run `decide` with
`--no-request-text`.

Every decision is appended to `.claude/craft/jev-log.jsonl` without the request
text: the stage, the values, the source, the latency, and the cost. Read it to
check whether Jev and the developer agree before you trust it with more.
