---
description: 🧩 The stacks of this repository (Django, FastAPI, Go, Java, Node, PHP), their checks, and their skills
argument-hint: "[detect | checks | skills | set <id> | unset | list]"
---

Run from the host repository root:

```bash
<plugin root>/bin/craft-stack $ARGUMENTS
```

With no argument it detects the stacks. Report what it prints as it is. After
`checks`, remind the developer that Gate A runs each command through
`bin/craft-check`, and that `.claude/craft.md` can override any of them. After
`set`, say that detection is overridden for this repository until `unset`.
