# SPEC: Daily withdrawal limit per tier

Key: WDL · Route: task · Risk: high
Created: 2026-09-23

## Problem

A trader can withdraw any amount in one day. The tier table already stores a
daily limit, but `WithdrawalService.request()` never reads it. Support reported
two accounts that withdrew above their tier limit last week.

## Non-goals

- No change to the tier table or to how a tier is assigned.
- No per-currency limit. The limit is in cents, as the tier table stores it.
- No new API endpoint. The existing withdrawal endpoint returns the new error.
- No admin override flow.

## Acceptance criteria

| ID | Criterion | Class | Failure it catches |
|---|---|---|---|
| WDL-1 | WHEN a withdrawal would take the trader's total since 00:00 UTC above the tier's daily limit, THE withdrawal service SHALL reject it with `DailyLimitExceeded` and create no withdrawal row. | BUSINESS RULE | Limit read but not enforced, or enforced after the row is written |
| WDL-2 | WHEN the total equals the limit exactly, THE withdrawal service SHALL accept the withdrawal. | BUSINESS RULE | Off-by-one: `>=` instead of `>` |
| WDL-3 | WHEN withdrawals exist from before 00:00 UTC, THE withdrawal service SHALL not count them. | BUSINESS RULE | Window computed in Tehran time, not UTC |
| WDL-4 | IF two withdrawals for one trader run at the same time, THEN THE withdrawal service SHALL let at most one of them pass the limit. | CRITICAL BEHAVIOR | Race: both read the old total and both pass |
| WDL-5 | WHEN the endpoint receives a request that exceeds the limit, THE API SHALL return 400 with error code `daily_limit_exceeded`. | INTEGRATION CONTRACT | Error leaks as 500, or the code differs from the mobile client's |

Not tested, and why:
- The tier model returns its `daily_limit` field — FRAMEWORK BEHAVIOR.
- Rejected and cancelled withdrawals do not count — covered already by
  `test_services.py::test_total_ignores_rejected`, not duplicated.

## Invariants

- INV-1 — the sum of a trader's accepted withdrawals since 00:00 UTC never
  exceeds the tier's daily limit — owned by the service layer — enforced by
  `select_for_update()` on the trader's wallet row inside the existing atomic
  block.

## Contracts

- `POST /api/v1/withdrawals/` gains one error: 400, `daily_limit_exceeded`.
  The mobile client already renders unknown 400 codes, so no client change.

## Validation decisions

- Amount within the daily limit — REQUIRED — enforced in `WithdrawalService.request()`.
- Amount is positive — REDUNDANT — already enforced by `WithdrawalSerializer.validate_amount`, not added.

## Standards that apply

- django_standards: Django logic and style
- python_code_style: Naming, Constants and module globals
- technical: TS-5
- Checkpoint: `docker compose exec web pytest apps/wallet -q`

## Open questions

| Question | Options | Decision |
|---|---|---|
| Does "day" mean UTC or Tehran time? | UTC / Asia/Tehran | UTC — decided by the developer, 2026-09-23 |
