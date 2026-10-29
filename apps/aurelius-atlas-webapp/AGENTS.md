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
- `helm/` — the `atlas-webapp` chart (its own section below)
  image, with the real atlas-server container behind nginx `/api/` (DD-142) and
  Keycloak sign-in via the `authenticated` fixture (APC-10), which replays a
  per-browser session state — one form login per browser, silent check-sso for
  every test, form-login self-heal when the shared session dies (DD-224)

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
  (aurelius-atlas-observability, DD-193) —
  the collector's browser receiver validates it via OIDC; token-less (logged-out)
  pushes 401 by design.
- Every new component gets a Storybook story (7.2 wires the ui library pattern);
  every new route gets an e2e scenario.
- Template strings carry `i18n="@@legacy.key"` markers matching the catalogue ids.
- The nginx configs (shipped template + `e2e/config/nginx.conf`) are
  **http-context includes**: the hardened image loads `conf.d/*.conf` inside
  its `http{}` block, so http-scoped directives (`otel_exporter`, `map`,
  `geo`, limit zones) belong at file top. Tracing is opted in per location
  (`otel_trace on` on `/api/`, off server-wide, ETR-01); the OTel module and
  its library closure ship in the image (builder stage, DD-239) — do not
  `load_module` from conf.d, it is main-context only and lives in
  `etc/nginx/modules/otel.conf`.

## Helm chart

`helm/` — the `atlas-webapp` chart (10.3a, CHT-23/24/25/26; DD-270): TLS
8080 behind the umbrella's Gateway — the Gateway terminates browser TLS and
dials this listener over TLS too (its BackendTLSPolicy validates the chart's
`Certificate`, Service-name SANs, CHT-22's rule) — with HTTPS probes.
The shipped nginx template rides the chart as a **byte copy**
(`helm/files/nginx.conf.template` — a test asserts it matches this project's
`nginx.conf.template`, so the drift guard is the chart test); Helm never
substitutes a placeholder. The `resolve-nginx-config` init container (same
image, `/bin/sh -ec`) `sed`s the twelve `${AURELIUS_ATLAS_WEBAPP_*}` placeholders
into the emptyDir nginx reads, and `grep`s the output to fail the pod on any
left unresolved (DD-262 — Helm cannot render them without re-drawing the
umbrella's generated token). The twelve are the chart's join contract (CHT-25):
`API_UPSTREAM`/`_NAME` (the server Service) and `OTEL_UPSTREAM`/`_NAME` +
`OTLP_ENDPOINT` (the collector legs) default to **cluster FQDNs** — the
template's `proxy_pass` is a variable, which forces nginx's stub resolver, and
that resolver ignores `resolv.conf`'s search list (a short Service name 502s on
`Host not found`; the peer Certificates carry the `.svc.cluster.local` SAN so
`proxy_ssl_name` matches, DD-243). `KEYCLOAK_ORIGINS` (the issuer),
`DNS_RESOLVER`, `TLS_CA_FILE` (the CA mount), `TLS_CERT_FILE`/`TLS_KEY_FILE`
(the listener leaf mount, DD-270 — `tls.certSecretName` brings your own and
the chart's `Certificate` renders nothing), `REALIP_BLOCK` (DD-261, from
`nginx.trustedProxyCIDRs`), and `OTEL_INGEST_TOKEN` — which arrives from the
`<release>-collector-legacy` Secret at pod start, never rendered. `/config.json`
is a ConfigMap rendered from values and mounted at the SPA's bootstrap path
(`config.apiBaseUrl` `/api`, `config.keycloak.url`, `config.otelExporterUrl`).
`uid`/`fsGroup` 65532 with `/run/nginx`, `/var/lib/nginx/tmp`, `/var/log/nginx`
on emptyDirs (the read-only-rootfs nginx needs them writable — and _tmp_
specifically: the image bakes `/var/lib/nginx/logs` and `/var/lib/nginx/modules`
as symlinks, and an emptyDir over `/var/lib/nginx` hides them, which breaks
`load_module` at boot). Chart-contract
tests: `tests/test__charts_webapp.py`. Conventions in `helm/AGENTS.md`.

```bash
npx nx run aurelius-atlas-webapp:helm-template
```

Removing the app removes `helm/` too — plus the umbrella's dependency and
values-toggle rows (`helm/AGENTS.md`).

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
