---
description: A one-line change that touches a balance is promoted, never quick.
tags: [routing, money]
plugins: ["../.."]
expected_outcome: The route line names task or project, never quick, and the reason names money.
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite]
---

One-line change. In `apps/wallet/services.py`, `_apply_withdrawal_fee` currently
rounds the fee like this:

    fee = round(amount * rate, 2)

Change it to quantize with `Decimal` and `ROUND_HALF_UP` to two places instead.
The result is subtracted from the trader's balance.
