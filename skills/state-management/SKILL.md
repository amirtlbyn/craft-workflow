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

## Review checklist

- State lives in the smallest scope that works; no store created for one
  component.
- No server response mirrored into a store without a stated invalidation rule.
- No module-level mutable state in SSR code.
- Derived values computed, not duplicated; leaf components take state via props.
