# docker/

The docker-compose deployment target of the system (ADR 065), at the
**workspace root**: the standalone stack brings up the whole system by hand —
the server, the webapp, the embedder, a Keycloak and an Elasticsearch of its
own, behind one nginx — so, like the umbrella chart in `helm/` (DD-292), it
sits next to the whole repo and not inside one project. Workspace-wide rules,
including the conversion workflow, live in the root `AGENTS.md`. The stack
itself arrived in series 9.5b–9.5e (its own realm, store, webapp and theme)
and grew with the embedder (11.2) and tenancy (15.4); its `README.md` is the
user guide's [Standalone Server](../docs/user-guide/standalone-server.md)
page, included by it.

## Layout

- `docker-compose.yaml` — the umbrella: `name` and the `include` of the ten
  fragments; no service of its own (DD-677). Each piece is included from
  beside its owner (ADR 065): the gateway `proxy` (nginx, the only published
  port, 9000) from `gateway/compose.yaml`, which also carries the stack's
  `nginx.conf` as a static asset the proxy mounts (SPC-01, DD-694: `server_name`
  carries the host written in, and no service renders anything at start). The
  server (in the proxy's network, `/atlas2`) and the one shots `sample-import`
  (behind the profile `demo`, SPC-06) and, under the profile `tenancy`, `tenants`
  (SPC-07), from
  `apps/aurelius-atlas-server/docker/`; the webapp (its own nginx, reading the
  static `docker/webapp/nginx.conf`, SPC-04) from `apps/aurelius-atlas-webapp/docker/`; the
  extractor `aurelius-atlas-data2model`, the lineage API
  `aurelius-atlas-lineage-model` and the validator
  `aurelius-atlas-validate-entity` from each project's `docker/` (DD-674),
  each in the proxy's network with the stack's issuer and realm; the
  `embedder` from `apps/aurelius-atlas-embedder/docker/`; the telemetry piece
  (collector, Prometheus, Loki, Tempo, Grafana, the `jwks-fetch` one shot) from
  `observability/compose.yaml`, which extends the infra observability slice
  and forks only the collector's config to trust the stack's issuer from a
  file (DD-675); the store from `elasticsearch/compose.yaml` and the identity
  provider (with its Postgres) from `keycloak/compose.yaml`, both of which
  `extend` the infra slices' services and state the stack's differences only
  (ADR 066, DD-668, DD-670). Run the umbrella, never a fragment. The stack and
  the dev observability slice publish the same loopback ports, so only one of
  them runs at a time.
- `gateway/nginx.conf`, `keycloak/aurelius-atlas.json` (the stack's realm, in
  the production posture with its service identities and no users, DD-673) —
  the stack's
  own files; each sits in the piece whose container mounts it, and changes
  together with that piece's compose file. Beside each fragment are the files it mounts: the server's
  `import_sample.py` and `tenants.py`, the webapp's `config.json`. A relative
  path in a fragment reads from the fragment's
  own folder (an `include` rebases to its fragment's folder too). The webapp's
  nginx lives here, in `webapp/nginx.conf`, because the same file serves the
  umbrella and any run of the webapp piece.
- Shared assets live with their owner, not here: the Keycloak `aurelius`
  theme is `infra/keycloak/themes/aurelius` (mounted read-only), the store's
  configuration and CA are `infra/elasticsearch/`, the certificates are each
  project's own `certs/`, and the sample folder is
  `data/atlas-sample/`.
- `bin/` holds **every script a person runs by hand** (SPC-11, DD-699), and the
  bundler ships the whole folder: `make-certs.sh` (SPS-09, DD-681), `set-host.sh`
  (SPC-03), `import-sample.sh` (SPC-06), `provision-tenants.sh` (SPC-07). Each
  script finds the stack's root two folders above its own file, so a move
  changes no path inside the stack. They are never compose services, and the
  always-on stack runs none of them.
- `certs.txt`, `certs/` and `.env.example` are the
  stack's own TLS and settings material (SPS-09, DD-681). `bin/make-certs.sh [host]`
  reads `certs.txt` (one line per leaf: `<certs dir> <service>
<SAN>...`) and issues the leaves with `openssl` alone, plus the JVM
  `truststore.p12`, under a CA kept in `docker/certs/` outside the mount trees.
  Only the edge line of the manifest carries the `$HOST` token. The script
  never installs a CA, so it is distinct from `nx certgen`. The stack trusts by
  mount, and the browser warns once for the private CA (SPS-10). Bring your own
  certificates as the default posture: place a CA and leaves at the manifest's
  paths and never run the script. `.env.example` lists the guarded variables for
  a stack that ships alone. `stack.env` is the committed answer for the eight
  folder knobs (SBD-12, DD-687): the umbrella names it in each app `include`, and
  a customer's own `.env` overrides it.

## The release bundle

`nx standalone-bundle -- --version v1.2.3` builds the release artifact (17.3,
SBD-01..08, ADR 067, DD-689/690): a folder with **one flat compose file** under
`dist/standalone-bundle/`, tarred beside it, and never committed. The bundler is
`tools/standalone_bundle.py`.

- The flat file is `docker compose config --no-interpolate` output for the
  umbrella, so compose itself resolves the `include` tree and the `extends`
  bases and the tool carries no compose reading code (DD-689). `--no-interpolate`
  keeps every `${VAR}` the pieces wrote, so each setting stays open. The tool
  copies the files and folders that flat file mounts (DD-690).
- Three mechanical fixes ride on the output (DD-690): baked absolute bind
  sources are rebased to bundle-relative paths, guarded folder mounts gain
  `type: bind` (compose types them `volume` when it cannot interpolate), and the
  guarded folders are answered in the bundle's `.env` with bundle-relative
  values, read by pairing a second interpolated `config` run.
- Two files are written, not copied: `docker/.env` (the `.env.example` roster
  with empty secrets, the folder answers, and the image variables at the
  release tag) and `README.md`.
- Never copied: any `.env`/`.env.enc`, `certs/`, `secrets/`, and any
  `.pem`/`.key`/`.p12`/`.crt` (SBD-04). A bind that leaves the checkout or
  misses its material fails the build instead of shipping a broken stack
  (SBD-03). `make-certs.sh` fills the bundle's `certs/` folders, which is why
  no `certs/` dir needs to travel (SBD-12).
- A new piece or mount travels with no change to the tool, because the flat
  file and the copy list both come from compose itself. A piece that builds an
  image is a shape the bundler refuses by name.

## Conventions

- **The stack serves `localhost` and nothing else** (SPC-02, DD-694): the host
  sits written into the issuer, `KC_HOSTNAME`, each
  application's token URLs, the collector's `issuer_url`, the proxy's
  `server_name`, the webapp's `config.json`, and the realm asset. No piece
  names a host variable, and no service renders a host into a file. No
  application splits dial from expected issuer. A person who wants another host
  runs `bin/set-host.sh` before the start, which rewrites the three
  host-bearing files and re-issues the edge leaf (SPC-03); a host change
  clears the store, because Keycloak imports a realm only into an empty
  database (SPS-07 retires). The apps share the proxy's network namespace, so
  their dials at `https://localhost:9000` arrive at the proxy without an
  `extra_hosts` entry (SPS-04 retires).
- **The stack's certificates and the dev certificates collide on purpose**
  (DD-681): both live in the same `certs/` directories. `nx certgen` and
  `make-certs.sh` each keep a directory idempotent by what its CA signed. So
  running one after the other re-issues the leaves the other owns, and you run
  only one of them in a checkout. A running container holds its material in
  memory, so restart it after re-issuing. The script's truststore password comes
  from `TLS_TRUSTSTORE_PASSWORD` in the stack's env-files, the same value `nx
certgen` reads. When nothing sets it, the script makes one and records it in
  `docker/.env`, so a bundle start follows its README order (certificates first) without a secret to fill
  (DD-691).

- **The stack is apart from the infra stores on purpose** (DD-363, DD-367,
  ADR-066): its fragments `extend` the infra Elasticsearch, Keycloak and
  Postgres, so one component is defined once and the stack states its
  differences — its volumes, its realm, the issuer behind its proxy. It
  _reads_ the infra slices' configuration and certificates, and never writes
  their stores. Nothing here restarts `infra/*` services (DD-223).
  Inside `extends`, compose merges maps by key: `!override` replaces a key
  whole (the Keycloak listener shape, the stack's volumes) and `!reset`
  deletes one (no ports, the base's networks); a `volumes` entry appends and
  replaces at the same target. The stack's Keycloak keeps the production
  topology — Postgres-backed and prod-mode booted, like
  the chart (DD-670) — with no build one shot: Compose seeds the `kc-home`
  volume from the image and the first start re-augments it once (SPC-05,
  DD-696). It pushes its own telemetry to the
  stack's collector (DD-675).
- **Secrets come from three env-files**, never from this folder: `--env-file
apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env --env-file
infra/elasticsearch/.env` (decrypted SOPS defaults, DD-669). Compose
  interpolates an `extends` base with the consuming project's environment
  before the overrides apply, so the base's `${VAR:?}` guards must resolve
  even where a fragment replaces the value; name all three files at every
  command. A new required variable goes in the owning project's `.env` and
  `.env.enc`, and in the README.
- **Images are the `:local` tags** that `nx docker-build` of the server,
  webapp, embedder and the three aux projects produce; each piece names its
  image through a compose-time variable (`<PROJECT>_IMAGE`) with the `:local`
  tag as its default. The stack never pulls from a registry.
- **Folders are required, never defaulted** (SBD-12, DD-687). Each app piece
  names the certificate or sample folder it mounts through a required variable
  (`${NAME_CERTS_DIR:?...}`, `${SAMPLE_DIR:?...}`) with no path default, so a
  customer install cannot inherit a repository path. The umbrella names
  `docker/stack.env` in each app `include` as `env_file`. That committed file
  holds the repository's eight answers (paths, no secret), which keeps the
  README and CI commands unchanged. An e2e stack extends the pieces directly,
  so each project answers the names it transitively extends from its own `.env`
  (Nx injects it into every task). A relative value reads from the declaring
  piece's own folder. The three infra pieces keep their literal `./certs` paths
  (no default to remove; the bundle's path rebase relocates them, SBD-03).
- The compose project name `aurelius-atlas-standalone` and the container
  names it derives are in the README and the user guide (e.g. `docker restart
aurelius-atlas-standalone-aurelius-atlas-server-1`); a rename updates them.

## Tests

The stack is pinned by the root chart-contract suite (it parses the compose
YAML, no Docker daemon): `tests/test__standalone_*.py` (the aux pieces in
`test__standalone_aux_pieces.py`, IRT-10; the telemetry piece in
`test__standalone_observability.py`, IRT-11),
`tests/test__realm_organizations.py` and the standalone cases of
`tests/test__tenancy_chart.py` read the stack as written — the umbrella, its
fragments, and each `extends` merged by `standalone_compose()` in
`tests/conftest.py`, which resolves compose's merge the way compose does
(DD-671) — so a changed mount path, image, or env placeholder fails there.
The infra-owned parts (image, healthcheck, configuration mounts) are proved
as inherited, not copied (IRT-05, IRT-06). `docker compose -f
docker/docker-compose.yaml ... config --quiet` is the offline check that
every mount and env-file resolves. Rule ids of the series 9.5 specs (DMO-,
SST-, SWA-, SKT-, EMB-11, WPT-10, TRM-11), of 17.1 (IRT-), of 17.2 (SPS-), of
17.3 (SBD-) and of 17.4 (SPC-) name these tests. `tests/test__standalone_host.py`
pins the literal host across the issuer, the realm asset, the proxy's static
`nginx.conf`, the collector, the four scripts of `docker/bin/`, the certificate
script and its manifest, and the README (SPC-01..03, SPC-11; the kept SPS rules
on certificates). `tests/test__standalone_bundle.py` builds a bundle from the tree
into a temp folder and checks it offline: closed, secret-free, resolved free of
`:local` with its own `.env`, and its flattened service set equal to
`standalone_compose()`'s (SBD-01..08). The script's live run and a sign-in are
level-2 checks a human records in the PR, not part of this suite.

## Removal

The stack is `docker/` (umbrella and the gateway, store, identity and
telemetry fragments in `gateway/`, `elasticsearch/`, `keycloak/` and
`observability/` beside it) and
the six `docker/` folders beside the server, webapp, embedder and the three aux
projects: delete them, its ten root tests, the two
`mkdocs.yaml` nav entries (`Standalone Server`, `Add a Tenant to the
Standalone Server`) and the links from `docs/user-guide/index.md`,
`docs/user-guide/deployment.md`, `apps/aurelius-atlas-server/README.md`,
`infra/keycloak/README.md` and `apps/aurelius-atlas-embedder/AGENTS.md`. The
theme in `infra/keycloak/themes/` outlives it — the chart's realm takes it next
(DD-414 names it the Aurelius look, not the demo stack's).
