# standards/ — the vendored engineering standards

These four documents are the authoritative code style and engineering standards
for this workflow. Every skill and every reviewer in this plugin reads them from
here. Nothing in this plugin reads a standard from outside this directory.

| File | Owns |
|---|---|
| `python_code_style.ai.md` | Python language style: formatting, imports, naming, typing, OOP, strategy and modular design, docstrings, logging |
| `django_standards.ai.md` | Django logic and architecture: serializers, ORM/DRF, `transaction.atomic`, service-layer logic, settings-driven constants |
| `implementation_standards.ai.md` | Implementation mechanics: tests, migrations, i18n, admin registration, metrics, alerting, deployment |
| `technical_standards.ai.md` | The engineering standards TS-1 to TS-7 |

## Ownership

`*.ai.md` files are bot-maintained and may be edited by hand or by an agent.
`*.human.md` files carry a HUMAN-OWNED banner: **an agent never edits them**.
It reports the exact fragment and its location to the developer, who decides.

The three Python and Django standards ship as `*.ai.md`. A team that adopts one
takes ownership by renaming it to `*.human.md` and updating the table in
`config/workflow.md` section 1. From then on the `protect_human_owned` hook
refuses every agent edit to it.

## Replacing them with your own

These are generic standards for a large Django service. To use your team's own,
replace the files here, or keep yours in another repository and copy them in:

```bash
./scripts/sync-standards.sh /path/to/repo-with-aidocs
```

The script copies the files from that repository's `aidocs/` directory verbatim
and reports a diff. It never edits them. Then regenerate `SOURCE.lock`.

## Deliberately not vendored

These documents are repository-specific, not standards. Skills reference them
**only when the host repository has them**, and degrade cleanly when it does not:

- `INVARIANTS.human.md` — cross-app change-risk checklists.
- `ISSUES.human.md` — the known-bug register.
- `code_review_playbook.ai.md` — path-to-reviewer routing and financial-safety checks.
- `test_selection.ai.md` — which existing tests to run.
- `deployment_topology.ai.md`, `settings_flags.ai.md` — operational topology.
- Per-directory `README.ai.md` files.
