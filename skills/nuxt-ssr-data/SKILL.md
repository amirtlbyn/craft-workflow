---
name: nuxt-ssr-data
description: "Nuxt SSR and data-fetching discipline: useFetch and useAsyncData with stable unique keys, awaiting in setup so markup ships complete, the useLazy tradeoff, refreshNuxtData and clearNuxtData invalidation, SSR safety for window and document, ClientOnly boundaries, hydration discipline without Date.now or Math.random, and JSON-safe payloads. Load it before writing or reviewing data fetching, SSR behavior, or hydration-sensitive code in a Nuxt project."
---

# nuxt-ssr-data

First read the page or composable and its siblings. Follow what is there;
repository standards win when they are more specific.

## Data fetching

- `useFetch`/`useAsyncData` with a stable, unique key. Sibling calls never
  share a key — a shared key returns the first call's data for the second.
- Await in `<script setup>`, not `onMounted`, so the markup ships complete.
  An `onMounted` fetch that gates first paint is a defect, not a style choice.
- `useLazy*` trades blocking render for a flash of empty content. Use it only
  where an empty first paint is acceptable, and say so in the report.
- Invalidation through `refreshNuxtData(key)` / `clearNuxtData(key)`. Not by
  re-assigning refs or reloading the page.

## SSR safety

- `window`, `document`, and other browser APIs only inside `onMounted`, a
  `.client.ts` file, or a `plugins.client` plugin — never at module or setup
  top level.
- A client-only widget is wrapped in `<ClientOnly>` with a fallback for the
  server render, not hidden behind a `process.client` guard alone.

## Hydration discipline

- Nothing rendered on the server may differ on the client: no `Date.now()`,
  `Math.random()`, `crypto.randomUUID()`, or window-only values in rendered
  output. Derive them in an event handler or after mount.
- `useState` keys are stable and unique per scope (see `state-management`).

## Payload serialization

- Everything `useFetch`/`useAsyncData` ships in the payload must be JSON-safe:
  no class instances, no functions, no Maps or Sets, no `Date` objects where a
  string works. A non-serializable value breaks or corrupts hydration.

## Middleware and navigation

- Route middleware is SSR-aware: redirects use `navigateTo`, never a
  `window.location` assignment, so they work on the server and the client.

## Review checklist

- Keys unique; data awaited in setup; lazy use justified.
- No browser API outside `onMounted`/`.client`; `ClientOnly` has a fallback.
- No hydration-mismatch sources in rendered output; payload is JSON-safe.
- Middleware redirects via `navigateTo`.
