# aurelius-atlas-frontend-example

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
  client/realm, `apiBaseUrl` (provided to `aurelius-atlas-data-access` via `provideApiBaseUrl`),
  and `otelExporterUrl` — never hard-code them. Production deployments must serve their
  own `config.json`; a missing or malformed file throws at bootstrap (fail loudly).
- The bearer token is attached to `/api/*` requests via `includeBearerTokenInterceptor`.
- The OTLP exporters attach the user's own token through the
  `createAureliusOtelIngestAuth` headers factory (aurelius-atlas-observability,
  DD-103); `/otel` passes `Authorization` through and the
  collector validates it via OIDC — logged-out pushes 401 by design.

## Wiring Checklist

- `project.json` — `implicitDependencies` (keycloak, observability, fastapi) and
  the `serve` `dependsOn`; the `development` build config is what includes `dev/`
  assets, so secrets never leak into production bundles.
- `tsconfig.base.json` — add a path alias when consuming a new Angular lib.
- `package.json` — `@aurelius/atlas-brand` is a `file:` dependency.
- `Dockerfile` — static nginx (`dhi.io/nginx`, port 8080) serving the locale tree;
  bakes `nginx.conf.template` over the stock `/etc/nginx/conf.d/default.conf`.
  No entrypoint, no render-on-start (deliberately: the hardened runtime image
  has no shell tooling, and the `-dev` variant with envsubst runs as root —
  see the dhi guides). Optional `/etc/nginx/app.d/*.conf` fragments are
  included at server scope for per-deployment extras. Consumers that run the
  image mount their own **fully resolved** copy over
  `/etc/nginx/conf.d/default.conf` — E2E ships `e2e/config/nginx.conf` (static
  file, hard-filled values: TLS + verified `/api/` + `/otel/` proxies);
  deployments do the same with their topology (ConfigMap/secret, compose
  config, …). Keep the security headers and proxy paths in sync when either
  changes.
- `nginx.conf.template` — production also reverse-proxies `/api/` → the FastAPI
  upstream and `/otel/` → the OTLP collector (prefix stripped, mirroring
  `proxy.conf.json`), so the CSP can stay `connect-src 'self'`. Topology is
  parameterized with `${AURELIUS_ATLAS_FRONTEND_*}` placeholders
  (`API_UPSTREAM[_NAME]`, `OTEL_UPSTREAM[_NAME]`, `TLS_CA_FILE`,
  `DNS_RESOLVER`, `KEYCLOAK_ORIGINS` in the CSP `connect-src`/`frame-src`) —
  resolved **by the consumer at deploy time** (envsubst/sed/kustomize), never
  at container start: nginx treats `${NAME}` as an unknown nginx variable, so
  an unresolved file fails `nginx -t` loudly instead of serving. Upstream TLS
  is verified against `TLS_CA_FILE`'s resolved value (mount the CA beside the
  config). Hostnames go through `resolver` per request, so a missing backend
  returns 502 instead of blocking container start. Quick syntax check of a
  resolved copy:
  `docker run --rm -v ./resolved.conf:/etc/nginx/conf.d/default.conf:ro <image> -t`.
- `mkdocs.yaml` — user-guide pages referencing this app.

## Commands

```bash
nx serve aurelius-atlas-frontend-example        # starts Keycloak + FastAPI first
nx test aurelius-atlas-frontend-example -c ci   # never without -c ci (watch mode hangs)
nx e2e aurelius-atlas-frontend-example          # builds image, runs Playwright
nx extract-i18n aurelius-atlas-frontend-example # refresh translation bundles
nx lint aurelius-atlas-frontend-example
```

Offline-safe: `nx test -c ci`, `nx lint`, `extract-i18n`. Needs Docker: `serve`, `e2e`.

## Conventions

- Components stay presentational; data access goes through `aurelius-atlas-data-access`,
  shared UI through `aurelius-atlas-ui`, styling tokens through `@aurelius/atlas-brand`.
- Follow the existing injectable-service pattern in `src/app` for new state.
- New routes need E2E coverage in `e2e/`.

## Removal

This app is part of the spine. If a fork removes it, also remove: its `mkdocs.yaml`
nav entry and CI references. The backend and Keycloak realm client can stay — they
serve other consumers.
