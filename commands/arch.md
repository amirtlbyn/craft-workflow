---
description: Ask the architecture assistant for a second opinion — advisory only
argument-hint: [what to look at, or empty for the current change]
---

Load the `arch-assistant` skill and advise on:

$ARGUMENTS

With no argument, look at the current uncommitted change, or the active spec and its design when
one exists.

Describe the current shape from the code first. Name a force before you suggest
anything — and when you cannot name one, say the shape fits and stop. State the
permanent cost of every boundary you propose. Classify each suggestion as
WORTH IT NOW, WORTH IT LATER, or NOT WORTH IT.

End with a recommendation and `Your call.` Do not implement. Do not block.
