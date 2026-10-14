# SPEC: {title}

Key: {key} · Route: {route} · Risk: low
Created: {date}

<!-- spec.md is the WHAT and the WHY. The developer approves it once, and the
     approval is bound to this file's SHA-256. Keep state and progress out of it:
     they go in tasks.md and log.md. A change here closes the gate until the
     developer approves the change. Delete every comment before approval. -->

## Problem

<!-- 2 to 4 sentences. What is wrong or missing, for whom, and how we know. -->

## Non-goals

<!-- What this change will not do. Each line removes a way to overbuild. -->
- 

## Acceptance criteria

<!-- One observable behavior per row, in EARS form. Each row gets exactly one
     test, and that test names the ID in its docstring. Class comes from
     test-discipline. Keep the list short: MUST and SHOULD classes only. -->

| ID | Criterion | Class | Failure it catches |
|---|---|---|---|
| {key}-1 | WHEN <trigger>, THE <component> SHALL <observable response>. | BUSINESS RULE | <the realistic bug this catches> |

Not tested, and why:
- <behavior> — FRAMEWORK BEHAVIOR

## Invariants

<!-- State that must stay true after every code path, including under two
     concurrent callers. Name the layer that owns it and the mechanism. -->
- INV-1 — <invariant> — owned by <layer> — enforced by <constraint | lock | transaction | check>

## Contracts

<!-- Changed API endpoints, serializer shapes, Kafka payloads, Celery task
     signatures, settings keys. Write "None." when nothing external changes. -->
None.

## Validation decisions

<!-- From validation-discipline. Only the meaningful checks. -->
- <invariant> — REQUIRED — enforced in <layer>

## Standards that apply

<!-- The sections the implementer and the reviewer must read. Use the names
     that `bin/craft-std --list` prints: python_code_style and django_standards
     on Django, fastapi_standards, go_standards, java_standards, node_standards,
     php_standards on the other stacks. Keep it to what this change touches. -->
- python_code_style: Naming, Type annotations
- Checkpoint: `<the real test command from config/workflow.md section 6>`

## Open questions

<!-- Only questions that change scope, data, behavior, security, or rollout.
     Resolve every one before approval, or write the assumption. -->
| Question | Options | Decision |
|---|---|---|
