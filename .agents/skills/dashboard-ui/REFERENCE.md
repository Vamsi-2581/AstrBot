# Dashboard UI reference

Condensed library facts behind [SKILL.md](./SKILL.md). Version deltas from this
repo's `dashboard/package.json` are called out; the upstream citations come from
the skill sources listed under **Sources**. When a fact conflicts with the
installed version, trust the installed package and `dashboard/src/design/theme.ts`.

## Table of contents

- [Vuetify 4](#vuetify-4)
- [Customization layers](#customization-layers)
- [Which table component](#which-table-component)
- [Vue 3.5](#vue-35)
- [Pinia 4](#pinia-4)
- [vue-router 5](#vue-router-5)
- [Testing (Vitest 5)](#testing-vitest-5)
- [Common red flags](#common-red-flags)
- [Vuetify MCP](#vuetify-mcp)
- [Sources](#sources)

## Vuetify 4

Upstream skill targets `vuetify@4.0.1`; this repo pins `4.2.4`, so the 4.0
breaking changes below still apply.

- Environment: Vue `^3.5.0` peer, ESM only, modern browsers, minimum design
  width 320px. Default font is Roboto and the default icon set is `mdi`
  (`@mdi/font`). This repo ships a subset MDI CSS at
  `dashboard/src/assets/mdi-subset/`.
- Setup: `createVuetify()` returns `{ install, unmount, defaults, display,
theme, icons, locale, date, goTo }`; `app.use(vuetify)` and a single
  `<v-app>` root are required. Components resolve through the plugin — without
  `app.use(vuetify)` Vue renders unknown empty tags with no error.
- With `vite-plugin-vuetify`, components tree-shake automatically and
  `vuetify/styles` is not imported by hand. This repo imports `vuetify/styles`
  in `src/plugins/vuetify.ts` and registers all components only in test mode
  (Vitest does not run the SFC transform).
- Breakpoints (v4): `sm 600`, `md 840`, `lg 1145`, `xl 1545`, `xxl 2138` — not
  the common CSS `768/960`. Use `useDisplay()` for responsive logic and grid
  props for responsive layout.
- `density` values are `default | comfortable | compact` (not numeric).
  `dense` is gone; the repo default is `compact` for inputs.
- Elevation was reduced to levels `0-5` in v4. The repo design-system guard
  caps template `elevation` at `4`; `VCard` defaults to `0`, `VSnackbar` to `4`.
- Typography variants renamed: `h1-h3` → `display-*`, `h4-h6` → `headline-*`,
  `subtitle-1`/`body-1` → `body-large`, `caption` → `body-small`,
  `button`/`subtitle-2` → `label-large`.
- Grid uses CSS `gap`; `dense` → `density="compact"`, and
  `align`/`justify`/`order`/`align-self` props are now utility classes. `VRow`
  gained a `gap` prop.
- `VSelect`/`VCombobox`/`VAutocomplete` slot `item` renamed to `internalItem`
  (`item` is now an alias for `internalItem.raw`). `VForm` slot values
  (`isValid`, `errors`, ...) are unwrapped, no longer refs.
- Defaults merging skips `undefined`; use `null` to override a global default.
- Styles ship in cascade layers (`vuetify-core`, `vuetify-components`,
  `vuetify-overrides`, `vuetify-utilities`, `vuetify-final`); unlayered user
  CSS now wins over Vuetify. This repo's overrides live in
  `dashboard/src/styles/vuetify-overrides.scss` and `dashboard-shell.css`.
- Labs components are not production ready and import from `vuetify/labs/*`
  (e.g. `VDateInput`, `VFileUpload`, `VPicker`, `VCommandPalette`). Prefer a
  stable component unless a lab is already used nearby.
- Pitfalls: missing MDI subset → blank icons; custom CSS breaking styles →
  layer order; `VNumberInput` uses `toFixed()` internally; never import
  `vuetify/styles` from a SASS file (use `vuetify` or `vuetify/settings`).

## Customization layers

Pick the layer that owns the property; reaching for a stylesheet override
(especially `!important`) usually means the property was available a layer up.

| What you are changing                     | Layer                                                   |
| ----------------------------------------- | ------------------------------------------------------- |
| Colours, dark mode                        | `theme` in `src/design/theme.ts`, read via `useTheme()` |
| Default props everywhere                  | `defaults` in `src/plugins/vuetify.ts`                  |
| Default props for one subtree             | `v-defaults-provider` (merges, innermost wins)          |
| Radius, heights, fonts — CSS-level values | SASS variables under `src/styles/`                      |
| One internal element of a component       | Its named slot                                          |
| Arrangement of several components         | Ordinary template composition                           |

`theme.variations` auto-generates `primary-lighten-1`, `primary-darken-2`, and
so on; do not declare those by hand. Colours are also reachable in CSS as
`rgb(var(--v-theme-primary))`.

## Which table component

```text
Static rows, no interaction        → v-table
Local sort/filter/page             → v-data-table
Server owns sort/page              → v-data-table-server (separate component)
Thousands of rows, no paging       → v-data-table-virtual (height required)
Rows grouped under headings        → v-data-table with group-by
```

Customise columns with `v-slot:item.<key>` matching the header `key`; keep the
headers array in `<script>`, not inline in the template.

## Vue 3.5

Upstream skill tracks the 3.6 beta; this repo is on `3.5.43`, so 3.6 Vapor Mode
notes are informational only.

- `<script setup lang="ts">`, Composition API, TypeScript by default.
- Reactive props destructure and `defineModel` are available:
  `const { count = 0 } = defineProps<{ count?: number }>()`.
- `useTemplateRef('name')` (3.5+) is the current template-ref pattern.
- `onWatcherCleanup` (3.5+) pairs with `watch` for aborting in-flight work.
- Composable inputs accept value/ref/getter via `MaybeRefOrGetter<T>` +
  `toValue()`.
- Reactivity Transform (`$ref`, `$computed`) was removed in 3.4 — use plain
  `ref`/`computed`. Global `JSX` namespace is no longer registered.
- Avoid unnecessary re-renders: derive with `computed`, watch narrow sources,
  and keep entry/route views as composition surfaces.

## Pinia 4

Repo pins `pinia@4.0.3`.

- ESM only; `@vue/devtools-api` is a required peer install.
- Define stores with `defineStore('id', ...)`. The object-only
  `defineStore({ id, ... })` signature was removed (v3).
- Option stores: `state` / `getters` / `actions`. Setup stores: `ref` →
  state, `computed` → getter, functions → actions; return every state property
  or SSR/devtools break.
- `storeToRefs(store)` for destructuring state/getters (actions can be
  destructured directly). `$reset()` exists only on option stores.
- Call `useStore()` inside setup/composables, not at module scope; outside a
  component pass the pinia instance.
- Repo examples: `dashboard/src/stores/{appearance,auth,common,customizer,
promptStore,routerLoading,toast}.ts` — all option stores.

## vue-router 5

Repo pins `vue-router@5.4.0` and uses classic routes with
`createWebHashHistory` (`dashboard/src/router/index.ts`, route modules in
`src/router/`). File-based routing is not used.

- Guards **return** a value; `next()` is deprecated. Return `{ name }`, a path,
  `false`, or nothing.
- `router.currentRoute` is a `ShallowRef` — read `.value`. `onReady()` does not
  exist; `await router.isReady()`.
- `scrollBehavior` returns `{ top, left }` (not `x`/`y`).
- Detect failed navigations with `isNavigationFailure(...)`.
- `route.meta` merges non-recursively; read `to.meta.<key>` directly.
- Decouple components with route `props: true`; watch narrow sources
  (`() => route.params.id`) rather than the whole `route`.

## Testing (Vitest 5)

- Config: `dashboard/vitest.config.ts` — `jsdom`, setup
  `dashboard/tests/setup.vitest.ts`, include `dashboard/tests/**/*.{vitest.ts,test.mjs}`.
- Coverage is v8 over `src/**/*.ts` (excluding generated OpenAPI, `*.d.ts`,
  `main.ts`, `views/**`, `router/index.ts`, `plugins/**`, and a few utils) with
  thresholds lines 93 / functions 95 / statements 92. SFC smoke tests live under
  `dashboard/tests/` and are outside that denominator.
- Mount components with `@vue/test-utils` `mount`. `restoreMocks` and
  `clearMocks` are on.
- Run `pnpm test` (collection check + Vitest + node tests), `pnpm test:vitest`
  (Vitest only), `pnpm test:design-system` (guard + theme tests), and
  `pnpm test:e2e` (Playwright) from `dashboard/`.

## Common red flags

- No `app.use(vuetify)`, or a component used outside a `<v-app>` root.
- `v-col` without a `v-row` parent, or `v-row` outside `v-container`.
- Inline `headers`/`items` arrays on `v-data-table` (re-render every parent
  render).
- `v-data-table` with hand-rolled server paging instead of
  `v-data-table-server`; `v-data-table-virtual` without `height`.
- `v-if` on a dialog/drawer (destroys state and transition) instead of
  `v-model`.
- `theme.variations` colours declared by hand.
- A raw `#hex`/`rgb()`/named colour or inline `style` in a template — the
  design-system guard fails the build.

## Vuetify MCP

The official Vuetify MCP server (`vuetifyjs/mcp`, npm `@vuetify/mcp`, MIT)
serves live Vuetify component/API docs and install/upgrade guides. It is a
client-level tool, not a repository artifact — configure it in the agent
client, never commit secrets.

This checkout configures the hosted, no-auth endpoint for OpenCode in the
local, gitignored `.opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "vuetify": {
      "type": "remote",
      "url": "https://mcp.vuetifyjs.com/mcp",
      "enabled": true
    }
  }
}
```

Codex CLI reads MCP servers from `~/.codex/config.toml`; use the local stdio
form there (or the equivalent streamable-HTTP form when the installed Codex
supports it):

```toml
[mcp_servers.vuetify-mcp]
command = "npx"
args = ["-y", "@vuetify/mcp"]
```

- Endpoints: `https://mcp.vuetifyjs.com/mcp` (public docs, no auth);
  `https://mcp.vuetifyjs.com/one` needs Vuetify One OAuth — do not paste an API
  key there.
- Local fallback: `npx -y @vuetify/mcp` (stdio). Interactive setup:
  `npx -y @vuetify/mcp config --remote`.
- Restart the client after editing MCP config; it is loaded at startup.
- Prefer the MCP for exact Vuetify 4 API/prop questions and v3→v4 migration
  lookups; keep this skill's design-system and theme-token rules authoritative
  for this repository.

## Sources

The skill fuses these MIT-licensed agent skills, reviewed at the commits below
and rewritten as an AstrBot overlay; no upstream file is vendored verbatim.

| Upstream                                                                                                | Reviewed commit                            | License | Absorbed                                         |
| ------------------------------------------------------------------------------------------------------- | ------------------------------------------ | ------- | ------------------------------------------------ |
| `skilld-dev/vue-ecosystem-skills` (`vuetify-skilld`, `vue-skilld`, `pinia-skilld`, `vue-router-skilld`) | `c60d4ccc466a8ca2694cbb089fdd3b3d97b78961` | MIT     | version-correct API facts, migration notes       |
| `vuejs-ai/skills` (`vue-best-practices`)                                                                | `c9d355ff23f654309dd02006be671859df0a134c` | MIT     | workflow, boundaries, split triggers, self-check |
| `agents-inc/skills` (`web-ui-vuetify`)                                                                  | `3a51ef571e996b18294bf776d53dbdad26de0617` | MIT     | three-layer model, table chooser, red flags      |
| `antfu/skills` (`vue`, `pinia`, `vitest`)                                                               | `feb0f3aba6566426f12230e7fc7a10d97c1293bb` | MIT     | concise preferences, testing notes               |

`vuetifyjs/0` (vuetify0) and `vuetifyjs/mcp` were reviewed and not adopted:
this repo uses standard Vuetify components, not the headless `vuetify0` engine,
and the MCP server is a client-level configuration rather than a repository
artifact.

Official docs: <https://vuetifyjs.com>, <https://vuejs.org>,
<https://pinia.vuejs.org>, <https://router.vuejs.org>, <https://vitest.dev>.
