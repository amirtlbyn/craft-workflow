# Frontend Component Design Standards — Vue, Nuxt, React

> **Scope & ownership:** factual `*.ai.md` (bot-maintainable), written for
> craft-workflow. It applies when `bin/craft-stack` detects a frontend stack
> (`nuxt`, `vue`, or `react`). A team that adopts this file can rename it to
> `.human.md` to make it human-owned.

## Component responsibility

- One component, one job. A component that renders, fetches, and transforms
  data is three components: a container that composes data, presentational
  children, and a composable (Nuxt/Vue) or hook (React) that owns the logic.
- A presentational component is reviewed by reading its props and emits alone.
  If its behaviour cannot be predicted from that interface, the interface is
  wrong.
- Pages/routes compose; they do not implement. Business rules live in
  composables, stores, or server endpoints — never in template expressions.

## Props and emits contracts

- Every prop and emit is declared and typed. In Vue/Nuxt, `defineProps` with a
  type argument and `defineEmits` with a typed event map; in React, an explicit
  props type. No untyped escape hatches (`any`, bare `Object`) in new code.
- Props go down, events go up. A component never mutates a prop; a child never
  reaches into a parent. Where two-way binding is genuinely the model, name it
  explicitly (`defineModel` in Vue, controlled value + `onChange` in React).
- Required props are required. Optional props carry defaults in the type, not
  in scattered `|| fallback` expressions in the template.
- An emit's payload is documented where the event is declared, including when
  it carries nothing.

## Composition and reuse

- Reuse by composition first: slots (Vue) or children (React) beat
  configuration. A component with eight boolean props is a rewrite waiting to
  happen; split it.
- Duplication is extracted only after the third instance, and only when the
  instances agree on the abstraction. Two similar components that differ in
  intent are not the same component.
- Shared components live in one place (`components/` in Nuxt/Vue). Anything
  used by two features belongs there; anything used by one does not.
- Generic components (tables, dialogs, selects) expose a typed item model, not
  an `any`-shaped escape valve.

## Auto-imported components (Nuxt)

- Nuxt auto-imports `components/` by filename. A component's file name is its
  public API: descriptive, stable, and free of its directory prefix when the
  directory is already the namespace (`components/ui/AppButton.vue`, not
  `components/ui/UiAppButton.vue`).
- Deleting or renaming an auto-imported component is a breaking change for
  every template that uses it. Grep templates before renaming.

## Styling boundaries

- A component owns its own styles (scoped styles or a component-level class);
  it never reaches into another component's internals with a global selector.
  Deep selectors (`:deep()`, `::v-deep`, descendant hacks) are reviewed like a
  public-API change to the target component.
- Layout that a parent must control is exposed as props, slots, or CSS custom
  properties — not overridden from outside.

## What reviewers refuse

- Data fetching or business rules inside a leaf component's template or setup.
- An undeclared or untyped prop/emit; a mutated prop.
- A component imported only to forward props to another component.
- A shared component that reads global application state silently — state
  dependency belongs in the composition layer, visible at the call site.
