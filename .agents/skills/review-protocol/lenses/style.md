# Lens: style — what the linters cannot see

- **Ceiling:** Medium. **This lens never blocks a merge.**
- **Minimum confidence:** 0.8. It is the cheapest lens, so its bar is the highest.
- **Reads:** `skills/asd-ste100/references/card.md`, sibling files in the
  touched modules for local convention, and these sections only when an item
  needs them:
  `bin/craft-std python_code_style Naming "Type annotations" "Documentation and comments"`,
  `bin/craft-std django_standards "Django logic and style"`.

Formatting, line length, blank lines, and import order belong to the Gate A
tools. Do not report them.

**Other stacks.** The items below name Django constructs. On another stack, run
`bin/craft-stack lens style --paths <changed paths>` and apply its notes in their
place.

## Naming pass — every new or renamed identifier

Report an identifier that is:

- an abbreviation a newcomer cannot expand — `ac`, `tx_amt`, `usr_bal`, `tmp2`
- vague — `data`, `result`, `handle`, `process`, `do_it`, `flag`
- a boolean that does not read as a predicate. Prefer `is_`, `has_`, `should_`, `can_`
- a money value with no unit — `cost` instead of `cost_cents`
- a collection with a singular name, or a scalar with a plural name
- shaped against the case convention for its kind

Quote the current name and give the replacement.

## English pass — every added comment, docstring, and developer message

Apply the six scan checks from the card: synonym rotation, hedge stacking,
nominalization, marketing adjectives, run-on sentences and semicolons, soft
phrasal verbs. Do not apply them to user-facing text or to exception messages
users see.

## Checklist — answer every item

1. **Naming** — the pass above.
2. **Typing** — annotations on public APIs, `X | None`, built-in generics, no
   mutable defaults.
3. **Docstrings** — present on public modules, classes, functions, and every
   test method, in the required shape. Test docstrings start with the criterion ID.
4. **English** — the pass above.
5. **Structure** — no tiny helper that should be inlined, no needless
   indirection, constants at the top of the file or class. No new code that
   reimplements the codebase, the stdlib, Django/DRF, or an installed
   dependency (`minimal-code`). Name the existing thing to use instead.
6. **Framework idiom** — on Django: thin views and tasks, `TextChoices` or
   `IntegerChoices`, no `ordering = ["-id"]`, no `@transaction.atomic`
   decorator. On another stack: the idiom in its stack notes.
7. **Constants** — no hardcoded business constant. It belongs in settings.
8. **Localization** — no hardcoded user-facing string.
