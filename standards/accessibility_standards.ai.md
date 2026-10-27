# Accessibility Standards — Vue, Nuxt, React

> **Scope & ownership:** factual `*.ai.md` (bot-maintainable), written for
> craft-workflow. It applies when `bin/craft-stack` detects a frontend stack
> (`nuxt`, `vue`, or `react`). Baseline: WCAG 2.1 AA. A team that adopts this
> file can rename it to `.human.md` to make it human-owned.

## Semantics first

- Reach for the native element before ARIA: `button`, `a`, `input`, `select`,
  `table`, `details`. A `div` with a click handler and a `role="button"` patch
  is a defect — the native element already ships focus, keyboard, and
  announcement behaviour.
- Landmarks structure the page: `header`, `nav`, `main` (one), `footer`.
  Every page has an `h1`; heading levels descend without skipping.
- Decorative images are `alt=""`; informative images describe their content;
  icon-only controls carry an accessible name.

## Keyboard operability

- Every interactive element is reachable and operable with the keyboard, in a
  logical tab order. If it responds to click, it responds to Enter/Space or is
  a native control.
- Visible focus is never removed (`outline: none` without an equivalent
  `:focus-visible` style is a finding).
- Modals and menus trap and restore focus per the ARIA APG pattern for their
  role; Escape closes; focus moves to the dialog on open and back to the
  trigger on close.
- Skip navigation to `main` exists on pages with repeated navigation.

## Forms

- Every control has a programmatically associated `label` (or
  `aria-label`/`aria-labelledby` where a visible label is a design decision
  the team consciously made — the association still exists).
- Errors are announced: the field is `aria-invalid`, the message is linked
  with `aria-describedby`, and focus moves to the first invalid field on
  submit.
- Required fields, input purpose, and formats are stated in text, not color or
  placeholder alone. Placeholders are examples, never labels.

## Dynamic content and announcements

- Async state changes that a sighted user sees (loading, success, error) are
  announced via a polite live region; route changes in SPAs announce the new
  page title.
- Toasts are `aria-live` regions, not just visual popups.
- Content that updates in place (tables, counters) does not steal focus or
  reset scroll to announce itself.

## Color, contrast, motion

- Text contrast meets 4.5:1 (3:1 for large text and UI boundaries). Contrast
  is checked with a tool, not estimated.
- Color never carries meaning alone — pair it with text, an icon, or a
  pattern (form errors, chart series, status pills).
- Respects `prefers-reduced-motion`; nothing flashes more than three times a
  second.

## Verification

- Every review pass answers, with evidence: Can this flow be completed with
  the keyboard alone? Does the screen reader announce what the user needs at
  each step (names, roles, states)? Do the checks hold up at 200% zoom?
- Automated scans (`@axe-core/playwright`, `vue-axe`) run in the test suite
  for new pages; a scan catches the mechanical third, not the workflow —
  keyboard walking the flow is the standard, and it is done in review.
