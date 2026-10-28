# Component Lens

Owns: component design correctness in frontend code — the props/emits
contract, reactivity and hooks discipline, rendering states, teardown, and
component-level performance claims.

Severity ceiling: High. Confidence threshold: 0.7.

## Checklist

- [ ] Props are typed and validated; required props are required; defaults
      live in the type, not in scattered `|| fallback` expressions.
- [ ] Nothing mutates a prop. Data flows down, events flow up; two-way
      binding is explicit (`defineModel`, controlled value + `onChange`).
- [ ] Every emit has a handler expectation and a documented payload.
- [ ] Reactivity/hooks rules hold: no conditional hooks, complete dependency
      arrays (React); `computed` for derived values, watchers only for side
      effects (Vue); `OnPush` with `trackBy` (Angular).
- [ ] Loading, error, empty, and success states are explicit in the render.
- [ ] Every subscription, observer, listener, and timer has a teardown.
- [ ] Memoization is measured: `React.memo`/`useCallback`/`useMemo` appear
      only where a re-render or computation was measured to matter.
- [ ] Error boundaries (React) or error states (Vue/Angular) wrap critical
      subtrees.
- [ ] The component is testable from its public contract: props in, events
      out, rendered output.
- [ ] Component responsibility stays narrow; no template business logic.

## Stack notes

Run `bin/craft-stack lens component --paths <changed paths>` for the
detected stack's own notes. Per stack, the lens resolves to:

- **React** — Rules of Hooks and dependency arrays; `React.memo` for pure
  components; `useCallback` for handlers passed to memoized children; error
  boundaries around critical regions.
- **Vue** — Composition API: `defineProps`/`defineEmits` typed; `computed`
  over watcher-synced refs; `provide`/`inject` only for library internals or
  theming; slots before boolean props.
- **Nuxt** — everything Vue, plus the SSR lenses: no module-level shared
  state, `useState` keys stable and unique, hydration-safe rendering.
- **Angular** — `OnPush` change detection; `trackBy` on `*ngFor`;
  subscriptions torn down via `async` pipe or `takeUntilDestroyed`; typed
  constructor injection.
