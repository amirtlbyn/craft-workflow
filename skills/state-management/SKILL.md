---
name: state-management
description: "Where state lives in a Vue, Nuxt, or React app: local component state by default, shared UI state in useState or a store, and server state fetched with useFetch, useAsyncData, or TanStack Query that is never mirrored into a client store. Includes the SSR rule that module-level refs and shared singletons leak across Nuxt requests. Load it before choosing where state lives or reviewing state changes in a Vue, Nuxt, or React codebase."
---

# state-management

First read how the app already shares state (`composables/`, `stores/`,
context providers). Follow what is there; repository standards win.

## The taxonomy — pick the smallest home

1. **Local component state by default.** A ref or `useState` inside the
   component that renders it. Lift it only when a second component needs it.
2. **Cross-component shared UI state** (theme, sidebar open, draft form):
   `useState` (Nuxt) or a Pinia/Redux/Zustand store — the store pattern the
   repository already uses, not a new one.
3. **Server state is not client state.** Data owned by the backend
   (`useFetch`, `useAsyncData`, TanStack Query) keeps its own cache and
   invalidation. Do not copy it into a store; mirror it and the two copies
   disagree.

## SSR rule (Nuxt)

- A module-level `ref`, a shared singleton, or a plain module variable leaks
  across requests — every visitor shares one user's data. Shared state is
  `useState("unique-key", ...)` or Pinia, only.
- Keys are stable and unique per scope; two unrelated features never share a
  key.

## Dependency visibility

- No silent global reads inside leaf components. Pass the state through props
  so the component's dependencies are visible at the call site.
- Derived state is `computed` (or a selector), calculated from its source.
  Never store a second copy of a value that is a function of other state.

## Money and auth

- Cart totals, payments, sessions, and tokens get the money/auth path review:
  who writes it, where it is validated, and that it is never trusted from the
  client. A client-side store is a convenience cache, not a source of truth.

## Performance

- State slicing: a store exposes slices; a component subscribes to the slice
  it renders, not the store.
- Derived values are computed or selector-based (`reselect` for Redux);
  memoize the selector, not the component.
- Batch updates: group mutations that would each trigger a render (React 18
  batches automatically; Pinia/Vuex actions batch naturally).
- Persisted state (localStorage, cookies) is opt-in per slice, versioned, and
  never holds auth tokens or secrets.

## Testing state

- Test state transitions (initial -> loaded -> error -> recovered), not
  implementation details of the store.
- Server state is mocked at the fetch layer; a test never depends on network.
- Side effects (invalidation, refetch, optimistic update + rollback) each get
  a test naming the trigger.
- Persistence round-trips: serialize, restore, assert the store state.

## React patterns

- `useState` for local, `useReducer` when transitions have named actions or
  the next state depends on the previous one.
- Context for low-frequency global values; high-frequency updates belong in a
  store (`zustand`, Redux Toolkit) or co-located state.
- `zustand`: one store per domain, selectors at the call site
  (`useStore(s => s.slice)`), never destructuring the whole store in a render.
- TanStack Query owns server state: stale times stated, invalidations keyed,
  optimistic updates carry an `onError` rollback.
- Jotai/Recoil atoms stay fine-grained; derived atoms instead of derived
  duplicates.

## Vue patterns

- `ref` for single values, `reactive` for composed objects — never
  destructuring a `reactive` object (loses reactivity).
- `computed` for every derived value; a `watch` writing to another ref is a
  `computed` waiting to be found.
- Pinia: `defineStore` per domain, setup-style stores with `ref`/`computed`;
  state mutated through actions in dev, `storeToRefs` when destructuring.
- Vuex is legacy: new stores are Pinia; a Vuex migration goes through the
  report, module by module, and never mixes both for one domain.
- Vue Query (`useQuery`/`useMutation`) for server state, same rule: never
  mirrored into a store.

## Angular patterns

- Services are the stores: `providedIn: 'root'` singletons exposing state via
  `BehaviorSubject` or Angular signals (`signal`, `computed`).
- RxJS: state streams with `scan`/`distinctUntilChanged`; subscriptions in
  components use the `async` pipe or `takeUntilDestroyed`.
- NgRx for large apps with time-travel needs; `createSelector` for derived
  state, effects only for side effects. Akita follows the same discipline with
  less ceremony — pick one, not both.
- Angular Query for server state when RxJS is not already the house style.

## Review checklist

- State lives in the smallest scope that works; no store created for one
  component.
- No server response mirrored into a store without a stated invalidation rule.
- No module-level mutable state in SSR code.
- Derived values computed, not duplicated; leaf components take state via props.
