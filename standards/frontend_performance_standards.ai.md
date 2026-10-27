# Frontend Performance Standards — Vue, Nuxt, React

> **Scope & ownership:** factual `*.ai.md` (bot-maintainable), written for
> craft-workflow. It applies when `bin/craft-stack` detects a frontend stack
> (`nuxt`, `vue`, or `react`). A team that adopts this file can rename it to
> `.human.md` to make it human-owned.

## Hydration cost (Nuxt/SSR)

- Everything a bundle ships, the client re-hydrates. Before adding a
  dependency, ask what it costs on the critical path; a component library for
  three components is a payload decision, not a convenience.
- Components below the fold or behind interaction are loaded lazily
  (`defineAsyncComponent`, `Lazy*` components in Nuxt, dynamic `import()` in
  React). A lazily-rendered component is also a hydration saving.
- Interactive islands that need no server markup are candidates for
  `<ClientOnly>` with a cheap fallback, so the server payload and hydration
  work shrink together.

## Data fetching and waterfalls

- Page data is fetched in setup with `useFetch`/`useAsyncData` (Nuxt) or the
  framework's server-side data entry, so markup arrives complete. Fetching in
  `onMounted`/`useEffect` that gates first paint is a review finding.
- Parallel requests are issued in parallel (`Promise.all` of two async data
  calls, not two awaited lines). Sequential awaits that could be parallel are
  a waterfall and get fixed.
- Payloads are shaped for the page: an endpoint that returns a full entity
  list to render three fields is a server fix, not a client filter.

## Rendering discipline

- Derived values are `computed`/`useMemo`, not recomputed in template
  expressions on every render.
- Lists render with stable keys tied to identity, never the array index of a
  mutable list.
- Watchers and effects have cleanup where they start subscriptions, timers, or
  observers; a leaked `addEventListener` or interval is a defect.

## Assets

- Images ship with explicit dimensions (no layout shift), responsive sizes
  where the layout varies, and lazy loading below the fold. Prefer the
  framework image component (`nuxt/image`) over raw `img` where configured.
- Fonts subset and preloaded for the text actually used; a font that blocks
  first paint is measured, not assumed.
- Icons tree-shake: named imports from the icon package, not the whole
  library.

## Bundle and dependencies

- New dependencies are justified in the spec/PR: what it replaces, its size on
  the critical path, and whether a maintained platform API does the job.
- No `import` of a library for one utility the platform already has
  (`lodash.get`, `moment` where `Intl`/`Temporal` suffices).
- Route-level code splitting is the default; a shared chunk is extracted only
  when at least two routes need it.

## Measured, not vibed

- A performance claim in review (faster, smaller, fewer re-renders) names the
  measurement: bundle analyzer output, Lighthouse/inspection numbers, or a
  profiler trace. Unmeasured optimizations do not justify complexity.
