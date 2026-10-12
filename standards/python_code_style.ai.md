<!-- ═══════════════════════════════════════════════════════════════
     A team that adopts this file should take ownership of it: rename it
     to python_code_style.human.md (and update config/workflow.md). The
     craft hooks then refuse any agent edit to it.

     ▸ While it is human-owned, a coding assistant must NOT edit it
       inline. In its reply to the developer it states (a) the exact
       fragment(s) to add or change and (b) the exact file and location
       for each, and the developer applies them.
     ═══════════════════════════════════════════════════════════════ -->

# Python Code Style — language conventions for every Python change

> **MUST-READ before you write or modify ANY Python code, or design a plan that contains Python code.** No Python
> code may be generated in a session where this file has not been loaded into context. It is the language-level
> style guide (formatting, imports, naming, typing, OOP, strategy/modular design, docstrings, logging). It is written
> for a Django codebase that uses unittest/Django `TestCase`, `django.conf.settings`, and standard logging.
>
> **Companion standards (each loads when its stage begins):**
> - Django & logic architecture rules (custom serializers, ORM/DRF, `transaction.atomic`, service-layer logic,
>   settings-driven constants) live in [django_standards.ai.md](django_standards.ai.md) — read before
>   writing any implementation plan or design.
> - Implementation-stage mechanics (writing tests, generating migrations, i18n, admin/permission-group
>   registration, metrics, alerting, deployment wiring) live in
>   [implementation_standards.ai.md](implementation_standards.ai.md).
> - The engineering standards live in [technical_standards.ai.md](technical_standards.ai.md).

> **Audience vs. ownership.** The **reader is the AI/developer** about to plan or write code — this guide exists to
> be consumed before development. Once a team makes it **human-owned** (`*.human.md`), only humans change it, and
> **only by explicit human request** — never from automatic AI detection. Coding assistants then may only *flag* a
> suggested change for a human to apply. When a convention and the code disagree, the code is authoritative — open
> an issue, do not silently weaken the convention.

## Core principle

Write code that is easy to read top-to-bottom. Prefer clarity over cleverness.
Avoid unnecessary indirection, tiny helper functions, and "power features"
unless truly required.

---

## Formatting

### Tools and hard limits

- Auto-format with the project formatter, typically `black` or `pyink`, to avoid
  style debates. Run `pylint` with the project config when relevant.
- Keep lines to **80 characters** where practical. Exceptions: long URLs, long
  string literals with no whitespace, and `# pylint: disable=...` comments.
- Indentation: **4 spaces**, **no tabs**.
- No semicolons; one statement per line (exception: `if cond: action()` is
  allowed only if it fits and has no `else`).

### Line breaks

- Never use `\` for line continuation (except to escape a newline inside a
  string literal).
- Use implicit continuation inside `()`, `[]`, `{}`.
- Break at the highest syntactic level (between args/items, not mid-name).
- If a container's closing bracket is on its own line, add a trailing comma on
  the last element.

```python
result = some_func(
    first=first,
    second=second,
)
```

### Blank lines

- Two blank lines between top-level defs (functions/classes).
- One blank line between methods.
- One blank line after a class docstring before the first method.
- No blank line immediately after a `def` line.
- Use blank lines inside functions to separate logical blocks; do not overuse.

### Whitespace

- No spaces inside `()`, `[]`, `{}`.
- No trailing whitespace.
- One space after `,` and `:`, no space before them.
- One space around binary operators (`=` in expressions, comparisons,
  `and`/`or`/`not`).
- No spaces around `=` in keyword arguments or defaults, **except** when the
  parameter has **both** a type annotation and a default.

```python
def f(a: int = 0, b=1) -> None:
    ...
```

### Vertical space

- Avoid both "wall of code" (dense, no blank lines) and excessive blank lines.
- Separate code into logical blocks like paragraphs, one blank line between, a
  short header comment atop each block. The compass: skimmable top-to-bottom.
- If something fits in one line, make it one line.

```python
# Good — fits, so keep it on one line.
logging.info(f"Failed to read {whatever} from {wherever}: {ex}")
```

- Fit statements in the fewest readable lines. Do not expand short, readable
  calls or defs into one-argument-per-line when they fit the line limit. Prefer
  keeping the closing bracket on the last argument's line when it fits.

---

## Strings

- Use **f-strings** for interpolation (`%`/`.format()` are acceptable
  alternatives); never build formatted strings with `+`.
- `a + b` is fine when truly concatenating two strings, not formatting.
- Do not use `+=` to accumulate strings in a loop. Use a list + `"".join(...)`
  or `io.StringIO`.

```python
items: list[str] = ["<table>"]
for last_name, first_name in employees:
    items.append("%s, %s" % (last_name, first_name))
items.append("</table>")
html = "".join(items)
```

- Use triple double quotes for multi-line strings; use `textwrap.dedent()` when
  indentation matters.
- Be consistent with single vs. double quotes throughout a file; default to
  double quotes.

---

## Imports

- Use `import x` for packages/modules, and `from x import y` where `x` is the
  package and `y` is the module or symbol. Importing classes/functions directly
  is normal and accepted (e.g. `from django.conf import settings`,
  `from myproject.log import log`) — do not enforce the stricter "import modules
  only, qualify at the call site" rule.
- Use `from x import y as z` only when names conflict or are inconveniently long.

```python
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias
```

- **No relative imports.** Always use full package paths (no leading dots).
- **Avoid `__init__.py` re-exports** to shorten import paths; cross module
  boundaries explicitly (see Modular design — `module.Symbol`, not a re-export).
- **Ordering:** group as (1) `from __future__ import ...`, (2) stdlib,
  (3) third-party, (4) repo/internal; blank line between groups; sort
  lexicographically by full path within each group (use `isort` with the project
  config).

---

## Naming

- Identifier shapes: `module_name`, `package_name`, `ClassName`, `method_name`,
  `ExceptionName`, `function_name`, `GLOBAL_CONSTANT_NAME`, `global_var_name`,
  `instance_var_name`, `function_parameter_name`, `local_var_name`.
- Public vs. internal: prefix internal/protected names with a single leading
  `_`. Discourage double-leading `__` name-mangling — prefer single `_` for
  readability and testability.
- No dashes in any package/module name. Python files must end in `.py` and must
  not contain dashes.
- Avoid single-character names except loop counters, exception vars like `e`,
  and standard math notation.
- Avoid short or vague variable names:
  - wrong: `le = LedgerEntry.objects.get(id=entry_id)`
  - right: `ledger_entry = LedgerEntry.objects.get(id=entry_id)`
- Money variables must include the unit in the name (e.g., `cost_cents`).
- Unit tests follow `lower_with_under`; prefer `test_<method_under_test>_<state>`.

---

## Type annotations

- Annotate public APIs and complex or error-prone code.
- Prefer `X | None` over `Optional[X]`; built-in generics (`list[int]`,
  `dict[str, int]`); abstract containers from `collections.abc` in signatures.
- Import typing symbols directly (`from typing import Any, cast`;
  `from collections.abc import Sequence`).

```python
from collections.abc import Mapping, Sequence

def get_names(employee_ids: Sequence[int]) -> Mapping[int, str]:
    ...
```

- Do not use mutable default values (`[]`, `{}`); use `None` + init inside the
  function, or immutable defaults like `()`.
- Do not rely on implicit `None` defaults.
- Use annotated assignments for hard-to-infer internals: `value: Foo = compute()`.
  Do not add `# type: Foo` end-of-line comments in new code.
- Use `from __future__ import annotations` or string literals for forward
  references. Prefer refactoring to remove circular imports over `TYPE_CHECKING`.

---

## Enums

- Use enums for fields with finite, code-owned value sets (types, statuses,
  currencies, roles, phases, actions, reject reasons).
- Prefer `str, enum.Enum` for values that cross APIs, DTOs, logs, persistence,
  or module boundaries. Use integer enums only when numeric values carry domain
  meaning (card ranks, chart-of-accounts codes).
- Keep public enum values stable once exposed.
- Avoid enums when the value set is user-configurable, database-managed, or
  expected to change without a code deployment.

---

## Control flow and expressions

- Raise built-in exceptions where appropriate (`ValueError`, `TypeError`,
  `RuntimeError`).
- Avoid bare `except:` and `except Exception:` unless re-raising or creating a
  deliberate isolation boundary. Keep `try` blocks minimal; use `finally` for
  cleanup.
- **Do not use `assert` for application logic or required runtime checks**
  (asserts may be skipped). Assertions are for non-production test cases only.
- Avoid mutable global state; prefer module-level constants.
- Comprehensions: allowed for simple single-clause cases. Do **not** use
  multiple `for` clauses or multiple filters; use explicit loops instead.
- Keep lambdas to one-liners; prefer `operator` helpers where available.
- Ternaries only when all three parts fit on one line; otherwise use `if/else`.
- Use generators for memory efficiency on large sequences; document with
  `Yields:` and ensure cleanup of expensive resources (context managers).
- Truthiness: prefer implicit (`if seq:`); use `is None`/`is not None` for
  `None`; never compare booleans with `== False` (use `if not x:`); compare ints
  explicitly to `0`; for numpy arrays use `.size`.
- Avoid metaclasses, `__del__`, bytecode manipulation, and other power features
  unless the project clearly requires them (stdlib uses like `dataclasses`,
  `enum` are fine).

---

## Object-oriented design

- Define interfaces with `Protocol`; interface names end with `Interface`.
  Decorate overriding/implementing methods with `@override`. (`abc.ABC` is also
  acceptable — e.g. `LedgerInterface(ABC)`,
  `PaymentGatewayInterface(metaclass=abc.ABCMeta)` — when you need enforced
  abstract methods; prefer `Protocol` for new structural contracts.)

```python
from typing import Protocol
from typing_extensions import override

class WalkerInterface(Protocol):
    def walk(self) -> None:
        ...

class Walker(WalkerInterface):
    @override
    def walk(self) -> None:
        print("I'm walking")
```

- Prefer composition over inheritance unless a framework forces it. A root base
  class intended for inheritance must start with `Base` (e.g., `BaseModel`).
- Use `@property` only for trivial, side-effect-free attribute access; a
  `get_this_value()` method is preferred over `@property`.
- Prefer module-level functions over `@staticmethod`, except external interfaces
  meant to be used without instantiating the class (those may be static).
- Use `@classmethod` only for named constructors or class-level operations, and
  only when the class may be subclassed.

---

## Strategy pattern

Use when behavior varies by a **code-owned discriminator** (type, mode,
backend). Select by data, not by `if/elif` scattered across call sites.

- Define the contract as a `Protocol` ending in `Interface`. Put shared defaults
  in a `Base...` class; concrete strategies subclass it and `@override`.
- Resolve via a registry/factory — the `if/elif` lives there, **once** — not at
  the call site.
- Strategies are **stateless** and resolved by code, **not** by a DB query.
- Concretes depend on the interface, never the reverse.

```python
from collections.abc import Sequence
from typing import Protocol
from typing_extensions import override

class ExporterInterface(Protocol):
    def export(self, rows: Sequence[Row]) -> bytes:
        ...

class CsvExporter(ExporterInterface):
    @override
    def export(self, rows: Sequence[Row]) -> bytes:
        ...

class DBExporter(ExporterInterface):
    @override
    def export(self, rows: Sequence[Row]) -> bytes:
        ...

# The factory holds the single if/elif; call sites stay branch-free.
exporter = ExporterFactory.get_exporter(params)
data = exporter.export(rows)
```

### Shapes this takes

- **Interface + concretes + registry factory** — a `ProviderErrorFactory` holds
  the single resolver (`create_from_status_code`, `register`); concrete
  exceptions (`InsufficientBalance`, `DuplicateEventId`, …) attach themselves
  with the `@ProviderErrorFactory.register` decorator instead of a call-site
  `if/elif`.
- **Interface + `Base...` + concretes** — a `StatementParserInterface` is the
  contract; a `BaseCsvStatementParser` carries shared defaults; per-provider
  parsers subclass and specialize. Resolved by provider, not by a call-site
  branch.
- **Interface + injected implementation** — a `LedgerInterface` is the
  contract; `DbLedger` is the concrete, injected into the service (see Modular
  design below). The concrete depends on the interface, never the reverse.
- **External API handlers** — one `PaymentGatewayInterface` with one concrete
  per provider, each a strategy behind one contract.

---

## Modular design

Organize a domain as a package with **one public seam**; callers use that
surface only. A sub-package needs a real boundary, not just tiny helpers.

- **One entry point per module** (e.g., `ledger_service`). Going around it
  (raw `LedgerEntry` writes) is forbidden.
- Cross the boundary with **DTOs** (e.g., `ledger/dto_layer`), not ORM
  models.
- Decompose a large app by concern, each self-contained (e.g., `user_profile`:
  `region/`, `verification/`, `providers/`, `restriction/`, `referral/`,
  `url_manager/`), each with its own `base.py` contract plus implementations.
- Dependency direction is **one-way**: concretes depend on the contract, never
  the reverse.
- No `__init__.py` re-exports; import the module and use `module.Symbol`.

**[IMPORTANT] Do not abuse this rule.** Use a module only when it adds real
value and the target can be defined as a module *by logic* — we do not want to
end up with too many modules. A module boundary costs you forever — a contract,
DTO mapping, and indirection paid on every future change. Default to a flat
structure (same spirit as "avoid tiny packages / reduce indirection"); promote
code into a module only when it **earns the boundary** by passing all three:

1. **Reuse** — 2+ independent callers today, or a genuinely pluggable strategy.
   One caller, or "we might reuse it", is not enough — inline it.
2. **Boundary** — it maps to a real domain concept that owns its own data and
   invariants (like `ledger` owns the balances). If you cannot name the
   invariant it protects, it is a folder, not a module.
3. **Coupling** — the seam must *reduce* net dependencies (one guarded entry
   point replacing scattered access), not just add a layer everyone routes
   through.

Wrong-seam signal: if a typical simple change has to straddle the seam — editing
the contract *and* the impl *and* the DTO *and* the caller in lockstep — the
parts you split actually change together. Collapse the boundary back.

### A reference shape

A `ledger/` app that follows this pattern looks like this:

- **One public seam** — `ledger/services.py` `LedgerService`, exposed as the
  module-level singleton `ledger_service`, built as
  `LedgerService(ledger_interface=DbLedger())`. All money movements go through
  `post_transaction()` / `get_balance_dto()`.
- **Boundary crossed with DTOs, not ORM models** — `ledger/dto_layer/dtos.py`
  defines the frozen DTOs callers receive: `BalanceIdentifier` (the address),
  `BalanceDTO` (read-only state), `Transaction` (the request). ORM rows never
  leave the app.
- **The protected raw model** — `LedgerEntry` is the row callers are forbidden
  to write directly; they only ever see a read-only `BalanceDTO` handed back by
  `ledger_service`. The app reaches the model through a lazy reference, keeping
  the dependency one-way.
- **Decomposition by concern** — inside `ledger/`, the contract/impl split
  lives in `ledger_services/` (`ledger_interface.py` + `db_ledger.py`) and the
  boundary types in `dto_layer/`, each self-contained.

---

## Documentation and comments

- Treat documentation like code: keep it next to the code it explains, review it
  with code changes, and update stale docs when behavior changes. Deprecate
  stale docs explicitly.
- Optimize for the reader (who may know Python but not this codebase or domain).
  Identify the audience first: external callers, maintainers, new contributors,
  test readers, or a future debugger.
- Add docstrings to public modules, classes, functions, methods, and
  dataclasses. Add them to private helpers when the contract is not obvious from
  name and types.
- Start each docstring with a one-line summary (≤80 chars, ends in a period, in
  descriptive present tense — "Creates a thing", not "Create a thing"), then a
  blank line and details when useful.
- Use `Args`, `Returns`/`Yields`, and `Raises` sections when they clarify the
  contract; do not duplicate obvious type annotations. Omit `Returns:` for
  `None`.
- Use an `Attributes:` section for public class attributes and meaningful
  dataclass fields.
- For modules/classes, describe responsibility, collaborators, lifecycle,
  invariants, and intended use. Keep public-interface docstrings free of ORM/DB
  internals and design-history; put those in implementation comments.
- Use block comments before complex algorithms, rule enforcement, state
  transitions, and non-local decisions to explain **why** the code exists.
- Document domain rules, security assumptions, performance tradeoffs, ordering
  dependencies, and intentionally surprising choices.
- Do not restate what the next line says; comments teach structure, intent,
  constraints, or relationships. Wrap variable names in backticks (`target`).
  Use correct capitalization for names (Redis, HDFS).
- Inline comments: 2 spaces before `#`, used sparingly.
- For primitive-heavy structures, clarify key/value semantics via naming and a
  short comment:

```python
ads_by_keyword: dict[str, list[Ad]] = {}

# campaign_id, experiment_id -> spent budget in cents.
costs_breakdown: dict[tuple[int, int], int] = {}
```

---

## Functions, helpers, and structure

- Prefer a flat structure; avoid tiny packages/files unless there is a real
  boundary. Reduce indirection — do not put logic "one click away".
- **Extract a helper ONLY** when inlining would really clutter the call site
  (a sizeable, well-defined, independent piece of logic) and/or it is called
  2+ times — and even then, a trivial 1-2 line helper is better inlined. In all
  other cases, inline the code and begin the block with a short header comment.
  (No fixed line-count cap on functions — readability via header comments wins.)
- Avoid redundant local variables; prefer direct construction when the local
  adds no clarity.
- Avoid nested function defs; allow one only when it is ≤2 lines and passed as a
  callback/closure.
- Never use mutable default argument values; use `None`.
- Arguments are required by default. Use defaults only when the default is
  meaningful and safe; avoid `None` defaults unless `None` has explicit meaning.
- Do not use `*` to force keyword-only args unless a caller-side safety issue is
  documented with a brief comment.

### Call sites

- Prefer keyword arguments for non-trivial calls — literals, booleans, optional
  params, or more than two arguments.
- Positional args are fine for simple constructors, stdlib idioms, and calls
  where the argument meaning is obvious (logging, invariants, defining a flag or
  metric). Do not force keywords where the API does not support them or where
  they make a small conventional call noisier.

---

## Files and resources

- Close files/sockets/resources explicitly. Prefer `with ...`; for non-context
  resources use `contextlib.closing()`.

---

## Constants and module globals

- Module/class constants are `UPPER_SNAKE_CASE` (leading `_` if private),
  declared at the **top** of the file/class, before functions/`__init__`. Lookup
  tables, suffix lists, retry counts, and sentinels reused across methods are
  declared as class attributes immediately after `class Foo:` (before
  `__init__`), and module constants at the top of the file — never tucked above
  the first method that happens to use them. Reviewers reorder these without
  prompting. Example: a `MarketWsClient` declares `MIN_ITERATION_TIME_IN_MS` and
  `COOLDOWN_ON_403` as the first elements of its class body.
- Avoid mutable module-level globals; prefer constants.
- **Where business constants live is a Django architecture rule**, not just a
  style one — rates, limits, thresholds, and costs go in `settings.py` and are
  referenced via `settings.<NAME>`, never inlined in a model/service method. See
  [django_standards.ai.md](django_standards.ai.md) "Configuration and
  business constants".

---

## Logging

- Use the project logger (e.g. `from myproject.log import log, exception`) or a
  stdlib `logging.getLogger(__name__)`.
- Severity: high-frequency logs at `debug`, not `info`; `warning` for
  expected/tolerable issues; `error` for costly/irreversible failures.
- `debug`-level printf-style logging: pass a format string + args (lazy
  formatting), not an f-string. `info` and above: f-strings are fine.

```python
import logging

logger = logging.getLogger(__name__)
logger.debug("Fetched %d rows for trader_id=%d", count, trader_id)
logger.info(f"Fetched {count} rows for trader_id={trader_id}")
```

---

## TODOs

Use `# TODO: <bug/issue link> - <description>`. Avoid pointing at individuals.

---

## Entry points

If a file is executable, put behavior in `main()` and guard it. In a Django
project, root-level operational scripts call `django.setup()` first.

```python
def main() -> None:
    ...

if __name__ == "__main__":
    main()
```

---

## Where the rest of the rules live

These were split out of this file so each loads when its stage begins. Read the
matching file when you reach that stage:

- **Writing tests** (unittest/Django `TestCase`, DAMP-not-DRY, construction- vs
  validation-helper rules) →
  [implementation_standards.ai.md](implementation_standards.ai.md).
- **Django & logic architecture** (custom serializers, N+1/ORM, FK
  `db_constraint`, choice fields, `transaction.atomic` rules, thin views/tasks,
  service-layer logic, settings-driven constants) →
  [django_standards.ai.md](django_standards.ai.md) — read before writing
  any implementation plan or design.
- **Migrations & i18n reviewer checklists**, **admin/permission-group
  registration**, **Alerting**, **Metrics (Prometheus)**, and **Deployment
  wiring** → [implementation_standards.ai.md](implementation_standards.ai.md).

---

## General coding guide

**IMPERATIVE:** When implementing a change, do not make edits or style fixes
outside the lines necessary for the intended change. If you spot a problem
elsewhere, report it and ask before fixing. Exception: when explicitly asked to
do a broad code-style fix.

- Suppress lint warnings with `# pylint: disable=warning-name` plus an
  explanation comment.
- If a style rule here conflicts with established local project configuration,
  prefer the project configuration and mention the tradeoff.
