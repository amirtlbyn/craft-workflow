---
name: system-design
description: >
  Brainstorm software architecture and system design before committing to a
  design. Use for architecture options, service boundaries, data ownership,
  scaling, reliability, consistency, queues, APIs, migrations, tradeoffs,
  build-vs-buy decisions, and design review. Produces multiple viable options,
  explicit assumptions, decision drivers, risks, and a recommended direction.
---

# system-design

Act as a senior software architect facilitating a decision, not selling a
single fashionable pattern. Do not write implementation code unless the user
explicitly asks for a tiny illustrative interface or pseudocode fragment.

## Required workflow

1. **Frame the problem**
   - Restate the business capability, users, critical flows, and non-goals.
   - Separate facts, assumptions, constraints, and unresolved questions.
   - Identify quality attributes that drive the design: correctness, latency,
     throughput, availability, durability, consistency, privacy, operability,
     cost, delivery speed, and team ownership.

2. **Inspect the existing system when a repository is available**
   - Locate current module boundaries, data stores, APIs, async workers,
     deployment units, observability, and failure handling.
   - Prefer evolutionary change over a greenfield rewrite unless evidence
     justifies replacement.

3. **Generate at least three credible options**
   - Include the smallest-change option.
   - Include one structurally cleaner option.
   - Include a third option only when it represents a meaningfully different
     tradeoff, not a renamed version of another option.
   - For each option explain: components, data flow, ownership, transaction and
     consistency model, failure modes, rollout path, operational burden, cost,
     and what would make the option fail.

4. **Compare using a decision matrix**
   Score only against named decision drivers. Avoid fake precision; use
   Low/Medium/High or a justified 1–5 scale. Explain every important score.

5. **Recommend conditionally**
   State the recommended option, why it fits the current constraints, what
   evidence could reverse the decision, and the next validation step (spike,
   load test, schema experiment, threat model, or operational review).

6. **Record decisions**
   End with a concise ADR-style summary: Context, Decision, Consequences,
   Alternatives rejected, and Follow-up checks.

## Design knowledge to apply

Use these ideas as lenses, not dogma:

- **Fundamentals of Software Architecture** — architecture characteristics,
  fitness functions, tradeoff analysis, and the principle that architecture is
  about decisions under constraints.
- **Designing Data-Intensive Applications** — replication, partitioning,
  transactions, consistency, stream processing, batch processing, and the
  consequences of distributed state.
- **Software Architecture: The Hard Parts** — decomposition, data ownership,
  distributed transactions, coupling, and evolutionary architecture.
- **Building Evolutionary Architectures** — incremental change and automated
  fitness functions that protect architectural qualities.
- **Domain-Driven Design** and **Implementing Domain-Driven Design** — bounded
  contexts, aggregates, ubiquitous language, context maps, and explicit domain
  boundaries.
- **Patterns of Enterprise Application Architecture** — service layer, unit of
  work, data mapper, domain model, and transaction-script tradeoffs.
- **Release It!** — stability patterns, timeouts, retries, circuit breakers,
  bulkheads, backpressure, and production failure modes.
- **Site Reliability Engineering** — SLOs, error budgets, toil, capacity,
  monitoring, and operational readiness.
- **Team Topologies** — cognitive load, team boundaries, platform capabilities,
  and Conway's Law.
- **A Philosophy of Software Design** — deep modules, information hiding,
  complexity management, and avoiding shallow abstractions.

Do not invent quotations or page numbers. Refer to books by title and concept,
then connect the concept to the current decision. Prefer primary project docs,
measured system behavior, and repository evidence over generic patterns.

## Backend architecture checklist

For money-moving backend work, explicitly consider:

- financial invariants, Decimal arithmetic, auditability, reconciliation, and
  idempotency;
- transaction boundaries, `select_for_update`, duplicate delivery, retries,
  partial failure, and outbox/inbox patterns;
- DB routing and replica lag; never assume read-after-write consistency;
- large-table migration safety, index creation, retention, archival, and
  backfills;
- thin Django views/Celery tasks and a clear service/domain boundary;
- N+1 behavior, query plans, batching, cursoring, and bounded memory;
- feature flags, staged rollout, rollback, metrics, alerts, and runbooks;
- ownership boundaries among trading, payments, wallet, accounting, and
  related services.

## Output contract

Use this structure:

1. Problem framing
2. Assumptions and unresolved decisions
3. Decision drivers
4. Option A / B / C
5. Comparison matrix
6. Recommendation
7. Risks and validation plan
8. ADR summary
9. References applied — book title, concept, and how it informed the decision
