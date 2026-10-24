# aurelius-atlas-webapp

The Aurelius Atlas webapp — the legacy Aurelius interface rewritten in Angular
idiom, slice by slice (ADR 053, conversion increments 7.x). This file covers
wiring specific to this app; workspace-wide rules live in the root `AGENTS.md`
and the increment specs in `docs/architecture/conversion/increments/`.

## Layout

- `src/app/` — standalone, zoneless components; `app.config.ts` wires providers
  (config, router, Keycloak auth + bearer interceptor, OpenTelemetry via
  `aurelius-atlas-observability`), `routes.ts` the guarded shell routes
  (`createAuthGuard` + `rootAuthGuard` → Keycloak login), `config.ts` is the
  typed `/config.json` shape
- `public/silent-check-sso.html` — the silent-SSO redirect page (hash-pinned in
  the nginx CSP; served at the origin root, keyed to it by `keycloakInitOptions()`)
- `src/locale/` — **generated** XLIFF catalogues (the Aurelius dictionary bridge,
  DD-128); regenerate with `node tools/generate-legacy-catalogue.mjs`, never hand-edit
- `tests/fixtures/` — the vendored legacy dictionaries (parity reference, SHL-08)
- `scripts/check-webapp-purity.sh` — the legacy-construct gate (WBP-02); runs as a
  `dependsOn` of `test`, so CI enforces it
- `dev/config.json` — runtime config, bundled **only** in the development build
- `proxy.conf.json` — dev-server proxy: `/api` → atlas-server :21000 (**no
  rewrite** — the client composes the `/api` prefix, DD-139), `/otel` → 4318
  (HTTPS, CA-verified)
- `e2e/` — pytest + Playwright (chromium, firefox, webkit) against the built
  image, with the real atlas-server container behind nginx `/api/` (DD-142) and
  Keycloak sign-in via the `authenticated` fixture (APC-10)

## Porting rules (every slice)

- Read the increment spec in `docs/architecture/conversion/increments/` first;
  implement its rule ids with `@pytest.mark.covers`-style traceability on the
  tests (`@pytest.mark.covers` is Python; TS tests cite the rule id in the test name).
- Angular idiom only: signals for state, standalone components, `inject()`,
  zoneless. The purity gate blocks NgModules, `@models4insight/`, ngx-translate,
  `environment.ts`, and state-owning `BehaviorSubject`s — do not loosen it to land code.
- Dictionary strings: reference the existing XLIFF ids (`@@a.b.c`); never add
  strings to components that aren't in the catalogue — extend the fixtures and
  regenerate when the legacy app gains keys.
- The legacy source for parity comparison is the clone at
  `.scratch/aurelius` (commit-pinned; see 7-0 spec).

## Commands

```bash
nx serve aurelius-atlas-webapp          # 4300 (nl-NL: -c nl-NL → 4301); long-running, run detached
                                        # serves the pair: atlas-server + keycloak start via dependsOn
nx test aurelius-atlas-webapp -c ci     # never without -c ci (watch mode hangs)
nx run aurelius-atlas-webapp:check-purity
nx lint aurelius-atlas-webapp
nx e2e aurelius-atlas-webapp            # builds webapp + atlas-server images; keycloak/observability/
                                        # elasticsearch stacks up first (needs Docker + SOPS key)
nx extract-i18n aurelius-atlas-webapp   # template catalogue refresh only (bridge files are source of truth)
```

Offline-safe: `test -c ci`, `lint`, `check-purity`, `extract-i18n`,
`docker-build`. Needs the SOPS key: `serve`, `e2e`. Needs Docker: `serve`, `e2e`.

## Conventions

- Components stay presentational; state in signal stores under the feature
  folder; HTTP only via `aurelius-atlas-data-access` services (`TypeDefsService`,
  `AdminService` — 7.3's live surface; search types arrive with 7.4, DD-140).
- Auth is `keycloak-angular` only: the root guard + `check-sso`/silent-SSO, and
  `includeBearerTokenInterceptor` on `/api`. Never hand-write an `updateToken`
  loop (APC-07) and never store tokens outside keycloak-js's own memory (DD-004).
  The OTLP exporters are the one non-`/api` authenticated leg: they ride the
  user's own token through `createAureliusOtelIngestAuth`'s headers factory
  (aurelius-atlas-observability, DD-103) —
  the collector's browser receiver validates it via OIDC; token-less (logged-out)
  pushes 401 by design.
- Every new component gets a Storybook story (7.2 wires the ui library pattern);
  every new route gets an e2e scenario.
- Template strings carry `i18n="@@legacy.key"` markers matching the catalogue ids.

## Removal

The webapp is a conversion-track app: removing it means stopping the 7.x
roadmap. Remove together: its `mkdocs.yaml` nav entry (none yet), the 7.x
roadmap rows in `docs/architecture/conversion/index.md`, and the clone
reference in `docs/architecture/conversion/increments/7-0-webapp-foundation.md`.
Auth removal: the `provideKeycloak`/`INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG`
providers, `createAuthGuard` wrapper and `rootAuthGuard` in `routes.ts`,
`public/silent-check-sso.html`, the Keycloak locations in the nginx configs, the
webapp-port origins on the `aurelius` client in
`dev/keycloak/import/master.json`, and the `authenticated` fixture in
`e2e/conftest.py` (the example app shares the client, so the Keycloak import
entry stays as long as the example lives).
The example app (`aurelius-atlas-frontend-example`) stays — it is the pattern
reference and spine member; the webapp only replaces it once 7.x completes.
