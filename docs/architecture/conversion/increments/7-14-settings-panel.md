# 7.14 Settings panel

- **Status:** in progress
- **Pull request:** [#105](https://github.com/aureliusenterprise/aurelius-atlas/pull/105)
- **Records:** DD-069 (the drawer), DD-070 (telemetry toggle semantics), DD-071
  (supersedes SHM-01: `data-theme` follows the stored choice), DD-072 (the settings
  facade and per-category owners); relies on ADR 053, DD-039, DD-046, DD-047, DD-068

Part of the [7.0 umbrella](./7-0-webapp-foundation.md), whose rules WBP-01 to WBP-07
this slice inherits. It is a **new feature**, not a port: neither the Apache Atlas
dashboards nor the legacy Aurelius shell has a settings control (verified in
`.scratch/aurelius`'s `libs/shell` header and `dashboardv2`'s `Header.html` — the
legacy header's right side is Documentation, language and account, and no theme or
settings control exists). DV-12 records it as a deliberate addition.

## Scope

A **settings panel** in the webapp: a gear in the shell header's right side opens a
**drawer** (a new `aurelius-atlas-ui` component) carrying five sections:

- **Appearance** — the theme: Auto / Light / Dark, written to the document root the
  way Bulma's scheme machinery reads it (DD-068's ramp makes Dark legible).
- **Language** — the same full-page locale navigation the header dropdown carried
  (SHC-04, DD-039); the dropdown leaves the navbar and its control moves into the
  panel, which is why the gear replaces it (the user's brief: "the button to open
  the settings can live in the app header where the language settings currently are").
- **Time zone** — the display zone for dates, chosen from the ids the server
  publishes (`GET /atlas/admin/session`'s `timezones`, ADM-05), applied through
  Angular's `DATE_TIME_ZONE` provider.
- **Table page size** — the default page size the 7.6 tables will paginate with.
- **Telemetry** — the browser telemetry on/off switch (DD-070).
- Plus an **About** footer: the app name and version (the runtime config, SHL-10 —
  the same values the footer shows, SHC-06/07) and the server version
  (`GET /atlas/admin/version`, ADM-01/DV-03).

Storage is **per-browser `localStorage`** (SPL-09). The architecture is a facade
(DD-072): a `SettingsService` facade over one **owner** service per category; the
theme's owner is the ui-lib's existing `DarkModeService`. Server-side per-user
persistence (the Keycloak profile, or the Atlas session settings ADM-05 exposes) is
a deliberate later slice — the seam is the `UserPreference` helper, so the owners'
APIs, the facade and the panel do not change when it lands.

Not in scope:

| Not delivered here                                                                    | Delivered by                                                     |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Server-side persistence of the settings                                               | a later slice, behind the `UserPreference` seam (DD-072)         |
| Date/time rendering wired to the time zone                                            | 7.6 (details) — the first screen with dates; the provider is set |
| Pagination wired to the page-size setting                                             | 7.6/7.7 — the screens that paginate                              |
| The navbar search bar (the header's other right-side control)                         | 7.4 (DD-056)                                                     |
| Runtime language switching (in-page string swap)                                      | none — one build per locale is the design (DD-039)               |
| Retiring the example app (it keeps its own header, and the `dark-mode` widget's home) | 7.10 (DV-11)                                                     |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SPL-01 | The header's right side carries a gear button (`navbar-item`, a `faGear` icon, an accessible label `shell.header.settings`) that opens the settings panel; the language dropdown (SHC-04) leaves the navbar and its control lives in the panel. Documentation (SHC-03) and account (SHC-05) are unchanged.                                                                                                                                                                                                                                                  |
| SPL-02 | `Drawer` is a dumb `aurelius-atlas-ui` component: Bulma-token styled fixed-right panel, `active` as a `model()`, a `title` heading, `ariaLabel` for the close control; `dismiss()` on the backdrop, the close button and Escape (the `Modal`'s dismissal set, card anatomy); content is projected; opening moves focus into the panel, Escape returns it. Bulma 1 ships no drawer (DD-069).                                                                                                                                                                 |
| SPL-03 | The Appearance radio writes the theme through the owner: Light/Dark set `data-theme` to `light`/`dark` on the document root; **Auto removes the attribute**, so Bulma's OS-scheme path (`:root:not([data-theme])`, DD-068's dark host) applies. An empty `data-theme` is never written — the empty attribute keeps the OS path from applying (DD-071).                                                                                                                                                                                                      |
| SPL-04 | The choice persists: the key `data-theme` in `localStorage` (the key `DarkModeService` already owns), and the stored value is applied at bootstrap, before the first render, so a returning user never sees a flash of the other scheme.                                                                                                                                                                                                                                                                                                                    |
| SPL-05 | With no stored choice, the app renders the **light** scheme under any OS preference — SHM-01's user-visible promise, kept after its mechanism is superseded (DD-071): the light default is the `DarkModeService` mode default, not the html pin.                                                                                                                                                                                                                                                                                                            |
| SPL-06 | The Language section keeps SHC-04's semantics inside the panel: the active locale (from the document's `lang`) is marked, `en-US` and `nl-NL` are listed, choosing one is a full-page navigation to `/<locale>/<current path with any locale prefix stripped>` (DD-039). The active locale is the build that is served; the panel stores no language preference.                                                                                                                                                                                            |
| SPL-07 | The Time zone section stores the chosen IANA id (`aurelius-atlas.settings.timezone`), offers the ids the server's session publishes (ADM-05) with a "Browser default" first option, and applies it through the `DATE_TIME_ZONE` provider read at bootstrap: a change takes effect on reload (DD-073). The store is browser-scoped and carries no user identity (DD-073).                                                                                                                                                                                    |
| SPL-08 | The Table page size section stores the default page size (`aurelius-atlas.settings.pageSize`, a positive integer, default 10) for the 7.6 tables to read.                                                                                                                                                                                                                                                                                                                                                                                                   |
| SPL-09 | Every setting lives in `localStorage` under a browser-scoped key — `data-theme` (SPL-04) and `aurelius-atlas.settings.*` — written only by its owner (SPL-10). This is a user experience convenience, not a data store: nothing that identifies a user, grants a permission, or belongs to the catalogue is kept there (DD-073).                                                                                                                                                                                                                            |
| SPL-10 | `SettingsService` is a facade: it exposes each category's signal and setter and delegates to exactly one **owner** service per category — theme → `DarkModeService` (ui-lib), language → `LocaleNavigationService`, time zone → `TimezoneService`, page size → `PageSizeService`, telemetry → `TelemetryService`. The owner is the sole writer of its storage key, and the panel and the bootstrap providers consume the facade/owners, never `localStorage` directly. Server-side persistence replaces a `UserPreference` owner's internals only (DD-072). |
| SPL-11 | The Telemetry switch stores its state (`aurelius-atlas.settings.telemetry`, default on). **Off** takes effect immediately: the trace and metric exporters stop sending. **On** takes effect on reload — the SDK bootstraps at startup (DD-070). The panel states this where the switch is.                                                                                                                                                                                                                                                                  |
| SPL-12 | The About section shows the app name and version from the runtime config (SHL-10, the footer's SHC-06/07 values) and the server name and version from `GET /atlas/admin/version` (ADM-01, DV-03: the name is `aurelius-atlas`).                                                                                                                                                                                                                                                                                                                             |
| SPL-13 | Every chrome string is an `@@settings.*`/`@@shell.header.settings` id with entries in both fixture locales, so the completeness gate (SHL-08) and the purity gate (DD-042/DD-048) stay green; `Drawer` ships a spec and stories (UIC-15's bar), the theme switch is verified against DD-068's dark ramp.                                                                                                                                                                                                                                                    |

## Aurelius origin

Nothing is ported. The precedents the design leans on:

- `libs/shell/src/lib/header/header.component.html` (`.scratch/aurelius`) — the
  header's right-side controls the gear joins and the language dropdown it absorbs;
  its `setLanguage()` runtime swap is not ported (DD-039: the locale builds are
  separate bundles, so SHC-04's navigation stays).
- `libs/shell/src/translations/{en-US,nl-NL}.json` — the `shell.header.*` key naming
  the new `settings.*` keys follow.
- Apache Atlas 2.4.0 `AdminResource.Session` — the `timezones` list SPL-07 offers
  (ADM-05, DV-05), and `AdminResource.Version` for SPL-12 (ADM-01, DV-03).

## Deviations

- **DV-12 (new feature):** Aurelius Atlas ships a settings panel; Apache Atlas 2.4.0
  has none (its user-facing preferences live in the dashboard's `UserSettings`
  redux store, not in the header, and are not part of the REST contract). The panel
  is part of Aurelius's own interface (ADR 053, DV-11's framing), not a port, and
  touches no Atlas endpoint.
- **DD-071 supersedes SHM-01's mechanism** (7.12): the html `data-theme="light"` pin
  is removed because it is read as an explicit choice and would outrank a stored
  Dark/Auto selection. SHM-01's promise stands — with no stored choice the app is
  light under any OS preference — delivered by the mode default (SPL-05). 7.12's own
  scope note anticipated this: "the switch is a later slice".
- **DD-073:** the settings are browser-scoped `localStorage`, not the per-user store
  Atlas's `UserSettings` was; a shared browser shares the settings. Server-side
  persistence (Keycloak profile attributes, or the Atlas session settings) is the
  follow-up slice, and is why the `UserPreference` seam exists.

## Acceptance

- Vitest (`nx test aurelius-atlas-ui -c ci`, `nx test aurelius-atlas-webapp -c ci`):
    - `drawer/drawer.component.spec.ts` — `active` model opens/closes, `dismiss()`
      on backdrop/close/Escape, `title` and `ariaLabel` render, content projected
      (SPL-02)
    - `dark-mode/dark-mode.service.spec.ts` — `setMode` writes the attribute for
      light/dark and **removes** it for auto, persists to `data-theme`, defaults to
      light (SPL-03, SPL-04, SPL-05)
    - `settings/settings.service.spec.ts` — the facade delegates each category to
      its owner and exposes it read-only (SPL-10)
    - `settings/*/*.service.spec.ts` — `UserPreference` reads and writes its key
      (SPL-09); `TelemetryService` off stops the exporters, on is deferred to
      reload (SPL-11); `TimezoneService` id list and browser-default first (SPL-07);
      `PageSizeService` positive-integer guard (SPL-08)
    - `shell/header.component.spec.ts` — the gear opens the panel, the language
      dropdown is gone from the navbar, Documentation and account unchanged (SPL-01)
    - `settings/settings-panel.component.spec.ts` — the five sections render, the
      radio drives the theme, the language links compute locale hrefs (SPL-06),
      About shows the config and server version (SPL-12)
    - `i18n-completeness.spec.ts` — every new id exists in both locales (SPL-13)
- Storybook (`nx test-storybook aurelius-atlas-ui`): `Drawer` Primary/Open/OnDark
  with `play()` tests; the theme switch flipped from the toolbar on a drawer story
  proves DD-068's ramp under `Auto` (SPL-13).
- E2E (served app, `nx e2e aurelius-atlas-webapp`): the panel's rules are
  reviewable as code through the Vitest specs above; a served-app scenario (gear →
  dark → reload stays dark) lands with the 7.10 e2e set that serves the app.
- Gate: `nx run-many -t test e2e -c ci` (levels 1 and 2), lint, build, the webapp
  purity gate, and `uv run aurelius-atlas-trace check` for the coverage rule.
