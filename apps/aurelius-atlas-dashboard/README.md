# aurelius-atlas-dashboard

The two user interfaces of Apache Atlas 2.4.0, `dashboardv2` and `dashboardv3`, vendored from the
`release-2.4.0` tag and changed only by the patches in [`PATCHES.md`](PATCHES.md)
([DD-017](../../docs/architecture/conversion/design-log.md#dd-017-the-dashboards-are-vendored-unchanged-and-built-with-dart-sass-on-node-24)).

Introduced by increment [0.6](../../docs/architecture/conversion/increments/0-6-dashboards.md). The
dashboard image — this project's nginx container — serves them where Atlas does: `dashboardv2` at `/`
and `dashboardv3` at `/n/`, with the API proxied from the server on the same origin
([DD-034](../../docs/architecture/conversion/design-log.md#dd-028-the-dashboard-image-serves-the-dashboards-and-proxies-the-api)).
Until the later increments port the endpoints they call, the dashboards load and report errors for
those calls.

## Building

```bash
npx nx build aurelius-atlas-dashboard
```

The build runs `grunt build-minify` for both dashboards inside the hardened Node 24 image, as Atlas's
Maven build does, and writes only the static files to `dist/`. It needs Docker with `buildx`.

## Serving

```bash
npx nx docker-build aurelius-atlas-dashboard   # the nginx image around dist/
npx nx up aurelius-atlas-dashboard             # whole product on https://localhost:8444
```

The image bakes `nginx.conf.template` over the stock site config; the `${AURELIUS_ATLAS_DASHBOARD_*}`
placeholders are resolved by the deployment, which mounts its filled-in copy over
`/etc/nginx/conf.d/default.conf` (an unresolved container fails `nginx -t` at start). The template keeps
the API on the same origin: `/api/` is proxied to the server without stripping the prefix.

Authentication (increment [6.1](../../docs/architecture/conversion/increments/6-1-authentication.md))
gates the _pages_ at this origin: the five page locations (`/`, `/index.html`, `/n/`, `/n/index.html`,
`/login.jsp`)
ask the server `/api/atlas/auth/check` through an `auth_request` subrequest, and without a session the
browser is redirected to the server's login start, which runs the Keycloak code flow and returns to the
intended page (DD-036). `/login.jsp` — Atlas's login URI and logout landing — serves the login page
(`webapp/login.html`) on a session, which resolves to the dashboard the user was on (DSH-09, DD-040).
Assets, `/api/`, and `/logout.html` are not gated; the API guards itself in the
server. `nx up` brings Keycloak with it — sign in with one of the `dev/keycloak` dev users.

## License

The vendored source is Apache Atlas's, under the Apache License 2.0; see [`LICENSE`](LICENSE) and
[`NOTICE`](NOTICE).
