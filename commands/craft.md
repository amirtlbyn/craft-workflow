---
description: Classify a request into a cost route and run the spec-driven Craft workflow
argument-hint: <what you want done>
---

Load the `craft` skill and handle this request:

$ARGUMENTS

Read `config/workflow.md` first, then the host override at `.claude/craft.md`
when it exists. Run `bin/craft-spec status` to see whether a spec is already in
progress. Classify the request into **quick**, **task**, or **project** with the
rules in §2. State the route and one reason in a single line, then run it.
Promote the route when the change touches money, authentication, authorization,
migrations, concurrency, or an externally visible contract. Never demote.
