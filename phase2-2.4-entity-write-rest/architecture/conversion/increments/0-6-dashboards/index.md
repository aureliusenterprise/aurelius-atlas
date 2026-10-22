# 0.6 Dashboards served

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-017, DD-018, DD-019; relies on DD-001, ADR 046

## Scope

The two Apache Atlas 2.4.0 user interfaces are served by the Aurelius Atlas server where Atlas serves them: `dashboardv2` at `/` and `dashboardv3` at `/n/` ([DD-001](<https://aureliusenterprise.github.io/phase2-2.4-entity-write-rest/architecture/conversion/design-log/#dd-001-reference-is-apache-atlas-240-and-both-dashboards-are-served>)).

- **`apps/aurelius-atlas-dashboard`**: the `dashboardv2` and `dashboardv3` source of the `release-2.4.0` tag, vendored unchanged apart from the patches listed in its `PATCHES.md`, with a `build` target that compiles both in a hardened Node container.
- **`aurelius-atlas-server`**: serves the built dashboards next to the API; its image contains them.
- **Proof**: the end-to-end tests load both dashboards in a browser against the image.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| The data the dashboards show (types, entities, search, lineage, …) | 1.x to 5.x |
| The login page (`login.jsp`) and the redirect to it | 6.1 |
| Changes to the dashboards' behaviour or look | not planned (ADR 046, DD-001) |

Until those increments land, the dashboards load and show errors for every call the server does not answer yet. That is the expected state, not a deviation.

## Semantics

| Id | Rule |
| --- | --- |
| DSH-01 | `GET /` answers the built `dashboardv2` `index.html`, and every other built `dashboardv2` file is served at its path below `/` |
| DSH-02 | `GET /n/` answers the built `dashboardv3` `index.html`, and every other built `dashboardv3` file is served at its path below `/n/` |
| DSH-03 | The API takes precedence: a path the API answers is never served from the dashboards, and a path neither answers is 404 |
| DSH-04 | Without a configured dashboard directory, the server serves the API only |
| DSH-05 | The dashboards are built from the vendored `release-2.4.0` source, changed only by the patches in `apps/aurelius-atlas-dashboard/PATCHES.md` |
| DSH-06 | In a browser, each dashboard loads from the server image and asks it for `/api/atlas/admin/session`, which answers 200 |

DSH-05 keeps the dashboards those of Atlas 2.4.0: the vendored source is byte-identical to the tag and every change is one reviewed patch ([DD-017](<https://aureliusenterprise.github.io/phase2-2.4-entity-write-rest/architecture/conversion/design-log/#dd-017-the-dashboards-are-vendored-unchanged-and-built-with-dart-sass-on-node-24>)). DSH-01 to DSH-03 serve them from the API's origin, as Atlas does ([DD-018](<https://aureliusenterprise.github.io/phase2-2.4-entity-write-rest/architecture/conversion/design-log/#dd-018-the-server-serves-the-dashboards-from-the-apis-origin>)).

## Java origin

Apache Atlas `release-2.4.0`:

- `dashboardv2/`, `dashboardv3/`: the user interfaces, vendored
- `webapp/pom.xml`, `dashboardv2/pom.xml`, `dashboardv3/pom.xml`: where the builds go in the web application (`dashboardv2` at the root, `dashboardv3` under `n/`) and the `grunt build-minify` step

## Deviations

None that a client of the REST API sees. The dashboards' stylesheets are compiled by dart-sass instead of libsass (DD-017); the JavaScript is identical to Atlas's build.

## Acceptance

- `apps/aurelius-atlas-server/tests/` — serving from a dashboard directory, API precedence and the API-only mode (DSH-01 to DSH-04).
- `apps/aurelius-atlas-dashboard/` — `PATCHES.md` and the build (DSH-05), run by `nx build aurelius-atlas-dashboard` and by the server image's build.
- `apps/aurelius-atlas-server/e2e/` — both dashboards in Chromium against the image (DSH-06).
