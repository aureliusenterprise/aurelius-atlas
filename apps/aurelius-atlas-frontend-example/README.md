# aurelius-atlas-frontend-example

Example Angular 22 single-page app demonstrating the Aurelius frontend pattern:
a zoneless, standalone-component SPA protected by Keycloak, talking to the FastAPI
backend and exporting browser telemetry through OpenTelemetry.

Part of the template **spine**.

## Features

- The whole app sits behind one Keycloak-guarded root route (`createAuthGuard` with
  login redirect)
- Entity search with debounced queries and pagination, plus an entity editor
- Runtime config: `/config.json` (Keycloak client/realm, `apiBaseUrl`, `otelExporterUrl`)
  is fetched and validated at bootstrap and only bundled in the development build
  (`dev/config.json`); a missing or malformed file fails loudly instead of blank-screening
- `provideAureliusOpenTelemetry()` traces exported via the configured `otelExporterUrl`
  (`/otel/v1/traces` in dev); API calls use the configured `apiBaseUrl` (`/api`) with a
  bearer-token interceptor attached to `/api/*` calls

## Workspace dependencies

- `aurelius-atlas-ui` — presentational Bulma components
- `aurelius-atlas-data-access` — typed HTTP + SSE client for the backend
- `aurelius-atlas-observability` — browser OpenTelemetry setup
- `@aurelius/atlas-brand` (`libs/styles/aurelius-atlas-brand`) — SCSS design tokens

## Running

```bash
nx serve aurelius-atlas-frontend-example
```

Serves on `http://localhost:4200` with a dev proxy: `/api` → the FastAPI backend on
port 8000 (prefix stripped) and `/otel` → the OTLP collector on port 4318. Both
upstreams are HTTPS and verified against the local CA — the proxy trusts it via
`NODE_EXTRA_CA_CERTS` from the project `.env` (`nx certgen`, ADR 039). The
developer browser stays on plaintext HTTP on 4200.

## Testing

```bash
nx test aurelius-atlas-frontend-example -c ci      # Vitest unit tests
nx e2e aurelius-atlas-frontend-example             # Playwright (chromium, firefox, webkit)
nx extract-i18n aurelius-atlas-frontend-example    # refresh translation bundles
```

## Deployment

The production Docker image is a static nginx serve (`dhi.io/nginx`, port 8080);
`/config.json` is supplied at deploy time instead of being baked in.

The image ships its locale-aware nginx config (for `/en-US/` and `/nl-NL/`, the
preferred-language redirect at `/`, and localized SPA fallbacks) as a template
(`nginx.conf.template`, baked at `/etc/nginx/conf.d/default.conf`). The
`${AURELIUS_ATLAS_FRONTEND_*}` placeholders — backend topology
(`API_UPSTREAM[_NAME]`, `OTEL_UPSTREAM[_NAME]`), the upstream trust anchor
(`TLS_CA_FILE`), the DNS resolver (`DNS_RESOLVER`) and the Keycloak origins in
the CSP (`KEYCLOAK_ORIGINS`) — are resolved **by the deployment**: mount a
filled-in copy over `/etc/nginx/conf.d/default.conf` (envsubst, sed,
kustomize — anything that writes a file). Unresolved placeholders make nginx
fail at startup rather than serve with template values. Add per-deployment
extras as fragments at `/etc/nginx/app.d/*.conf` — fragments are included
inside the existing `server` block, so they must not define another `server`
or an HTTP-level `map`.

E2E ships exactly such a filled-in copy: Compose mounts `e2e/config/nginx.conf`
(a static file with the stack's values hard-filled) at
`/etc/nginx/conf.d/default.conf`: the same locale-serving rules, but with
`listen ssl` using the frontend's certificate and TLS-verified `/api/` and
`/otel/` proxies — E2E always runs over TLS (ADR 039). Tests also get the
runtime `config.json`. Tests use `/en-US/` and check the root locale
redirects and SPA fallbacks for both locales. Neither nginx configuration is used
by `nx serve`, which runs Angular's development server.
