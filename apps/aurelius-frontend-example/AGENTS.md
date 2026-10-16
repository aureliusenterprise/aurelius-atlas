# aurelius-frontend-example

Example Angular SPA. This file covers wiring specific to this app; workspace-wide
rules live in the root `AGENTS.md`.

## Layout

- `src/app/` — standalone, zoneless components; `app.config.ts` wires providers
  (Keycloak, OpenTelemetry, interceptors); routes in `app.routes.ts`
- `dev/config.json` — runtime Keycloak config, bundled **only** in the development
  build (see `build.configurations.development.assets` in `project.json`)
- `proxy.conf.json` — dev-server proxy: `/api` → backend on 8000 (prefix stripped),
- `proxy.conf.json` — dev-server proxy: `/api` → backend on 8000 (prefix
  stripped), `/otel` → OTLP collector on 4318. Both upstreams are HTTPS with
  verification; the proxy trusts the local CA via `NODE_EXTRA_CA_CERTS`
  (`.env.enc`) — ADR 039
- `e2e/` — pytest + Playwright (chromium, firefox, webkit)

## Configuration

- Runtime config comes from `/config.json`, fetched and validated at bootstrap
  (`src/app/config.ts` defines the typed `AppConfig` shape). It carries the Keycloak
  client/realm, `apiBaseUrl` (provided to `aurelius-data-access` via `provideApiBaseUrl`),
  and `otelExporterUrl` — never hard-code them. Production deployments must serve their
  own `config.json`; a missing or malformed file throws at bootstrap (fail loudly).
- The bearer token is attached to `/api/*` requests via `includeBearerTokenInterceptor`.

## Wiring Checklist

- `project.json` — `implicitDependencies` (keycloak, observability, fastapi) and
  the `serve` `dependsOn`; the `development` build config is what includes `dev/`
  assets, so secrets never leak into production bundles.
- `tsconfig.base.json` — add a path alias when consuming a new Angular lib.
- `package.json` — `@aurelius/brand` is a `file:` dependency.
- `Dockerfile` — static nginx (`dhi.io/nginx`, port 8080), with locale routing baked
  in from `nginx.conf`. Optional `/etc/nginx/app.d/*.conf` fragments are included at
  server scope for per-deployment extras. E2E ships its own full `default.conf`
  (`e2e/config/nginx.conf`, TLS + verified `/api/` + `/otel/` proxies); keep the
  security headers and proxy paths in sync when either changes.
- `nginx.conf` — production also reverse-proxies `/api/` → the FastAPI upstream and
  `/otel/` → the OTLP collector (prefix stripped, mirroring `proxy.conf.json`), so
  the CSP can stay `connect-src 'self'`. Upstreams are the stack's service names —
  template material like the CSP's Keycloak origins: deployments edit them (or
  override the file) for their topology. Hostnames are variables resolved through
  `resolver` per request (Docker DNS `127.0.0.11` by default), so a missing backend
  returns 502 instead of blocking container start. Upstream TLS verification is off
  (no mounted CA); `e2e/config/nginx.conf` shows the verified variant.
- `mkdocs.yaml` — user-guide pages referencing this app.

## Commands

```bash
nx serve aurelius-frontend-example        # starts Keycloak + FastAPI first
nx test aurelius-frontend-example -c ci   # never without -c ci (watch mode hangs)
nx e2e aurelius-frontend-example          # builds image, runs Playwright
nx extract-i18n aurelius-frontend-example # refresh translation bundles
nx lint aurelius-frontend-example
```

Offline-safe: `nx test -c ci`, `nx lint`, `extract-i18n`. Needs Docker: `serve`, `e2e`.

## Conventions

- Components stay presentational; data access goes through `aurelius-data-access`,
  shared UI through `aurelius-ui`, styling tokens through `@aurelius/brand`.
- Follow the existing injectable-service pattern in `src/app` for new state.
- New routes need E2E coverage in `e2e/`.

## Removal

This app is part of the spine. If a fork removes it, also remove: its `mkdocs.yaml`
nav entry and CI references. The backend and Keycloak realm client can stay — they
serve other consumers.
