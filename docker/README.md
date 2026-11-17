# Standalone server

The server image with the Apache Atlas 2.4.0 dashboards and the Aurelius Atlas webapp, behind one nginx entry
on port 9000. It is a way to try them by hand. `nx serve` and the e2e stacks are unchanged.

| Path                             | Service                                                                 |
| -------------------------------- | ----------------------------------------------------------------------- |
| `https://localhost:9000/`        | The Aurelius Atlas webapp, in English or Dutch                          |
| `https://localhost:9000/atlas2/` | The server and its Atlas dashboards                                     |
| `https://localhost:9000/auth/`   | The stack's own Keycloak with the realm `aurelius-atlas`, and its admin |

The store is the stack's own Elasticsearch — `infra/elasticsearch`'s node, extended with the stack's
volumes (ADR 066, DD-668) — so it holds what you import and nothing the e2e suites or `nx serve`
write to the infra store (DD-367). The identity provider is `infra/keycloak`'s too, Postgres-backed
as the charts run it (DD-670), with the stack's own database volume; its address is the issuer the
server verifies, served behind the proxy at `/auth` (DD-363). At every start it imports the realm
`aurelius-atlas` from `keycloak/aurelius-atlas.json` (DD-673). The realm has the same posture as the
deployment's realm of the same name: the service identities the system needs, with each client
secret a placeholder filled from `infra/keycloak/.env`, and the `operators` organization with its
four role groups. It holds no user. To sign in from a browser, you add a person yourself, in
Keycloak's admin console (see Start).

The realm's sign-in pages wear the Aurelius look (DD-414): the theme `aurelius` in `infra/keycloak/themes/`, a
stylesheet over Keycloak's own login theme that brings back the legacy m4i page: the Aurelius Atlas logo over
one white box on a light band, with a teal sign-in button. The account console, which the webapp's Account
security opens, wears the webapp's navbar band and logo over a light sidebar (DD-663). Its logo and favicon
are copies of the webapp's.

## Start

The secrets come from three `.env` files: the server's, `infra/keycloak/.env` and
`infra/elasticsearch/.env` (DD-669). The stack extends the infra services, so the base files' own
required variables must resolve even where the stack states its own value — all three files are
named at every command below. The store and the identity provider use the infra slices'
configuration and certificates, `infra/elasticsearch/certs/` and `infra/keycloak/certs/`, and the
webapp its own, `apps/aurelius-atlas-webapp/certs/`. On a new clone,
`npx nx certgen aurelius-atlas-infra-elasticsearch`, `npx nx certgen aurelius-atlas-infra-keycloak`
and `npx nx certgen aurelius-atlas-webapp` make them.

```bash
docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env up -d
```

The webapp answers at <https://localhost:9000/> and the dashboards at <https://localhost:9000/atlas2/>
once Keycloak is ready. A cold start takes about two minutes now: the stack's Keycloak builds its
runtime once and boots against its Postgres, in production mode as the deployment's does (DD-670,
DD-676); the next start skips the build, until `down -v`. The realm holds no user (DD-673), so the sign-in is
bring-your-own-user. Open Keycloak's admin console at <https://localhost:9000/auth/admin/> as
`KC_BOOTSTRAP_ADMIN_USERNAME`, in the realm `master`, select the realm `aurelius-atlas`, and add a
person under Users with a password. Then give the person a role: open the user's Role mapping tab and
assign the roles of the client `aurelius-atlas-server` — `atlas-admin` does everything, `atlas-read`
and `atlas-write` read and change the catalogue, and `atlas-read` alone reads it. To try a tenant,
add the person to the tenant's organization and its role groups under Organizations instead (see
Tenants). One sign-in serves the webapp and the dashboards, as they share the realm; the admin
console's own session does not sign you in to them. The certificate is the dev CA's, so the browser
asks once, for `localhost:9000`.

The images are `aurelius-atlas-server:local`, `aurelius-atlas-webapp:local`,
`aurelius-atlas-embedder:local`, `aurelius-atlas-data2model:local`,
`aurelius-atlas-lineage-model:local` and `aurelius-atlas-validate-entity:local`;
`npx nx docker-build` of each project builds it from the checkout. The embedder and the three aux
services need their own certificates too: `npx nx certgen aurelius-atlas-embedder`,
`npx nx certgen aurelius-atlas-data2model`, `npx nx certgen aurelius-atlas-lineage-model` and
`npx nx certgen aurelius-atlas-validate-entity`.

## A sample dataset

`SAMPLE_ZIP` names an Apache Atlas export ZIP in `data/atlas-sample/` at the repository root. Once the server
is ready, the `sample-import` service signs in as the client `aurelius-atlas-admin` by the client-credentials
grant (DD-673: the realm holds no user, so the import uses a service identity, whose service account holds
the server's four roles), and posts the ZIP to `admin/import`, through the proxy. Without `SAMPLE_ZIP`, or
when no file has that name, the option is ignored: the service logs why and exits, and the server runs as
without it.

```bash
SAMPLE_ZIP=sample_data.zip docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env up -d
docker compose -f docker/docker-compose.yaml logs -f sample-import
```

The server creates the m4i types of the samples at start-up (ADR 058), so an import creates none. The log ends
with the import's status and its counts by type; a failed import exits non-zero. An import updates the
entities it finds by GUID, so running it again is safe. Other settings:

| Variable                | Default              | What it sets                                                         |
| ----------------------- | -------------------- | -------------------------------------------------------------------- |
| `SAMPLE_ZIP`            | empty: ignored       | The ZIP's file name in the sample folder                             |
| `SAMPLE_DIR`            | `data/atlas-sample/` | The sample folder; a relative path is read from this directory       |
| `SAMPLE_IMPORT_REQUEST` | `{}`                 | Atlas's `AtlasImportRequest` as JSON, such as its `options`          |
| `ATLAS_TASKS_ENABLED`   | `true`: as Atlas     | Whether the task worker propagates classifications after the request |
| `ATLAS_TENANCY_ENABLED` | `false`: as Atlas    | Whether the server serves several tenants (see Tenants below)        |

An import's propagation runs once it ends (DD-361), so an entity shows what is propagated to it a little
later.

## Tenants

`ATLAS_TENANCY_ENABLED=true` serves several tenants from the one stack (ADR 063): a request acts in the one
Keycloak organization its token names, and each tenant has its own indices and background work. Off by default,
the server answers as Apache Atlas does. The profile `tenancy` adds the one shot `tenants`, which provisions the
realm's two tenants at every start, leaving one already there as it is:

```bash
ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env --profile tenancy up -d
docker compose -f docker/docker-compose.yaml logs tenants
```

| Organization | What the one shot makes                         | Catalogue                             |
| ------------ | ----------------------------------------------- | ------------------------------------- |
| `demo`       | the organization and its four `/atlas-*` groups | the sample, `TENANT_SAMPLE`           |
| `meyn`       | the organization and its four `/atlas-*` groups | empty                                 |
| `operators`  | already in the realm file, with its four groups | the stack's catalogue without tenancy |

The realm holds no user (DD-673), so a tenant starts with no members. Add a person to a tenant in
Keycloak's admin console: under Organizations, open the tenant and add the person as a member, then
give the member the tenant's role groups under Groups. A person who belongs to one tenant signs in
to it without a choice. A tenant's administrator, set by `admin <tenant> add <username>` below,
manages the role groups of its tenant's members through Keycloak's admin API, and is refused on the
other tenant, its people and the realm's users. An administrator cannot use Keycloak's admin
console: the console needs the realm's settings, and its members page every user of the realm, which
would show one tenant's administrator the other tenant's people (ADR 063). A realm administrator
adds and removes members, in the console at `https://localhost:9000/auth/admin/` as
`KC_BOOTSTRAP_ADMIN_USERNAME` of `infra/keycloak/.env`, realm `aurelius-atlas`, under Organizations.

`operators` is the platform's organization: a person who is its member holds the operator role, so the
server holds that person at read access outside the tenants (ADR 063). The one shot also gives the
platform a user of its own in the store, named `operator`, an admin of every index (ADR 063's direct
store access). Its password is `DEMO_USER_OPERATOR_PASSWORD` in `infra/keycloak/.env`; it is a store
user, not a realm user. The store has no published port, so it is reached from the stack's network.
`TENANT_SAMPLE` names the export ZIP in `SAMPLE_DIR` that demo starts with, `sample_data.zip` by
default. With tenancy on, `SAMPLE_ZIP` is left unset: the sample goes into demo, not into the stack's
own catalogue.

To add a tenant of your own that lasts, follow the user guide's page `docs/user-guide/standalone-tenants.md`.

At sign-in, a person in several organizations, such as an operator who also reads a tenant, chooses
which to act in. The webapp shows
the tenant in its account menu, and "Switch tenant" there asks for the choice again; the dashboards switch by
signing out and in. Another tenant is provisioned by the server's command, run in the server's image with its
settings:

```bash
ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env \
    run --rm --no-deps --entrypoint python aurelius-atlas-server \
    -m aurelius_atlas_server.provisioning provision acme
```

The command keeps the realm in step too, as the client `aurelius-atlas-provisioning`: it makes the tenant's
organization and its four `/atlas-*` groups, and makes each operator a member who reads it while the tenant
trusts the operators. `list` shows the tenants. `trust acme off` closes a tenant to the operators and removes
them from it. `operators` brings every tenant in step after an operator joins or leaves `operators`.
`admin acme add <username>` lets that user manage the role groups of acme's members, and nothing outside acme.
`remove acme` deletes its indices, about a minute after it stops serving the tenant, then its organization. The
server picks up a new tenant within `tenancy_refresh_seconds`, 30 by default, without a restart. A tenant's
members are added in Keycloak's admin console, or by invitation: Keycloak doesn't yet let a tenant's
administrator list or add them. The stack's Keycloak keeps no data of its own beyond its database
volume: each new container imports `keycloak/aurelius-atlas.json` again, so a change made in its
console lasts across restarts but not across `down -v`.

## How it fits together

The stack is one compose project: `docker/docker-compose.yaml` names it and `include`s every
piece (ADR 065, DD-677) — the gateway from `docker/gateway/`, the server and its one shots from
`apps/aurelius-atlas-server/docker/`, the webapp from `apps/aurelius-atlas-webapp/docker/`, the extractor from
`apps/aurelius-atlas-data2model/docker/`, the lineage API from
`apps/aurelius-atlas-lineage-model/docker/`, the validator from
`apps/aurelius-atlas-validate-entity/docker/` (DD-674), the embedder from
`apps/aurelius-atlas-embedder/docker/`, the telemetry piece from `docker/observability/` (DD-675),
and the store and the identity provider from `docker/elasticsearch/` and `docker/keycloak/`, which
`extend` the infra slices' services and state only the stack's differences (ADR 066). Run the
umbrella; the fragments are not a target of their own.

- `docker/gateway/compose.yaml`: the `proxy`, the stack's only published port (loopback 9000, TLS
  with the server's certificate) and its TLS terminator — the piece DD-677 gives the gateway its own
  folder, beside the store, identity and telemetry pieces. `docker/gateway/nginx.conf` holds its
  routing (the next bullet).
- `docker/elasticsearch/compose.yaml`: `infra/elasticsearch`'s node, extended — its image,
  configuration, roles, certificate, java agent and healthcheck inherited; the stack's volumes
  `elasticsearch-data` and `elasticsearch-snapshots`; no published port (DD-668). The server reaches
  it as `https://elasticsearch:9200` with its own password, which is the `elastic` user's here.
- `docker/keycloak/compose.yaml`: `infra/keycloak`'s Keycloak and its Postgres, extended (DD-670) —
  Postgres-backed and prod-mode booted as the charts run it (the `keycloak-build` one shot builds,
  the start mounts its home — DD-676), the shared theme mounted, the realm `aurelius-atlas` imported
  from `docker/keycloak/`, and the stack's own database volume `keycloak-postgres-data`; no published
  port. The proxy reaches it on its plaintext listener, and its own traces and metrics push to the
  stack's collector (DD-675).
- The proxy's `nginx.conf` is the stack's only reverse proxy. `/atlas2/` goes to the server without
  the prefix (the server knows it as `AURELIUS_ATLAS_SERVER_ROOT_PATH`, so its redirects and its
  sign-in's return lead back under it, 9.5), `/auth/` to Keycloak unchanged (which serves under
  `/auth` itself), `/api/` to the server with its prefix, and `/` and every
  other path to the webapp, whose own nginx, in a container of its own, only serves the webapp's files.
  `webapp-config` fills that nginx's template into the volume `webapp-nginx-conf` before it starts
  (`apps/aurelius-atlas-webapp/docker/resolve-nginx.sh`, as the chart's init container does), and the
  webapp fragment's `config.json` points the webapp at the realm `aurelius-atlas`. Its nginx forwards
  `/lineage-model/` and `/validate-entity/` to the aux services through the proxy's ports, and
  `/otel/` to the collector's browser leg, so the webapp's traces leave the browser through the
  proxy's own port (DD-675).
- `aurelius-atlas-data2model`, `aurelius-atlas-lineage-model` and `aurelius-atlas-validate-entity`:
  the extractor, the lineage API and the validator (DD-674), each in the proxy's network like the
  server, so their issuer is the browser's address and their audience is the chart's posture (the
  lineage pair keeps `aurelius` as its extra, DD-385). They publish no port of their own.
- `docker/observability/compose.yaml`: the stack's telemetry (DD-675) — `infra/observability`'s
  collector, Prometheus, Loki, Tempo and Grafana, extended with the stack's volumes. The collector
  checks tokens against the stack's issuer, read once from Keycloak into a shared file, and the
  server, the aux services, Keycloak and the webapp all push to it. Grafana answers on
  <http://localhost:3000> and Prometheus on <http://localhost:9090>, both pinned to this machine.
  The dev observability slice publishes the same ports, so stop it
  (`docker compose -f infra/observability/docker-compose.yaml --env-file infra/observability/.env down`)
  before starting the stack, and bring it back (`npx nx up aurelius-atlas-infra-observability`) after.
- `embedder`: the embedding model of search by meaning (ADR 059), `https://embedder:21004` on the stack's network
  with its own certificate. It checks no tokens, so it has no published port (DD-432), and nothing waits for it.
  The server embeds every entity through it in the background (11.3): new and changed ones within its poll
  interval, and those stored before at the first start. That start first moves the entity index to one that keeps
  vectors, `aurelius-atlas-entities-000002`, once (DD-439). See `apps/aurelius-atlas-embedder/README.md`.
- The server and the sample import run in the proxy's network (`network_mode: service:proxy`). nginx reaches
  the server on `127.0.0.1:21000` and the webapp as `aurelius-atlas-webapp:8080`, and the server reaches
  Keycloak at `https://localhost:9000/auth`, the
  address the browser uses, so the tokens' issuer is the one the server checks.

## Stop

```bash
docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env down
```

The data stays in the stack's volumes for the next start. `down -v` deletes them, so the next start begins
with an empty store: the server creates Atlas's and the m4i types again, and `SAMPLE_ZIP` imports the sample.
The Statistics chart fills from the hourly snapshots, so a new store's chart is empty until the first full
hour.
