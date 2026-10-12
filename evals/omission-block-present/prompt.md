---
description: The omission set is part of the spec, not an afterthought.
tags: [gate, tests]
plugins: ["../.."]
expected_outcome: Acceptance criteria appear, followed by a "Not tested, and why" block.
max_turns: 14
timeout_seconds: 360
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite]
---

Propose the acceptance criteria and tests for this new Django code, and do not write them yet.

```python
class ReferralCode(models.Model):
    code = models.CharField(max_length=12, unique=True, db_index=True)
    owner = models.ForeignKey("traders.Trader", on_delete=models.CASCADE)
    uses_left = models.PositiveIntegerField(default=10)
    expires_at = models.DateTimeField()

def redeem(code: str, trader: Trader) -> ReferralBonus:
    referral = ReferralCode.objects.select_for_update().get(code=code)
    if referral.expires_at <= timezone.now():
        raise ReferralExpired(code)
    if referral.uses_left == 0:
        raise ReferralExhausted(code)
    if referral.owner_id == trader.id:
        raise SelfReferral(code)
    referral.uses_left -= 1
    referral.save(update_fields=["uses_left"])
    return ReferralBonus.objects.create(trader=trader, source=referral)
```
