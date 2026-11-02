# Nuxt Lenses

## SSR Safety Lens
- No `window`/`document` access outside `onMounted`, a client plugin, or a `.client.ts` file.
- State shared across requests lives in `useState`, never module-level `ref`s.
- Components that cannot render on the server are wrapped in `<ClientOnly>` with a fallback.

## Data Fetching Lens
- Page data uses `useFetch`/`useAsyncData` with a stable key; no bare `onMounted` fetching that gates first paint.
- Sibling calls never reuse the same key; payloads are awaited in setup, not chained after mount.

## Route & Hydration Lens
- Dynamic routes declare their params; middleware redirects are SSR-aware.
- Rendered output has no `Date.now()`/`Math.random()` values that can mismatch at hydration.

## Component Lens
- Composition API state is local unless sharing is justified.
- Derived values use `computed`; watchers are reserved for side effects.
- Props and emits are typed, documented, and validated.

## Accessibility Lens
- Templates use semantic elements, labels, visible focus, and keyboard support.
- Dynamic announcements and dialogs expose an appropriate accessible name.
