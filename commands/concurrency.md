---
description: 🧵 Is this system built for high concurrency? The model it runs, the verdict, what is allowed, and what to avoid
argument-hint: "[--stack django|fastapi|go|java|node|laravel|symfony|php]"
---

Load the `concurrency` skill, then run from the host repository root:

```bash
<plugin root>/bin/craft-stack concurrency $ARGUMENTS
```

Report the model, the verdict, and the allowed and avoid lists in a short
table. Then follow the skill:

- `ready` → name the stack's concurrency skill to load (`fastapi-async`,
  `go-concurrency`), and the Gate A additions (`go test -race` for Go).
- `limited` → say which part is safe, and that anything beyond it is a change of
  model.
- `not-ready` → do not introduce concurrency here. Give the three choices of the
  skill's Step 3, and say which one fits the request.
