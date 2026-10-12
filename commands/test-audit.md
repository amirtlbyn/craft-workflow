---
description: Audit existing tests for low value and propose removals
argument-hint: <test file, directory, or empty for the current diff>
---

Audit the tests in:

$ARGUMENTS

With no argument, audit the tests in the current uncommitted diff.

Load `test-discipline` and run its **Step 4** audit against every test in scope.
For each test, report the class, whether it has a realistic failure story, and the
verdict: `keep`, `merge into <test>`, or `remove`.

Group the output by verdict. For every `remove`, give the one-line reason.

**Propose. Do not delete.** Deleting an existing test needs the developer's
approval, and you present the list first.
