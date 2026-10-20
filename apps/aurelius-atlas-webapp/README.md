# aurelius-atlas-webapp

The Aurelius Atlas webapp: the legacy Aurelius interface (Angular 17,
`aureliusenterprise/aurelius` `apps/atlas`) rewritten in Angular idiom, slice by
slice, on Angular 22. Per [ADR 053](../../docs/architecture/adr/053-the-webapp-is-rewritten-in-angular-idiom-slice-by-slice.md)
this is a rewrite, not a transplant: zoneless, standalone, signals — the
legacy NgModules, `@models4insight/*` libs, custom Redux state, and
ngx-translate are never ported (enforced by `scripts/check-webapp-purity.sh`).

The increment ledger for this track is the 7.x series:
[7-0 foundation](../../docs/architecture/conversion/increments/7-0-webapp-foundation.md),
[7-1 shell](../../docs/architecture/conversion/increments/7-1-webapp-shell.md),
[7-3 API client + auth](../../docs/architecture/conversion/increments/7-3-api-client-auth.md).

## Features (slice 7.1 — shell + localisation)

- `bootstrapApplication` + `provideZonelessChangeDetection`; no `NgModule`
- Runtime config: `/config.json` is fetched and validated into the typed
  `AppConfig` at bootstrap (`src/app/config.ts`); a missing or malformed file
  fails loudly. Only the development build bundles it (`dev/config.json`)
- Root component renders a bare `<router-outlet />`, as the Aurelius root does;
  `''` redirects to `/search/browse` (the Aurelius default destination), `'**'`
  falls back to it, scroll position is restored on back/forward
- `en-US` and `nl-NL` builds; the full Aurelius dictionary (495 leaves / 105
  key trees) is bridged into XLIFF catalogues keyed by the legacy dotted paths
  (`@@search.browse.description`), verified by `i18n-completeness.spec.ts`
- Static nginx image (`dhi.io/nginx`, TLS 8080) serving the locale tree with
  same-origin `/api/` and `/otel/` proxies, CSP `connect-src 'self'`
- OpenTelemetry: traces and Core Web Vitals metrics exported via
  `otelExporterUrl` (`/otel/v1/traces`), uncaught errors recorded as span
  events, and `traceparent` propagated on HTTP calls — all through
  `aurelius-atlas-observability`, replacing the Aurelius Google Analytics and
  clickstream paths (DD-040)

Not wired yet by design: the shared UI components (7.2), the header/search bar
and the search client (7.4, DD-051), and server-side token verification
(6.1 — the bearer token rides from day one and is inert until then, DD-052).

## Features (slice 7.3 — API client + auth wiring)

- Auth: `keycloak-angular` with `check-sso` + silent-SSO
  (`public/silent-check-sso.html`); every route sits behind a root
  `createAuthGuard` whose guard redirects to Keycloak login with the current
  URL as `redirect_uri` (APC-05, DD-052 — replacing the Aurelius
  `libs/authentication` wholesale)
- Bearer token on `/api` via `includeBearerTokenInterceptor`; refresh is
  keycloak-angular's, the legacy `updateToken` loop is not ported (APC-06,
  APC-07, DD-004's in-memory token store)
- REST client: `aurelius-atlas-data-access`'s `TypeDefsService` and
  `AdminService` type the live server surface (typedefs + admin, DD-051); the
  client composes `${apiBaseUrl}/atlas/v2/...` — the Aurelius
  deployment-proxy coupling is not ported (APC-01, DD-050), so the dev proxy
  and the nginx image forward `/api` untouched (APC-08)
- Keycloak dev origins for 4300/4301 (serve) and 18444 (e2e) on the shared
  `aurelius` client (APC-09)

## Running

```bash
nx serve aurelius-atlas-webapp          # http://127.0.0.1:4300 (nl-NL: config nl-NL, port 4301)
```

The serve target starts its pair first: `aurelius-atlas-server` (:21000) and
Keycloak (:8080) come up via `dependsOn`, so a cold `nx serve` lands on the
Keycloak sign-in page and returns to the app after you sign in as
`aurelius-writer` (the dev-keycloak users). The dev server proxies `/api` →
:21000 and `/otel` → 4318 (HTTPS, verified against the local CA via
`NODE_EXTRA_CA_CERTS` from `.env.enc` — ADR 039); `/api` forwards with the
prefix intact (DD-050). `/config.json` is served from `dev/` (development build
only).

## Testing

```bash
nx test aurelius-atlas-webapp -c ci       # Vitest; runs check-purity first, never without -c ci
nx lint aurelius-atlas-webapp
nx run aurelius-atlas-webapp:check-purity # the legacy-construct gate (WBP-02)
nx e2e aurelius-atlas-webapp              # Playwright (chromium, firefox, webkit) against the image
nx extract-i18n aurelius-atlas-webapp     # refresh src/locale/messages.xlf (see below)
```

The XLIFF catalogues under `src/locale/` are **generated** from the vendored
legacy dictionaries (`tests/fixtures/*.json`) by
`tools/generate-legacy-catalogue.mjs` — run that after touching them, and keep
the completeness spec green. `nx extract-i18n` regenerates the template
catalogue from templates only; the bridge files are the source of truth for
dictionary keys (DD-039).

The e2e stack runs the **real** Atlas server container behind the nginx `/api/`
proxy on the dev Elasticsearch network (DD-053), with Keycloak on the host
stack. Every page test signs in through the `authenticated` fixture
(`AURELIUS_ATLAS_WEBAPP_USERNAME`/`_PASSWORD` from `.env.enc`, the
`aurelius-writer` dev user); changing `dev/keycloak/import/master.json` needs a
full keycloak recreation (`docker compose -f dev/keycloak/docker-compose.yaml
down -v && up -d`) — Keycloak imports do not overwrite an existing realm.

## Deployment

The image serves each locale from its own directory with
`<base href="/<locale>/">`; the shipped `nginx.conf.template` (baked at
`/etc/nginx/conf.d/default.conf`) is a **template**: the
`${AURELIUS_ATLAS_WEBAPP_*}` placeholders (API/OTLP/Keycloak upstreams, TLS
names, trust anchor, DNS resolver) are resolved by the deployment, which mounts
a filled-in copy over that path. Unresolved placeholders make nginx fail at
startup instead of serving with template values (same pattern as the example
app; see its README for the envsubst/kustomize recipe). E2E ships such a
filled-in copy at `e2e/config/nginx.conf` (TLS + verified proxies, ADR 039).
