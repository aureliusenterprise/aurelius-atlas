# 7.11 Shell chrome

- **Status:** in progress
- **Pull request:** [\#102](<https://github.com/aureliusenterprise/aurelius-atlas/pull/102>)
- **Records:** ADR 053; DD-056 (supersedes the Shell half of DD-054); relies on ADR 007, ADR 018, DD-039, DD-041, DD-046, DD-047, DD-052, SHL rules (7.1), UIC rules (7.2)

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/feat-webapp-alerts-drawer/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

Port the Aurelius **application chrome** — the `libs/shell` header and footer that wrap every screen — onto the root component, replacing the 7.1 bare outlet:

- the navbar (`aurelius-atlas-ui-header`, 7.2): app name to `/search/browse`, and on the right the Documentation link, the language dropdown, and the account dropdown
- the footer: the Aurelius copyright line, app name, and version
- the session chrome over Keycloak: the signed-in identity, Keycloak's account console, and logout (the bearer-token plumbing itself is 7.3, done)

The chrome is **search-free**: the legacy navbar's centrepiece (the global search bar inside the `search` route chrome) and the primary-nav buttons stay with the search slice (7.4, on hold — DD-051). What is ported here is the frame every Aurelius screen wears, proven against the landing page (7.5).

Explicitly not delivered here, with the increment that will:

| Deferred | Lands with | Why |
| --- | --- | --- |
| Global search bar, primary-nav route buttons | Search slice (7.4, gated by server 4.1/2.3, DD-051) | Search navigation, on hold per the user's 2026-10-20 direction |
| PWA install/update buttons (`shell.header.install`, `.update`) | – (not planned) | Aurelius ships a service worker (`@angular/pwa`) and its update prompt; the port ships no service worker — chrome with no SW |
| Services dropdown (`shell.header.services`) | – (not planned) | Links to Models4Insight platform apps (Platform, Data2Model, Analytics) that are not part of Aurelius Atlas (`standalone`) |
| Loading bar and pipeline progress (shell `sticky` block) | With the slices that need them | The loading bar tracks router navigation and the pipeline tracks import jobs; the landing slice has neither to show |
| Language switch via `ngx-translate` runtime swap | – (superseded) | The locale builds are separate bundles (DD-039): switching is a full-page navigation into the locale tree the image serves |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name (`@pytest.mark.covers(..., rules=["SHC-NN"])`; TS/e2e tests name the id in the test title).

| Id | Rule |
| --- | --- |
| SHC-01 | The root component is the shell: `aurelius-atlas-ui-header` above the router outlet, the footer below it (the Aurelius root renders `<models4insight-shell>`, which wraps its `router-outlet` in exactly this chrome — SHL-03's "bare outlet" reading lands here) |
| SHC-02 | The navbar's brand is the app name from the runtime config, linking to `/search/browse` (the Aurelius logo is a product asset not vendored to this workspace; the 7.2 header's name fallback is the brand). `navbar-start` is empty: Aurelius's only primary-nav item (the `search` route) is `hidden`, so the legacy navbar renders no nav buttons for this app |
| SHC-03 | The navbar end carries the Aurelius Documentation link (`shell.header.documentation`, the Aurelius Atlas documentation site, `target="_blank" rel="noopener noreferrer"`) |
| SHC-04 | The language dropdown shows `shell.header.language` with the active locale (from the document's `lang`), and lists `en-US` and `nl-NL`; choosing one is a full-page navigation to `/<locale>/<current path with any locale prefix stripped>` — the locale builds are separate bundles (DD-039), and the image serves the locale tree (SHL-05's nginx) |
| SHC-05 | The account dropdown shows `shell.header.welcome` with the signed-in identity (`preferred_username`, falling back to `email`, read from the Keycloak token); its items are `shell.header.security` (opens Keycloak's account console) and `shell.header.logout` (ends the Keycloak session). No login button is ported: every route sits behind the root guard (APC-05), so the legacy logged-out navbar is unreachable |
| SHC-06 | The footer renders the `shell.footer.copyright` label, a copyright icon, the copyright year, the app name, and the app version — the Aurelius footer anatomy — with every value from the runtime config (`/config.json`), not an `environment.ts` (SHL-10, DD-041) |
| SHC-07 | Every chrome string carries its legacy `libs/shell` dictionary key as its i18n id (`@@shell.header.*`, `@@shell.footer.*`); the shell dictionaries (en, nl) are vendored as fixtures and bridged into the XLIFF catalogues beside the app and components dictionaries (SHL-08, UIC-04's category), and the completeness spec proves both locales |
| SHC-08 | The chrome is zoneless/Angular-idiom (standalone, OnPush, signals, `inject()`): the identity is a signal read from the Keycloak client at construction (the guard has resolved before any render), session actions call the Keycloak client directly, no store, no `BehaviorSubject` (DD-046, purity gate). The client is the `Keycloak` (keycloak-js) instance `provideKeycloak` registers — keycloak-angular v21's `KeycloakService` is the deprecated pre-v19 class and is not provided by it |
| SHC-09 | e2e (authenticated, chromium/firefox/webkit): the navbar shows the welcome line with the signed-in user (`aurelius-writer`); the language dropdown's `nl-NL` item navigates the page into the Dutch build (a real click, not a hand-written URL — the locale-tree channel proven end to end); the footer shows copyright year, app name, and version; the Documentation link points at the Aurelius docs with `rel="noopener noreferrer"` |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit pinned by 7-0), `libs/shell/src/lib/`:

- `shell.component.{ts,html}` — the chrome layout (header, outlet, footer; the sticky loading/pipeline block is not ported)
- `header/header.component.{ts,html}` — the navbar: brand, nav buttons (deferred), documentation, language dropdown, account dropdown, services/install/update (not planned); the session actions come from `libs/authentication`, here from Keycloak directly (DD-052)
- `footer/footer.component.{ts,html}` — copyright icon, app name, version
- `shell-config.service.ts` — the `shell` block of `environments/environment.ts` (appName, appCopyright, appLogoPath, standalone): its role moves to `/config.json` (SHL-10); `standalone`/`hideDocumentation` are config knobs Aurelius never flipped for atlas — not ported as flags, the atlas choices are baked (documentation shown, services hidden)
- `src/translations/{en-US,nl-NL}.json` — the chrome strings (SHC-07)

## Deviations

Against Apache Atlas: none — this is an Aurelius product frame, Atlas has no UI.

Against the Aurelius product, recorded in [design-log](<https://aureliusenterprise.github.io/feat-webapp-alerts-drawer/architecture/conversion/design-log/index.md>):

- DD-056: the navbar is static, not `is-fixed-top` (the legacy pinned-to-top bar is cosmetic; the port keeps the Bulma navbar in flow), the login button is not ported (SHC-05), the language switch navigates (SHC-04), and the root composes the chrome directly — the Aurelius `Shell` module, its service (token-refresh-on-focus — keycloak-angular owns refresh, DD-052) and its reusable-route strategy are not ported (SHC-01, DD-046).

## Acceptance

- Vitest (`nx test aurelius-atlas-webapp -c ci`):

  - `app.component.spec.ts` — root renders header, outlet, footer (SHC-01); the old "bare outlet" spec is superseded here
  - `shell/header.component.spec.ts` — brand from config (SHC-02), documentation link (SHC-03), language items and computed locale hrefs (SHC-04), welcome line, Account-security and Logout actions on the Keycloak client (SHC-05), strings render from the bridge keys (SHC-07)
  - `shell/footer.component.spec.ts` — copyright/appName/version from `AppConfig` (SHC-06)
  - `session.service.spec.ts` — identity from the token, fallback to e-mail (SHC-08)
  - `config.spec.ts` — the new `appName`/`appCopyright`/`appVersion` fields validate and fail loudly when missing (SHL-02)
  - `i18n-completeness.spec.ts` — the shell fixtures join the parity check (SHC-07)
- e2e (`nx e2e aurelius-atlas-webapp`): the SHC-09 scenarios; the 7.1/7.5 scenarios stay green (the landing keeps its anchors inside the new frame)
- Purity gate green (SHC-08); example app untouched.
