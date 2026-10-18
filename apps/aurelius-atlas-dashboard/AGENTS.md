# aurelius-atlas-dashboard

The Apache Atlas 2.4.0 dashboards, vendored (DD-017). This file covers wiring specific to this project;
workspace-wide rules, including the conversion workflow, live in the root `AGENTS.md`.

## Layout

- `dashboardv2/`, `dashboardv3/` — the `release-2.4.0` source, byte for byte apart from `PATCHES.md`
- `PATCHES.md` — every change made to the vendored source, one commit each (DSH-05)
- `LICENSE`, `NOTICE` — Apache Atlas's, kept with the source it covers
- `build.Dockerfile` — `grunt build-minify` for both dashboards in the hardened Node 24 image
- `dist/` — the build output (git-ignored): `dashboardv2` at the root, `dashboardv3` in `n/`
- `webapp/` — this project's own pages (not vendored): `login.html`, the login page nginx answers
  at `/login.jsp`, resolving to the dashboard the user was on (DD-040)
- `Dockerfile` — the nginx image: `dist/` as the site root plus `nginx.conf.template` baked over
  `/etc/nginx/conf.d/default.conf` (DD-034), and `webapp/` copied beside it
- `nginx.conf.template` — the site config with `${AURELIUS_ATLAS_DASHBOARD_*}` placeholders
  (`API_UPSTREAM[_NAME]`, `TLS_CA_FILE`, `DNS_RESOLVER`) the deployment resolves at mount time
- `docker-compose.yaml` + `nginx.conf` — the dev stack: nginx in front, the API-only server and the
  dev store behind; `nginx.conf` is the resolved config the stack mounts over the image's template.
  The compose plugin infers `up` from this file (`serve` is opted out in `project.json` metadata —
  the dev loop here is the detached stack, not a foreground run)
- `nginx.conf` also carries the page-load gate (DSH-07, DD-036): `auth_request /_auth` on the five
  page locations (`/`, `/index.html`, `/n/`, `/n/index.html`, `/login.jsp`) asks the server's
  `/api/atlas/auth/check` and a 401 redirects to its login start (`@login`, relative); on a session
  `/login.jsp` serves `webapp/login.html` — Atlas's login URI and logoutSuccessUrl, and the vendored
  UI's 401 landing (DSH-09, DD-040); `/logout.html` proxies to the server, and assets stay ungated
  (DSH-08). The template keeps the same structure with placeholders.
- `tls.json` — the image's certificate for that stack (`nx certgen`)
- `e2e/` — the pytest tests that prove DSH-01 to DSH-09; their conftest starts exactly the stack
  above (plus dev/keycloak, which the server's AUTH_* settings point at)

## Rules

- **Never edit the vendored source in passing.** A change is a new row in `PATCHES.md` and its own
  commit; the formatters, linters and hooks skip `dashboardv2/` and `dashboardv3/` on purpose.
- The behaviour or look of the dashboards does not change (ADR 046, DD-001). The server answers the
  calls they make; the dashboards are not adapted to the server.
- The site config keeps the origin contract the vendored source assumes: `/api/` proxied with the
  prefix kept (their `apiBaseUrl` comes from `window.location.pathname`), `/n` redirected to `/n/`,
  no SPA fallback (they route on the URL fragment), no CSP (they run inline scripts and `eval` —
  DV-09). The resolved variant (`nginx.conf`) differs only by TLS and the filled-in upstream — keep
  the two in sync when either changes.
- The gate lives at this origin and the OIDC flow lives in the server (DD-036): nginx only asks
  `/api/atlas/auth/check` and redirects — no token or session logic belongs here. The gated page
  locations are exact matches on purpose; a prefix location would sweep unknown paths (and their
  404s) into login redirects.

## Wiring Checklist

- `project.json` — the `build` target and its inputs; the `up` `dependsOn`, which adds the server
  image, the server's certificate, the dev store and — since 6.1, via `implicitDependencies` —
  dev/keycloak, to what the compose plugin infers; and the `metadata.dockerCompose.serve = false`
  opt-out that drops the inferred `serve` target.
- `Dockerfile` — `COPY dist/` as the site root (its layout is Atlas's webapp layout: v2 at the root,
  v3 in `n/`) and `COPY webapp/` beside it (the login page ships without a `dist/` rebuild); the
  docker plugin infers the `docker-*` targets from its name, and its `dependsOn` `build` writes
  `dist/` first.
- `.env.enc` — the dev stack's compose interpolation (the ES password mirrors `dev/elasticsearch/.env`).
  The RP client secret mirrors `dev/keycloak/.env` and reaches the server service as
  `AURELIUS_ATLAS_SERVER_AUTH_CLIENT_SECRET` (6.1). Re-run `nx encrypt aurelius-atlas-dashboard`
  after changing `.env`.
- `.dockerignore` — keeps local `node_modules/`, `dist/` and `public/js/libs/` out of the build context.
  The `Dockerfile` build context is the workspace root and needs `dist/`, which it does not exclude.
- `.pre-commit-config.yaml`, `.prettierignore`, `eslint.config.mjs` — exclude the vendored directories.
- No `pyproject.toml` on purpose: the project ships no Python. The trace check (ADR 049) still
  gathers the `covers` markers of its e2e tests, because an Atlas project is an Nx project (DD-035).
  `release.versionActions` is the noop plugin, as for the other manifest-less projects.
- `e2e/conftest.py` — the tests start exactly this stack (testcontainers), so `nx up` and `nx e2e`
  exercise the same topology.

## Commands

```bash
npx nx build aurelius-atlas-dashboard     # docker buildx; writes dist/
npx nx docker-build aurelius-atlas-dashboard   # the nginx image around dist/
npx nx up aurelius-atlas-dashboard        # whole product on https://localhost:8444 (dev store + Keycloak)
npx nx e2e aurelius-atlas-dashboard -c ci # DSH tests against the stack (dashboard image + server)
# First page load redirects to Keycloak; the dev users live in dev/keycloak (see its README).
```

## Removal

Not removable: the dashboards are part of the product (ADR 046).
