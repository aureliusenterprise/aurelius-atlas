# 17.4 Simplify the standalone stack to Docker Compose

- **Status:** in progress
- **Pull request:** [#397](https://github.com/aureliusenterprise/aurelius-atlas/pull/397)
- **Records:** DD-694 to DD-699 (here); relies on
  [ADR 065](../../docs/architecture/adr/065-compose-stacks-that-deploy-the-whole-system-live-at-the-root.md)
  (the compose fragments and the root `docker/`),
  [ADR 066](../../docs/architecture/adr/066-infrastructure-components-live-at-the-repository-root.md)
  (the infra slices the stack extends),
  [ADR 067](../../docs/architecture/adr/067-the-standalone-stack-ships-as-one-generated-release-bundle.md)
  (the bundle), increment 17.1 (IRT, DD-667..677), increment 17.2 (SPS, DD-678..681), and increment 17.3
  (SBD, DD-682..693).

## Scope

The standalone stack carries three kinds of extra machinery that Docker Compose does not need. It boots one
one-shot service to write a browser host into two files, and a second to render a webapp configuration from
constants. It runs a Keycloak build stage that the container runtime can do by itself. It starts a sample
import and a tenant provisioning one-shot on every start, whether the person wants them or not. Each piece
exists for a reason the current stack no longer has, and the user's rule for this stack is the least custom
logic that stays inside Docker Compose.

This increment removes that machinery. It makes the stack need only Docker Compose and the images it names.

It delivers:

- A localhost-only browser surface. The proxy's `nginx.conf` becomes a static mount, and the host is written
  into it, the webapp's `config.json`, and the realm asset (SPC-01, SPC-02). No piece reads a host variable.
  This retires the host machinery of increment 17.2 (SPS-01, SPS-04, SPS-06).
- The render one-shots gone. The gateway's `gateway-config` and the webapp's `webapp-config` services no
  longer exist (SPC-02, SPC-04).
- One documented host path, outside the stack. A person who wants a host other than `localhost` runs an
  optional script or edits the host-bearing files before the start (SPC-03).
- A Keycloak that starts in production mode with no build one-shot. The container seeds its home from the
  image, as it does for Elasticsearch, and the first start re-augments once (SPC-05).
- A sample import and a tenant provisioning that leave the always-on stack. One external script runs each,
  and neither starts unless the person runs it (SPC-06, SPC-07).
- The two one-shots that stay, with the reason written down: the collector's JWKS fetcher (SPC-08) and the
  store's volume owner (SPC-09).
- One folder for the scripts a person runs. `docker/bin/` holds the certificate script and the three scripts
  above, and the bundle ships the folder (SPC-11).

It does not deliver, with the increment that will:

| Not delivered                                                                                                     | Lands with              |
| ----------------------------------------------------------------------------------------------------------------- | ----------------------- |
| A re-simplified bundler (the flat file's mechanical fixes of DD-690 shrink once the rendered files become assets) | the bundler follow-up   |
| A host other than `localhost` as a default path (a host change wipes the store, SPC-03)                           | not planned             |
| Production hardening and a signed bundle                                                                          | the hardening increment |
| Network exposure, internal TLS re-pointing, or a multi-host topology                                              | not planned             |

## Semantics

"A render one-shot" is a service that writes a host value into a configuration file before the service that
reads it starts. A "static asset" is a file the stack mounts as it sits in the repository. The "host" is the
browser address of the stack. "The edge leaf" is the certificate the proxy serves. The "demo one-shots" are
`sample-import` and `tenants`. An "external script" is a shell script a person runs by hand. It is not a
compose service. The "always-on stack" is what `docker compose up -d` starts with no profile and no script.
The "scripts folder" is `docker/bin/`, the one folder that holds every script a person runs by hand.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SPC-01 | The proxy's `docker/gateway/nginx.conf` is a static asset. It carries `server_name localhost` written in, holds no host placeholder, and is mounted into the proxy's nginx configuration folder as a bind (SPS-01 and SPS-06 retire, DD-694).                                                                                                                                                                                                                                                                                                                                                              |
| SPC-02 | No piece of the standalone stack names `STANDALONE_HOST`, and the stack declares no service that renders a host into a file. The proxy's `server_name`, the apps' issuer and token URLs, the webapp's `config.json`, and the realm asset carry `localhost` directly, and the proxy's `extra_hosts` entry for the host is gone. The `config.json` is served by the webapp through the proxy's catch-all location, so the proxy's own `location = /config.json` block and the `gateway-conf` and `gateway-static` named volumes no longer exist, and the `gateway-config` service no longer exists (DD-694). |
| SPC-03 | A person who wants a host other than `localhost` changes it outside the stack, before the start. The stack ships an optional script `docker/bin/set-host.sh` that rewrites the three host-bearing files (`nginx.conf`, the webapp's `config.json`, the realm asset) and re-issues the edge leaf, or the person edits those files by hand. A host change wipes the identity store and re-imports the realm (the SPS-07 keep-data path retires with the host machinery). The script is not a compose service and the always-on stack never runs it (DD-694).                                                 |
| SPC-04 | The webapp starts with no config one-shot. It mounts a static nginx configuration the stack ships, which names the same upstreams the chart's init container renders and carries no ingest token. The `webapp-config` service, the `webapp-nginx-conf` volume, and `resolve-nginx.sh` no longer exist (DD-695).                                                                                                                                                                                                                                                                                            |
| SPC-05 | Keycloak boots in production mode with a plain `start` and no build one-shot. The `keycloak-build` service no longer exists. The `kc-home` volume stays, because Docker seeds it from the image and the seeded home is writable by the image's user, which the image's own root is not. The first start re-augments the build once into that home, and later starts find a current build and write nothing (DD-696).                                                                                                                                                                                       |
| SPC-06 | The `sample-import` one-shot moves behind a compose profile, so the always-on stack starts no import. An external script `docker/bin/import-sample.sh` runs it on demand through `docker compose run`, and the script names no secret (it passes the stack's env files). The service stays in the pieces, so the bundle keeps it (SBD-07, DD-697).                                                                                                                                                                                                                                                         |
| SPC-07 | The `tenants` one-shot stays behind its compose profile, so the always-on stack starts no provisioning (it already sits behind the `tenancy` profile). An external script `docker/bin/provision-tenants.sh` runs it on demand through `docker compose run`, and the script names no secret (DD-697).                                                                                                                                                                                                                                                                                                       |
| SPC-08 | The `jwks-fetch` one-shot stays. The collector validates the stack's issuer and reads its keys from a file, because the issuer URL is the proxy's browser address and no in-network container can dial it. The rule records this as the reason the one-shot is not a fixable design (DD-698).                                                                                                                                                                                                                                                                                                              |
| SPC-09 | The store's `elasticsearch-volume-init` one-shot stays. It sets the owner of the store's volume folders, and the in-cluster shape of the same rule is the chart's `fsGroup`. The rule records this as the second one-shot that is not a fixable design (DD-698).                                                                                                                                                                                                                                                                                                                                           |
| SPC-10 | The repository's suites stay green with the stack resolved by `docker compose config`. The root standalone suite, the bundle suite, and the three infra e2e stacks start the same service set they named before, minus the three services this increment removes (`gateway-config`, `webapp-config`, `keycloak-build`). The `sample-import` and `tenants` services stay behind a profile and stay in the flat file, and no service gains a custom render step (DD-694..697). The bundle the target builds stays closed (SBD-03) and names no removed service (SBD-02).                                     |
| SPC-11 | Every script a person runs by hand sits in `docker/bin/`. That holds `make-certs.sh`, which increment 17.2 placed at `docker/make-certs.sh`, plus the three scripts of SPC-03, SPC-06, and SPC-07. Each script finds the stack's root two folders above its own file, so a move changes no path inside the stack. The bundler ships every file of that folder, so a bundle holds the scripts its own README names (DD-699).                                                                                                                                                                                |

## Java origin

None. This increment ports no Apache Atlas behaviour. It removes Aurelius deployment machinery that Apache
Atlas's own single-container demo never carried.

## Deviations

None new. The stack moves closer to Apache Atlas's single-container simplicity, not away from it. The
retire- ments of SPS-01, SPS-04, SPS-06, and SPS-07 are recorded as superseded in this spec's Records line
and in DD-694, and the accepted SPS rules in increment 17.2's spec stay as written.

## Acceptance

- `uv run pytest tests` (no Docker daemon): the root standalone suite stays green.
  `tests/test__standalone_gateway.py`, `tests/test__standalone_webapp.py`,
  `tests/test__standalone_demo_realm.py`, and `tests/test__standalone_host.py` drop the assertions on the
  render one-shots and the host placeholder, and gain assertions that the two static files carry `localhost`
  with no placeholder and that the stack declares no `gateway-config` or `webapp-config` service (SPC-01,
  SPC-02, SPC-04). Each rule id is named with `@pytest.mark.covers(..., rules=["SPC-NN"])`.
- `tests/test__standalone_observability.py` keeps `jwks-fetch` (SPC-08) and
  `tests/test__standalone_bundle.py` keeps the store's `elasticsearch-volume-init` (SPC-09).
- `tests/test__standalone_paths.py` drops the render one-shots from the mount set and keeps the guarded
  folders (SPC-01, SPC-02).
- A level 2 run, recorded in the pull request: start the always-on stack on a clean store, open
  `https://localhost:9000/` and sign in, then run `docker/bin/import-sample.sh` and confirm it imports the
  sample, and run `docker/bin/provision-tenants.sh` and confirm it provisions the demo tenant (SPC-03, SPC-06,
  SPC-07). Confirm Keycloak reaches healthy on a fresh volume with no build one-shot (SPC-05).
- `tests/test__standalone_host.py` reads the script at its new path and `tests/test__standalone_bundle.py`
  asserts the bundle holds all four scripts of `docker/bin/` (SPC-11).
- The docs gates pass: prettier, `zensical build --strict`, and markdownlint on the changed files.
