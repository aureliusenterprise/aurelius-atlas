# 0.6 Dashboards served

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-017, DD-019, DD-034 (supersedes DD-018), DD-035; relies on DD-001, ADR 046

## Scope

The two Apache Atlas 2.4.0 user interfaces are served where Atlas serves them — `dashboardv2` at `/` and
`dashboardv3` at `/n/` — by the dashboard image, an nginx container that keeps the API on the same
origin by proxying `/api/` to the Aurelius Atlas server
([DD-001](../design-log.md#dd-001-reference-is-apache-atlas-240-and-both-dashboards-are-served)).

- **`apps/aurelius-atlas-dashboard`**: the `dashboardv2` and `dashboardv3` source of the
  `release-2.4.0` tag, vendored unchanged apart from the patches listed in its `PATCHES.md`, with a
  `build` target that compiles both in a hardened Node container, and an nginx image that serves the
  built files and proxies `/api/`, `dashboardv3`'s `/n` directory redirect and the login root
  `j_spring_security_check` to the server (DD-034).
- **`aurelius-atlas-server`**: serves the API only; its image no longer contains the dashboards.
- **Proof**: the end-to-end tests load both dashboards in a browser against the dashboard image, with
  the server's API behind its proxy.

Not in scope:

| Not delivered here                                                 | Delivered by                  |
| ------------------------------------------------------------------ | ----------------------------- |
| The data the dashboards show (types, entities, search, lineage, …) | 1.x to 5.x                    |
| The login page (`login.jsp`) and the redirect to it                | 6.1                           |
| Changes to the dashboards' behaviour or look                       | not planned (ADR 046, DD-001) |

Until those increments land, the dashboards load and show errors for every call the server does not
answer yet. That is the expected state, not a deviation.

## Semantics

| Id     | Rule                                                                                                                                                        |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DSH-01 | `GET /` answers the built `dashboardv2` `index.html`, and every other built `dashboardv2` file is served at its path below `/`                              |
| DSH-02 | `GET /n/` answers the built `dashboardv3` `index.html`, and every other built `dashboardv3` file is served at its path below `/n/`; `/n` redirects to `/n/` |
| DSH-03 | The API takes precedence: a path the API answers is never served from the dashboards, and a path neither answers is 404                                     |
| DSH-04 | The server serves the API only: on its own origin, no dashboard path answers                                                                                |
| DSH-05 | The dashboards are built from the vendored `release-2.4.0` source, changed only by the patches in `apps/aurelius-atlas-dashboard/PATCHES.md`                |
| DSH-06 | In a browser, each dashboard loads from the dashboard image and asks it for `/api/atlas/admin/session`, which answers 200                                   |
| DSH-10 | The proxy forwards the origin's Host, port included, so an upstream-generated absolute redirect (FastAPI's slash normalization) keeps the public origin     |

DSH-05 keeps the dashboards those of Atlas 2.4.0: the vendored source is byte-identical to the tag and
every change is one reviewed patch
([DD-017](../design-log.md#dd-017-the-dashboards-are-vendored-unchanged-and-built-with-dart-sass-on-node-24)).
DSH-01 to DSH-04 serve them on one origin that also answers the API, as Atlas does
([DD-034](../design-log.md#dd-028-the-dashboard-image-serves-the-dashboards-and-proxies-the-api)): the
dashboard image serves the files and proxies `/api/` to the server, whose routes keep the prefix.
DSH-03's precedence is nginx's longest-prefix match: `/api/` reaches the server even where a dashboard
file has the same name.

## Java origin

Apache Atlas `release-2.4.0`:

- `dashboardv2/`, `dashboardv3/`: the user interfaces, vendored
- `webapp/pom.xml`, `dashboardv2/pom.xml`, `dashboardv3/pom.xml`: where the builds go in the web
  application (`dashboardv2` at the root, `dashboardv3` under `n/`) and the `grunt build-minify` step
- Atlas's web application is a servlet container serving both dashboards and the API from one origin;
  the dashboard image keeps that shape with a proxy instead of a shared process (DD-034)

## Deviations

DV-09: serving the dashboards from nginx instead of the API's process changes what a browser observes
around the dashboards — `/n` answers 308 where the serving process directory-redirected, hardening
headers are added, and the origin speaks TLS per container. None that a client of the REST API sees.
The dashboards' stylesheets are compiled by dart-sass instead of libsass (DD-017); the JavaScript is
identical to Atlas's build.

## Acceptance

- `apps/aurelius-atlas-dashboard/` — `PATCHES.md` and the build (DSH-05), run by `nx build
aurelius-atlas-dashboard` and by the dashboard image's build.
- `apps/aurelius-atlas-dashboard/` — its stack (`docker-compose.yaml`) runs the dashboard image and the
  API-only server on the dev store, and its `e2e/` tests prove both dashboards, the `/n` redirect, the
  proxy's precedence, the forwarded Host and the server's API-only origin (DSH-01 to DSH-04, DSH-10)
  against it, plus both dashboards in Chromium against the dashboard image (DSH-05, DSH-06).
