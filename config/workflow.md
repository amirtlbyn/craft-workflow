# workflow.md — the one file you edit to make this workflow yours

Everything in this plugin reads its routing from this file. Change a row, and the
behavior changes. Delete a row, and the step stops running. You do not need to
edit any skill or agent to customize the workflow.

Claude reads this file whenever the `craft` skill loads. Keep the table shapes.
The text in each cell is free-form.

**The workflow is spec-driven.** On `task` and `project`, a written spec is the
source of truth. The developer approves the spec before any code or test is
written. Code, tests, and review are checked against the spec. The gates in §4
are derived from the spec, not invented at the end.

---

## 1. Standards — what "correct code" means here

Every skill and reviewer reads these. Paths resolve against the plugin root.
Replace them with your own documents to retarget the whole workflow.

| Role | Path | Editable by agents |
|---|---|---|
| Python language style | `standards/python_code_style.ai.md` | Yes (rename to `.human.md` to own it) |
| Framework and layering | `standards/django_standards.ai.md` | Yes (rename to `.human.md` to own it) |
| Implementation mechanics and tests | `standards/implementation_standards.ai.md` | Yes (rename to `.human.md` to own it) |
| Engineering standards | `standards/technical_standards.ai.md` | Yes |
| Developer English | `skills/asd-ste100/SKILL.md` | Yes |

**Per stack (§9).** The four documents above are the Django stack's. Every other
stack adds its own standard, named in its `stacks/<id>/stack.json`:
`fastapi_standards.ai.md`, `go_standards.ai.md`, `java_standards.ai.md`,
`node_standards.ai.md`. They are bot-maintainable until a team renames one to
`.human.md`. `technical_standards` TS-1 to TS-5 apply to every stack that owns a
database.

**Read sections, not whole files.** `bin/craft-std --list` prints every section
of every standard with its size and first sentence. Pull only the sections a
change needs:

```bash
bin/craft-std --list                          # every section, one line each
bin/craft-std python_code_style Naming "Type annotations"
bin/craft-std technical TS-1
```

For developer English, read `skills/asd-ste100/references/card.md` (one page).
Load the full `asd-ste100` skill only to rewrite a long document.

**Optional host-repository documents.** Read them when the repository has them.
Skip them silently when it does not. Never fail because one is absent.

| Purpose | Conventional path |
|---|---|
| Cross-app change-risk checklists | `aidocs/INVARIANTS.human.md`, `<dir>/INVARIANTS.human.md` |
| Known-bug register | `aidocs/ISSUES.human.md` |
| Review routing and financial-safety checks | `aidocs/code_review_playbook.ai.md` |
| Test selection | `aidocs/test_selection.ai.md` |
| Reviewer suppressions | `aidocs/reviewer-memory.md` |
| Per-directory orientation | `<dir>/README.ai.md` |

---

## 2. Routes — how much process a request gets

Pick the cheapest route that fits. The `craft` skill classifies the request,
states the route and the reason, and proceeds. Say "use route X" to override.

| Route | Use it for | Spec | Implementer | Review |
|---|---|---|---|---|
| **quick** | Typo, comment, rename, import, config value, one-line fix with a known cause | None | Main session, inline | None. Gate A tools only. Say "review it" to add the `style` lens |
| **task** | One merge request. A scoped feature or bug fix with no design question | `spec.md` + `tasks.md` | Main session, inline | One `reviewer` pass. `deep-reviewer` too when the spec says `Risk: high` |
| **project** | Multi-session work, cross-app change, anything needing a design | `spec.md` + `design.md` + `tasks.md` | `coder` per session, from the spec | The same, once per session |

**Classification rules.** Any one of these forces **project**: a schema migration,
a change to money or the ledger, a new external integration, a new permission or
authentication path, work that spans more than two applications, or an estimate
above one working session.

Any one of these forces **project** as well: changing a system's concurrency
model, such as WSGI to ASGI, a sync FastAPI service to async drivers, MVC to
reactive, or a first worker pool in a Node service. The `concurrency` skill
decides what counts as a change of model.

Any one of these forces at least **task**: new business logic, a new endpoint, a
new background task (Celery, a queue consumer, a worker goroutine), a changed
contract, new concurrent code for throughput, or a bug fix that needs a
regression test.

Everything else may be **quick**.

**Never let quick touch:** money, authentication, authorization, migrations,
concurrency, or an externally visible contract. Promote to task instead.

**Risk tier.** Every spec states `Risk: low` or `Risk: high`. It is `high` when
the change touches money, authentication, authorization, a migration,
concurrency, or an external integration. Otherwise it is `low`. The risk tier
decides the review in §3, not the route.

---

## 3. Review routing — which lenses run, and on which model

Reviewers cost money. One reviewer pass reads the diff once and applies every
lens the diff earns. The lens files live in `skills/review-protocol/lenses/`.

| Reviewer | Model | Runs when | Lenses it applies |
|---|---|---|---|
| `reviewer` | sonnet | Every `task` and `project` review | The routed lenses below. On `Risk: high`, every routed lens except `logic` and `security` |
| `deep-reviewer` | opus | Only when the spec says `Risk: high` | `logic` and `security`, limited to the spec's invariants and the paths that carry them |

| Lens | Runs when the diff touches |
|---|---|
| `spec` | Always, on `task` and `project`. Every acceptance criterion is implemented and tested, nothing outside the spec was built, and every non-goal holds |
| `style` | Always. Naming, developer English, docstrings, the stack's idiom. Formatting and import order belong to the Gate A tools, not to this lens |
| `logic` | Business logic, money, state transitions, transactions, concurrency for correctness, tests, migrations |
| `security` | Entry points (views, routers, handlers, controllers), serializers and DTOs, permissions, authentication, tokens, secrets, raw SQL, deserialization, file upload, outbound URLs, admin actions |
| `query` | Models, entities, repositories, querysets, ORM queries, raw SQL, migrations |
| `concurrency` | Concurrent code for throughput: `async def`, `await`, `gather`, `TaskGroup`, `go` statements, channels, `errgroup`, executors, `CompletableFuture`, reactive types, `Promise.all`, worker pools, threads |

**Every lens has stack notes.** The lens files are written for Django first.
For another stack, the reviewer also reads `bin/craft-stack lens <lens> --paths
<changed paths>`, which prints that stack's section of `stacks/<id>/lenses.md`.

**Re-review is a delta.** After fixes, re-run only the reviewer that raised a
Confirmed Critical or High finding, only on the diff since the review, with the
findings it must verify. A Medium or Low fix needs the Gate A tools, not a
re-review.

**Parallel mode.** When the developer asks for a full review, spawn `reviewer`
once per routed lens, in parallel. It costs more and gives each lens a fresh
context.

---

## 4. Specs on disk

Specs live in the **host repository**, not in this plugin. `bin/craft-spec new`
creates the directory from the templates in `skills/spec/templates/`.

```
<repo>/.claude/specs/
├── ACTIVE                       # one line: the active spec directory name
└── <YYYY-MM-DD>-<slug>/
    ├── spec.md                  # WHAT and WHY. Approved by the developer. Stable
    ├── design.md                # HOW. project route only
    ├── tasks.md                 # the task checklist, its state, the checkpoint
    └── log.md                   # append-only: gates, reviews, spec deltas
```

`spec.md` is approved once. The approval is bound to the file's SHA-256. When the
spec changes, the gate closes again until the developer approves the change. Put
state and progress in `tasks.md` and `log.md`, never in `spec.md`.

**The gates are derived from the spec. A session is `done` only when both pass:**

- **Gate A — spec verified (tests green).** Every acceptance criterion has one
  test that names its ID (`bin/craft-spec trace` is green, or
  `trace --session N` for one project session), the checkpoint
  command ran through `bin/craft-check` and passed, and lint, import order, and
  format pass.
- **Gate B — review green.** Every routed lens ran, no open Confirmed Critical or
  High finding, every lens checklist item answered.

Session states: `pending`, `in progress`, `tests green`, `in review`, `blocked`,
`done`, `abandoned`.

Writing the code is not `done`. Passing the tests is not `done` either.

---

## 5. Active skills

Delete a row to stop the workflow from loading that skill. Add a row for your
own. The `craft` skill uses this table as its routing map.

| Trigger | Skill |
|---|---|
| Writing or changing a spec | `spec` |
| Turning an approved spec into a design and tasks | `planner` |
| Python code | `python-style` |
| Django, DRF, Celery, ORM, migrations | `django-practices` plus `python-style` |
| FastAPI, Pydantic, SQLAlchemy, Alembic | `fastapi-practices` plus `python-style` |
| Go code | `go-practices` |
| Java or Kotlin on the JVM, Spring Boot, JPA | `java-practices` |
| Node.js or TypeScript backend code | `node-practices` |
| Concurrent code for throughput, or a request for "async", "parallel", "high concurrency", "faster" | `concurrency` first. It loads the stack's own skill only when the system is built for it |
| async code in a FastAPI service the concurrency report calls ready | `fastapi-async` |
| goroutines, channels, worker pools, or shared state in Go | `go-concurrency` |
| Writing any new function, class, module, helper, or dependency | `minimal-code` |
| Adding a check, guard clause, validator, or constraint | `validation-discipline` |
| Choosing acceptance criteria, writing or auditing tests | `test-discipline` |
| Diagnosing a bug | `debugging` |
| Git hygiene and merge-request text | `git-hygiene` |
| Unsettled architecture | `system-design` |
| A second opinion on the shape of a change | `arch-assistant` — advisory, never a gate |
| Rewriting a long document for developers | `asd-ste100` |
| Acting as a reviewer, or adjudicating findings | `review-protocol` |
| A verification tool is missing | `toolchain` |
| `/jev`, or a routing decision while Jev is on (§8) | `jev` |

---

## 6. Verification commands

The workflow must never claim a check ran when it did not. Set the real commands
for your repository here. Leave a row blank to make the workflow discover it.
Run every one of them through `bin/craft-check`, which records the exit code for
Gate A and prints only the summary or the failures.

| Check | Command |
|---|---|
| Tests | `docker compose exec web pytest <paths> -q` |
| Lint | `pylint <paths>` |
| Import order | `isort --check <paths>` |
| Format | detect `black` or `pyink` from the repository config. Never `yapf` |

These rows are the **Django** stack's. Every other stack takes its commands
from the `checks` of its `stacks/<id>/stack.json`, resolved against the
repository: `bin/craft-stack checks` prints them, for example `go test ./...`,
`go test -race ./...`, `go vet ./...`, `golangci-lint run`, `./mvnw -q test`,
`pnpm test`, `npx tsc --noEmit`. A host `.claude/craft.md` overrides any of
them. Gate A on another stack is its `tests`, `lint`, and `format` rows, plus
`race` for Go code that starts goroutines, and `types` where the stack has one.

---

## 7. Local overrides

A host repository may place its own `.claude/craft.md`. When that file exists,
its rules win over this one. Use it for repository-specific routing without
forking the plugin.

---

## 8. Jev — optional typed decisions

Off by default. `/jev on` turns it on for one repository. Jev is TypeSafe's
System One decision model, reached through OpenRouter's Decisions API. It
answers the routing questions in `config/jev.json`: the route, the risk tier,
the implementer model, the skills to load, and the review lenses. It does not
call tools. Claude acts on its answers.

Every answer is combined with a rules floor built from `config/paths.json` and a
few keywords. Jev can raise a decision above the floor, never lower it. A choice
below `confidence_threshold` counts as undecided, and Claude decides. When Jev
fails, the floor and Claude's own routing apply. The developer's "use route X"
wins over both.

`/jev set endpoint <url>` and `/jev set model <id>` override the endpoint and
model for one repository. `/jev approve on` is a second switch: it lets the
`jev_approve` hook approve routine tool calls, within the lists in the
`approve` block of `config/jev.json`. Only the developer turns it on.

---

## 9. Stacks — one workflow, any backend language

`bin/craft-stack` detects the stacks of the host repository from marker files
and dependencies, at the root and two directory levels below it, so a monorepo
gets one stack per service. Each stack is a pack in `stacks/<id>/stack.json`:

| Stack | Detected by | Skills | Concurrency skill |
|---|---|---|---|
| 🐍 `django` | `manage.py`, or Django in the dependencies | `python-style`, `django-practices` | none: Django here is sync. See `concurrency` |
| ⚡ `fastapi` | FastAPI in the dependencies | `python-style`, `fastapi-practices` | `fastapi-async` |
| 🐹 `go` | `go.mod` | `go-practices` | `go-concurrency` |
| ☕ `java` | `pom.xml`, `build.gradle*` | `java-practices` | the model the report names |
| 🟩 `node` | `package.json` | `node-practices` | the model the report names |

A pack gives: the test globs and how a test names a criterion, so
`bin/craft-spec trace` works in every language; the check commands of §6; the
path globs for money, auth, migrations, models, and entry points, so the
rules floor and the lens routing work in every language; its skills,
standards, and lens notes. Detection is overridden with `bin/craft-stack set
<id>`, or `CRAFT_STACK=<id>` for one shell.

`bin/craft-stack concurrency` reads the concurrency model a stack runs and
gives a verdict: `ready`, `limited`, or `not-ready`. High-concurrency patterns
are used only where the verdict allows them. The `concurrency` skill holds the
rule.
