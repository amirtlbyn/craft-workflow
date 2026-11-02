---
description: Run one routed review pass against the spec and adjudicate the findings
argument-hint: [target, or empty for uncommitted changes; "full" for one reviewer per lens]
---

Load the `craft` skill and run its Gate B step (task route, step 5) as a single review pass for: $ARGUMENTS

With no target, review the uncommitted changes against the active spec. Follow
the skill and `review-protocol` for every step.
