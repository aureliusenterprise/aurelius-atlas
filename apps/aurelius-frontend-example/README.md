# aurelius-frontend-example

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

- `aurelius-ui` — presentational Bulma components
- `aurelius-data-access` — typed HTTP + SSE client for the backend
- `aurelius-observability` — browser OpenTelemetry setup
- `@aurelius/brand` (`libs/styles/aurelius-brand`) — SCSS design tokens

## Running

```bash
nx serve aurelius-frontend-example
```

Serves on `http://localhost:4200` with a dev proxy: `/api` → the FastAPI backend on
port 8000 (prefix stripped) and `/otel` → the OTLP collector on port 4318. Both
upstreams are HTTPS and verified against the local CA — the proxy trusts it via
`NODE_EXTRA_CA_CERTS` from the project `.env` (`nx certgen`, ADR 039). The
developer browser stays on plaintext HTTP on 4200.

## Testing

```bash
nx test aurelius-frontend-example -c ci      # Vitest unit tests
nx e2e aurelius-frontend-example             # Playwright (chromium, firefox, webkit)
nx extract-i18n aurelius-frontend-example    # refresh translation bundles
```

## Deployment

The production Docker image is a static nginx serve (`dhi.io/nginx`, port 8080);
`/config.json` is supplied at deploy time instead of being baked in.

The image includes the locale-aware nginx config for `/en-US/` and `/nl-NL/`, the
preferred-language redirect at `/`, and localized SPA fallbacks. Keep these
application-serving rules in the image. Supply TLS and backend routing through
deployment infrastructure, or mount optional nginx fragments at
`/etc/nginx/app.d/*.conf`. These fragments are included inside the existing
`server` block, so they must not define another `server` or an HTTP-level `map`.

E2E runs the same image configuration. Compose mounts `e2e/config/nginx.conf`
E2E replaces the image's site config with `e2e/config/nginx.conf` (mounted at
`/etc/nginx/conf.d/default.conf`): the same locale-serving rules, but with
`listen ssl` using the frontend's certificate and TLS-verified `/api/` and
`/otel/` proxies — E2E always runs over TLS (ADR 039). Tests also get the
runtime `config.json`. Tests use `/en-US/` and check the root locale
redirects and SPA fallbacks for both locales. Neither nginx configuration is used
by `nx serve`, which runs Angular's development server.
