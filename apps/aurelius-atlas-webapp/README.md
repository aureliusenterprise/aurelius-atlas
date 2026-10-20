# aurelius-atlas-webapp

The Aurelius Atlas webapp: the legacy Aurelius interface (Angular 17,
`aureliusenterprise/aurelius` `apps/atlas`) rewritten in Angular idiom, slice by
slice, on Angular 22. Per [ADR 053](../../docs/architecture/adr/053-the-webapp-is-rewritten-in-angular-idiom-slice-by-slice.md)
this is a rewrite, not a transplant: zoneless, standalone, signals — the
legacy NgModules, `@models4insight/*` libs, custom Redux state, and
ngx-translate are never ported (enforced by `scripts/check-webapp-purity.sh`).

The increment ledger for this track is the 7.x series:
[7-0 foundation](../../docs/architecture/conversion/increments/7-0-webapp-foundation.md),
[7-1 shell](../../docs/architecture/conversion/increments/7-1-webapp-shell.md).

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

Not wired yet by design: Keycloak auth (7.3), the REST
client (7.3), shared UI components (7.2), the header/search bar (7.4).

## Running

```bash
nx serve aurelius-atlas-webapp          # http://127.0.0.1:4300 (nl-NL: config nl-NL, port 4301)
```

The dev server proxies `/api` → 8000 and `/otel` → 4318 (HTTPS, verified
against the local CA via `NODE_EXTRA_CA_CERTS` from `.env.enc` — ADR 039).
`/config.json` is served from `dev/` (development build only).

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

## Deployment

The image serves each locale from its own directory with
`<base href="/<locale>/">`; the shipped `nginx.conf.template` (baked at
`/etc/nginx/conf.d/default.conf`) is a **template**: the
`${AURELIUS_ATLAS_WEBAPP_*}` placeholders (API/OTLP upstreams, TLS names,
trust anchor, DNS resolver) are resolved by the deployment, which mounts a
filled-in copy over that path. Unresolved placeholders make nginx fail at
startup instead of serving with template values (same pattern as the example
app; see its README for the envsubst/kustomize recipe). E2E ships such a
filled-in copy at `e2e/config/nginx.conf` (TLS + verified proxies, ADR 039).
