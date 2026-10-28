---
name: component-design
description: "Vue, Nuxt, and React component design for implementation and review: one component one job, typed props and emits with data flowing down and events up, no prop mutation, composition over configuration, slots before boolean-prop explosion, extraction only on the third agreeing instance, and auto-import naming treated as public API. Load it before writing or reviewing a component in a Vue, Nuxt, or React codebase."
---

# component-design

First read two neighbouring components and `config/workflow.md`. Follow what is
there; repository standards win when they are more specific.

`standards/component_design_standards.ai.md` holds the detail:
`bin/craft-std component_design_standards --list`.

## Responsibility and boundaries

- One component, one job. If the docstring or name needs an "and", split it.
- Extract a shared abstraction only on the third agreeing instance, not the
  second guess. A component used once stays inline.
- Composition over configuration: a slot or a child component before a
  boolean-prop explosion (`<Modal fancy compact tall wide>`).

## Props and emits

- Data flows down through props; changes flow up through emits. Never mutate a
  prop, and never emit a mutation request disguised as an event that edits the
  parent's object in place.
- Vue: typed `defineProps<{...}>()` and `defineEmits<{...}>()` with
  `withDefaults` where needed. React: an explicit props type; no `any`.
- Every emit has a corresponding handler expectation documented at the call
  site or in the component's own comment.

## Naming (auto-import is public API)

- In Nuxt, the `components/` filename is the exported component name.
  Renaming a file is a breaking change: grep usages before renaming, and keep
  directory prefixes (`base/`, `app/`) consistent with the existing tree.

## Styling boundaries

- Scoped styles stay in the component that owns them. No `:deep()` reach-ins
  into a child's internals from a parent — style through the child's own API
  (props, slots, CSS custom properties).
- `styling-discipline` decides how styles are written; this skill only says
  they stay inside the component's boundary.

## Accessibility

- Interactive elements are semantic HTML first (`button`, `a`, `input`); ARIA
  only where semantics cannot say it.
- Every interactive element is keyboard operable with a visible focus state.
- Loading, error, and empty states are announced (`aria-live`, `role=status`)
  rather than only visual.

## Performance

- Measure before memoizing. React: `React.memo` for pure components that
  re-render on unrelated state, `useCallback`/`useMemo` only for work that is
  actually expensive or referentially required. Vue: `computed` over methods
  in templates; a watcher is a last resort.
- Lists render a bounded window or paginate before any virtualization is
  introduced.
- No new subscription, observer, or listener without a teardown.

## Testing

- A component test asserts the contract: props in, emitted events out, and the
  rendered result the user sees — not internal state.
- Test the state transitions of the component (empty, loading, error,
  success), one test per transition.
- Accessibility is part of the test: role and label queries before class or
  test-id queries.

## React patterns

- Follow the Rules of Hooks: no conditional hooks, complete dependency arrays.
- `React.memo` for pure components; `useCallback` for handlers passed to
  memoized children; `useMemo` for genuinely expensive derivations.
- Custom hooks own reusable logic: one concern per hook, named `useThing`,
  returning a tuple or object documented at the hook.
- Context for genuinely global cross-tree values (theme, session) — not to
  avoid drilling props two levels.
- Error boundaries wrap critical subtrees; one boundary per page region is
  enough.

## Vue patterns

- `<script setup>` with the Composition API. `computed` for derived values,
  never a manual ref synced by a watcher.
- Watchers: `watch` with explicit sources and an `immediate`/`deep` decision
  written down; side-effect watchers clean up with `onScopeDispose`.
- `provide`/`inject` only for component-library internals or theming, with the
  injection key typed and exported.
- Slots before boolean props; scoped slots when the child needs to hand data
  back for rendering.

## Angular patterns

- `OnPush` change detection on every new component; immutable inputs keep it
  sound.
- `trackBy` on every `*ngFor` over a collection that can change identity.
- Pure pipes for transformations; pipes are stateless unless documented.
- Subscriptions are torn down: `takeUntilDestroyed` or a `Subscription`
  collected and unsubscribed in `ngOnDestroy`. `async` pipe where possible.
- Constructor injection with typed tokens; no `Injector.get` service location.

## Review checklist

- One responsibility, no orphan props, no boolean-prop explosion.
- Props typed, emits typed, nothing mutates a prop.
- Slots used where structure varies; shared extraction justified by a third use.
- Rename of a `components/` file came with a project-wide usage grep.
- Keyboard operable, focus visible, async states announced.
- Memoization measured, teardown present, tests assert the contract.
