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
  `nginx.conf`; the
  server (in the proxy's network, `/atlas2`) and the one shots `sample-import`
  and, under the profile `tenancy`, `tenants`, from
  `apps/aurelius-atlas-server/docker/`; the webapp (its own nginx, fed by the
  one-shot `webapp-config`) from `apps/aurelius-atlas-webapp/docker/`; the
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
  `import_sample.py` and `tenants.py`, the webapp's `config.json` and
  `resolve-nginx.sh`. A relative path in a fragment reads from the fragment's
  own folder (an `include` rebases to its fragment's folder too).
- Shared assets live with their owner, not here: the Keycloak `aurelius`
  theme is `infra/keycloak/themes/aurelius` (mounted read-only), the store's
  configuration and CA are `infra/elasticsearch/`, the certificates are each
  project's own `certs/` (`nx certgen`), and the sample folder is
  `data/atlas-sample/`.

## Conventions

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
  topology — Postgres-backed, prod-mode booted through the `keycloak-build` one shot, like
  the chart (DD-670, DD-676) — and pushes its own telemetry to the
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
SST-, SWA-, SKT-, EMB-11, WPT-10, TRM-11) and of 17.1 (IRT-) name these
tests.

## Removal

The stack is `docker/` (umbrella and the gateway, store, identity and
telemetry fragments in `gateway/`, `elasticsearch/`, `keycloak/` and
`observability/` beside it) and
the six `docker/` folders beside the server, webapp, embedder and the three aux
projects: delete them, its nine root tests, the two
`mkdocs.yaml` nav entries (`Standalone Server`, `Add a Tenant to the
Standalone Server`) and the links from `docs/user-guide/index.md`,
`docs/user-guide/deployment.md`, `apps/aurelius-atlas-server/README.md`,
`infra/keycloak/README.md` and `apps/aurelius-atlas-embedder/AGENTS.md`. The
theme in `infra/keycloak/themes/` outlives it — the chart's realm takes it next
(DD-414 names it the Aurelius look, not the demo stack's).
