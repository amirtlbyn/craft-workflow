---
name: styling-discipline
description: "One styling approach per repository — utility CSS, scoped SFC styles, or CSS Modules — decided once in config or the README, with design tokens for color, spacing, and typography instead of raw hex and magic pixel values, layout from flex and grid primitives, and accessibility treated as a styling concern. Load it before adding styles, a styling library, or design tokens to a frontend project."
---

# styling-discipline

First find the repository's decision: `config/workflow.md`, the README, or the
existing components. One approach per repository. If none is written, propose
one there before adding styles — do not decide per component.

## One paradigm per repository

- Utility CSS (Tailwind, UnoCSS), scoped SFC styles, or CSS Modules — use what
  the repo has. Never mix paradigms inside one component.
- Adding a styling library (or a second one) is an architecture decision:
  it goes through `config/workflow.md` and the report, not a lone import.

## Design tokens

- Color, spacing, typography, radii, and shadows come from tokens — CSS custom
  properties or the theme config. No raw hex codes or magic pixel values in new
  code when tokens exist. A genuinely new value becomes a token first, named
  for its role (`--color-danger`), not its appearance (`--red-2`).

## Layout

- Layout uses the framework's primitives: flex/grid utilities or their CSS.
  No ad-hoc absolute positioning to fake a layout, no fixed pixel widths on
  content containers.

## Responsive

- Responsive at the breakpoints the theme defines; no new one-off breakpoints.
- Every new layout is checked at mobile width before it is called done.

## Accessibility is a styling concern

- Focus visibility: never remove an outline without replacing it with a
  stronger focus style.
- Contrast: text meets WCAG AA against its real background, including over
  images and gradients.
- Reduced motion: animations honor the user's `prefers-reduced-motion`.
- `standards/accessibility_standards.ai.md` holds the detail:
  `bin/craft-std accessibility_standards --list`.

## CSS-in-JS (React)

- Styled Components / Emotion: styles live beside the component, props-driven
  variants over class strings, and the theme comes from `ThemeProvider` —
  never a hardcoded palette inside a styled block.
- Dynamic styling goes through CSS custom properties on the wrapper, not
  interpolated strings that generate thousands of classes.
- Server-rendered React needs the styling library's SSR extraction configured;
  a flash of unstyled content is a bug, not a quirk.
- Performance: avoid style recalculation storms — stable class names over
  per-render unique ones.

## Utility CSS (Tailwind, UnoCSS)

- Utilities compose layout; repeated groups of 4+ utilities become an
  extracted component or an `@apply` rule with a role name.
- Custom configuration (colors, spacing, breakpoints) lives in the theme
  config, mapped to design tokens. Arbitrary values (`w-[137px]`) are a smell:
  register the token instead.
- No `!important` utilities to win specificity wars — fix the layer order.

## CSS Modules, SCSS/Less, and methodology

- CSS Modules for component-scoped classes in React/Vue SFCs; the class name
  is camelCase so `styles.primaryButton` reads in templates.
- SCSS: nesting max 3 levels deep, `&` for modifiers only, variables and
  mixins imported from a tokens partial. Less follows the same rules.
- BEM where global CSS survives (legacy pages, design-system resets):
  `block__element--modifier`, one block per file, no descendant selectors
  deeper than one level.
- Theming with CSS custom properties: tokens defined at `:root`, theme
  variants override tokens, components consume `var(--token)`.

## Design systems

- MUI, Chakra, Ant Design: use the system's tokens and components before
  writing custom CSS; theme overrides go in the theme file, not ad-hoc style
  props. Wrapping a third-party component in an app-specific component keeps
  the swap-out path open.
- A custom design system exposes tokens (colors, spacing, type scale) and
  primitives (Button, Input, Modal) in one importable module; app code never
  reaches into a primitive's internals.
- Adding a design system (or a second one) is an architecture decision: it
  goes through `config/workflow.md` and the report.

## Review checklist

- New styles use the repo's one paradigm; no new styling library appeared.
- No raw hex/px where tokens exist; new values registered as role-named tokens.
- Layout from flex/grid, responsive at defined breakpoints, mobile-checked.
- Focus visible, contrast holds, motion respects reduced-motion.
