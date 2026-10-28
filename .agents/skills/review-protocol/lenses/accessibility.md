# Accessibility Lens

Owns: accessibility of the changed frontend surface — semantics, keyboard
operability, focus, announcements, forms, and visual accessibility (contrast,
motion).

Severity ceiling: Critical. Confidence threshold: 0.8.

## Checklist

- [ ] Interactive elements are semantic HTML first (`button`, `a`, `input`,
      `select`); ARIA only where semantics cannot express the control.
- [ ] Everything interactive is keyboard operable in a logical tab order; no
      keyboard trap; custom widgets follow their ARIA pattern.
- [ ] Focus is visible on every focusable element; a removed outline is
      replaced with a stronger focus style; focus moves sensibly on route or
      dialog changes and returns on close.
- [ ] Every image has alt text that earns its place; decorative images are
      `alt=""`; icons that carry meaning are labeled.
- [ ] Form controls have associated labels; errors reference the control
      (`aria-describedby`), describe the fix, and are announced.
- [ ] Dynamic content changes are announced (`aria-live`, `role=status`,
      `role=alert`) at the right politeness for the change.
- [ ] Headings form a structure (no skipped levels); landmarks (`main`,
      `nav`) are used instead of div soup.
- [ ] Text meets WCAG AA contrast against its real background, including over
      images and gradients; information is never carried by color alone.
- [ ] Motion honors `prefers-reduced-motion`; nothing flashes faster than the
      WCAG threshold.
- [ ] Dialogs and modals manage focus: trapped while open, `aria-modal`,
      labelled, closed with Escape.

## Verification

- Automated: `npx axe-core` (or the project's `vitest-axe`/playwright-axe
  wiring) over the changed components; every violation is a finding.
- Manual: one keyboard-only pass over the changed surface. Note in the review
  that the pass happened, or that it could not and why.

## Stack notes

Run `bin/craft-stack lens accessibility --paths <changed paths>` for the
detected stack's own notes. Per stack:

- **React** — semantic elements before ARIA; focus management with refs, not
  querySelector; announcements via a live region component, not innerHTML.
- **Vue** — `v-html` never renders unsanitized or unlabeled content;
  `<Transition>` output stays accessible; Teleport targets keep focus logic
  with the dialog component.
- **Nuxt** — SSR output must be accessible before hydration: semantics and
  labels render on the server; `<ClientOnly>` regions ship their own fallback
  that is not a focus hole.
