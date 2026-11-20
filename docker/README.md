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
four role groups. Its one person is the platform operator `operator`, who reads `operators` and holds
the operator role, with the password `DEMO_USER_OPERATOR_PASSWORD` (DD-700). A tenant's users are not
in the realm file: the one shot `tenants` makes them when it provisions their tenant (see Tenants).
For any other person, you add one yourself, in Keycloak's admin console (see Start).

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
and `npx nx certgen aurelius-atlas-webapp` make them. The stack also ships `docker/bin/make-certs.sh`,
which makes the same material with `openssl` alone and needs none of the repository's tooling (see
Your host and your certificates below).

The seven app pieces name the folder they mount through a required variable, so a stack that names no folder
fails the start with that folder's name and never reads a path of this repository (SBD-12, DD-687). In a
checkout `docker/stack.env` answers the eight names, and the commands below need no extra argument. An install
that ships the stack without the repository names them in its own `.env`, as `docker/.env.example` explains.

```bash
docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env up -d
```

The webapp answers at <https://localhost:9000/> and the dashboards at <https://localhost:9000/atlas2/>
once Keycloak is ready. A cold start takes about two minutes now: the stack's Keycloak boots against
its Postgres in production mode as the deployment's does (DD-670, DD-676), and its first boot augments
its runtime once into the home volume Compose seeds (SPC-05, DD-696). The next start skips it, until
`down -v`. Without tenancy, the realm's only person is the operator (DD-700), so the sign-in is
bring-your-own-user. Open Keycloak's admin console at <https://localhost:9000/auth/admin/> as
`KC_BOOTSTRAP_ADMIN_USERNAME`, in the realm `master`, select the realm `aurelius-atlas`, and add a
person under Users with a password. Then give the person a role: open the user's Role mapping tab and
assign the roles of the client `aurelius-atlas-server` — `atlas-admin` does everything, `atlas-read`
and `atlas-write` read and change the catalogue, and `atlas-read` alone reads it. To try a tenant,
add the person to the tenant's organization and its role groups under Organizations instead (see
Tenants). One sign-in serves the webapp and the dashboards, as they share the realm; the admin
console's own session does not sign you in to them. The certificate is the dev CA's, so the browser
asks once, for `localhost:9000`.

The six images are the `:local` tags `npx nx docker-build` of each project builds from the checkout. Each
piece names its image through a compose variable: `SERVER_IMAGE`, `WEBAPP_IMAGE`, `EMBEDDER_IMAGE`,
`DATA2MODEL_IMAGE`, `LINEAGE_MODEL_IMAGE`, `VALIDATE_ENTITY_IMAGE`. An install that runs published images
sets those six values and leaves the defaults alone. The embedder and the three aux
services need their own certificates too: `npx nx certgen aurelius-atlas-embedder`,
`npx nx certgen aurelius-atlas-data2model`, `npx nx certgen aurelius-atlas-lineage-model` and
`npx nx certgen aurelius-atlas-validate-entity`.

## A sample dataset

The always-on stack imports nothing. The service `sample-import` sits behind the compose profile `demo`, and
the script `docker/bin/import-sample.sh` runs it once in a stack that is already up (SPC-06, DD-697). It names
an Apache Atlas export ZIP in `data/atlas-sample/` at the repository root, `sample_data.zip` by default.

```bash
docker/bin/import-sample.sh sample_data.zip
```

The script names no secret: it passes the same three env-files every start command names (DD-669). Once the
server is ready, the one shot signs in as the client `aurelius-atlas-admin` by the client-credentials grant
(DD-673: the realm holds no user, so the import uses a service identity, whose service account holds the
server's four roles), and posts the ZIP to `admin/import`, through the proxy. When no file has the name it
names, the one shot logs why and exits, and the server runs as without it. To run it yourself, name the
profile and `SAMPLE_ZIP` on `docker compose run`.

The server creates the m4i types of the samples at start-up (ADR 058), so an import creates none. The log ends
with the import's status and its counts by type; a failed import exits non-zero. An import updates the
entities it finds by GUID, so running it again is safe. Other settings:

| Variable                | Default            | What it sets                                                         |
| ----------------------- | ------------------ | -------------------------------------------------------------------- |
| `SAMPLE_ZIP`            | empty: ignored     | The ZIP's file name in the sample folder                             |
| `SAMPLE_DIR`            | `docker/stack.env` | The required sample folder to mount (a checkout answers it)          |
| `SAMPLE_IMPORT_REQUEST` | `{}`               | Atlas's `AtlasImportRequest` as JSON, such as its `options`          |
| `ATLAS_TASKS_ENABLED`   | `true`: as Atlas   | Whether the task worker propagates classifications after the request |
| `ATLAS_TENANCY_ENABLED` | `false`: as Atlas  | Whether the server serves several tenants (see Tenants below)        |

An import's propagation runs once it ends (DD-361), so an entity shows what is propagated to it a little
later.

## Tenants

`ATLAS_TENANCY_ENABLED=true` serves several tenants from the one stack (ADR 063): a request acts in the one
Keycloak organization its token names, and each tenant has its own indices and background work. Off by default,
the server answers as Apache Atlas does. The always-on stack provisions no tenant: the one shot `tenants` sits
behind the compose profile `tenancy`, and the script `docker/bin/provision-tenants.sh` runs it once in a stack
that already serves tenancy (SPC-07, DD-697). Turn tenancy on first, then provision:

```bash
ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env up -d
docker/bin/provision-tenants.sh
```

The one shot provisions the realm's two tenants, leaving one already there as it is, so a repeat run changes
nothing. The script names no secret and opens the profile for its own run. To provision by hand, turn tenancy
on and run `docker compose` with `--profile tenancy` or `run --rm tenants`.

| Organization | What the one shot makes                         | Catalogue                             |
| ------------ | ----------------------------------------------- | ------------------------------------- |
| `demo`       | the organization and its four `/atlas-*` groups | the sample, `TENANT_SAMPLE`           |
| `meyn`       | the organization and its four `/atlas-*` groups | empty                                 |
| `operators`  | already in the realm file, with its four groups | the stack's catalogue without tenancy |

The one shot makes each tenant's users when it provisions the tenant, not the realm file (DD-700):
`<tenant>_atlas` with every role and the tenant's administrator, `<tenant>_steward` who reads and writes,
and `<tenant>_scientist` who reads, each a member of its tenant alone. Their passwords are
`<TENANT>_USER_<ROLE>_PASSWORD` in `infra/keycloak/.env`, such as `DEMO_USER_ATLAS_PASSWORD`; a user already
there keeps its password, and a tenant without those passwords gets no users. The operator joins every
tenant that trusts the operators, with read access. To add a further person to a tenant, use
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
store access). Its password is `DEMO_USER_OPERATOR_PASSWORD` in `infra/keycloak/.env`, the same as the
realm's `operator`'s. The store has no published port, so it is reached from the stack's network.
`TENANT_SAMPLE` names the export ZIP in `SAMPLE_DIR` that demo starts with, `sample_data.zip` by
default. With tenancy on, `SAMPLE_ZIP` is left unset: the sample goes into demo, not into the stack's
own catalogue.

To add a tenant of your own, with its people and a sample if you name one, run `docker/bin/tenant.sh add <tenant>`;
the user guide's page `docs/user-guide/standalone-tenants.md` explains its options. You edit no file.

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

## Your host and your certificates

The stack serves `https://localhost:9000`, and the host sits written into three files: the proxy's
`gateway/nginx.conf`, the webapp's `config.json`, and the realm file `keycloak/aurelius-atlas.json`
(SPC-02, DD-694). No service renders them at start, and no piece reads a host variable.

Make the certificates before the first start with the script that ships here:

```bash
docker/bin/make-certs.sh
```

The script creates a certificate authority and issues every certificate the stack mounts, with `openssl`
alone. It installs nothing into a trust store (17.2's rule SPS-09): the stack trusts the CA by mount, and
the browser warns once for the host because the CA is private. That warning is expected. Either trust
`docker/certs/ca.pem` in the browser, or accept it.

You can bring your own certificates instead, and then the script stays unused: place your CA and leaves at
the paths `docker/certs.txt` names. Your edge certificate names the host, `localhost` and `127.0.0.1`;
every other certificate names its own service. The certificates between services never name the browser's
host, because those calls go by service name.
The stack's Keycloak also opens a PKCS12 truststore, `infra/keycloak/certs/truststore.p12`, with
`TLS_TRUSTSTORE_PASSWORD`. The script writes that file with the value your env-files carry, so the two
match. Bring your own certificates and you write that file yourself, with the same password, or the
identity provider fails to start.

`docker/.env.example` lists every setting the stack needs. It states the eight folder names as comments rather
than empty keys. Compose prefers an empty value in `.env`, and an empty folder fails the start. In a checkout,
the three project `.env` files carry the secret defaults and `docker/stack.env` carries the folder paths, so
you normally change nothing. An install that ships the stack alone copies the example to `docker/.env` and
fills the secrets and the eight folders.

### Your own host

To serve a name of your own, run the script that ships for it, before the start:

```bash
docker/bin/set-host.sh atlas.example
```

The script writes the host into the three files above and re-issues the edge certificate for it (SPC-03,
DD-694). It changes nothing else: every internal hop stays a service name or a loopback name. Then add the
name on the browser machine yourself, as a hosts-file entry or a DNS record. The stack publishes the port on
this machine only; reaching it from the local network is out of scope. The same thing by hand: edit the
three files and run `docker/bin/make-certs.sh` with the host.

A host change is not a restart. Keycloak imports its realm when its database is empty and skips a realm that
already exists, so a store that holds the realm keeps the old return addresses, and sign-in fails. Clear the
demo and start again (the path that kept the data retired with the host machinery, DD-694):

```bash
docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env down -v
```

The next start imports the realm for the new host, and the store begins empty: the catalogue is gone, as the
Stop section says. Trust `docker/certs/ca.pem` to quiet the browser warning (SPS-10).

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
  routing (the next bullet) as a static asset the proxy mounts: `server_name` carries the host written
  in, so no service renders anything at start (SPC-01, DD-694 — the hardened nginx image has no
  envsubst, which is why the file is static rather than a template).
- `docker/elasticsearch/compose.yaml`: `infra/elasticsearch`'s node, extended — its image,
  configuration, roles, certificate, java agent and healthcheck inherited; the stack's volumes
  `elasticsearch-data` and `elasticsearch-snapshots`; no published port (DD-668). The server reaches
  it as `https://elasticsearch:9200` with its own password, which is the `elastic` user's here.
- `docker/keycloak/compose.yaml`: `infra/keycloak`'s Keycloak and its Postgres, extended (DD-670) —
  Postgres-backed and prod-mode booted as the charts run it, with no build one shot: Compose seeds the
  home volume from the image and the first start augments it once (SPC-05, DD-696), the shared theme
  mounted, the realm `aurelius-atlas` imported
  from `docker/keycloak/`, and the stack's own database volume `keycloak-postgres-data`; no published
  port. The proxy reaches it on its plaintext listener, and its own traces and metrics push to the
  stack's collector (DD-675).
- The proxy's `nginx.conf` is the stack's only reverse proxy. `/atlas2/` goes to the server without
  the prefix (the server knows it as `AURELIUS_ATLAS_SERVER_ROOT_PATH`, so its redirects and its
  sign-in's return lead back under it, 9.5), `/auth/` to Keycloak unchanged (which serves under
  `/auth` itself), `/api/` to the server with its prefix, and `/` and every
  other path to the webapp, whose own nginx, in a container of its own, only serves the webapp's files.
  That nginx reads a static configuration the stack ships at `docker/webapp/nginx.conf`, which names the
  same upstreams the chart's init container renders and carries no ingest token (SPC-04, DD-695). The webapp
  fragment's `config.json` points the webapp at the realm `aurelius-atlas`, and the webapp serves that file
  through the proxy's catch-all (SPC-02). Its nginx forwards
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
  server, the aux services, Keycloak and the webapp all push to it. Grafana answers behind the proxy
  on <https://localhost:9000/grafana/> and signs people in through Keycloak alone (15.9); Prometheus
  answers on <http://localhost:9090>, pinned to this machine. The dev observability slice publishes
  the same Prometheus port, so stop it
  (`docker compose -f infra/observability/docker-compose.yaml --env-file infra/observability/.env down`)
  before starting the stack, and bring it back (`npx nx up aurelius-atlas-infra-observability`) after.
  Each tenant is a Grafana organization of its own, kept by the tenant command (`docker/bin/tenant.sh`):
  two data sources that read the tenant's indices alone, as the store user `grafana_<tenant>_reader`,
  and two dashboards: _catalogue_, the entities by type, state, data domain and owner as created over
  time, and _activity_, the audit events by action and user. The tenant's people are its Viewers and
  land in it; operators are Viewers of the main organization, which holds the stack's telemetry, and
  of every tenant that trusts them. Grafana's local administrator signs in to no one's browser: its
  password, `GRAFANA_ADMIN_PASSWORD` of `infra/keycloak/.env`, is what the command calls the API with.
  After people are changed in the Keycloak console, `docker/bin/tenant.sh grafana sync` brings Grafana
  in step and deletes the Grafana users the realm gives no tenant. The governance-quality results, the
  relationships and the classifications have no time field, so they are not charted yet.
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
with an empty store: the server creates Atlas's and the m4i types again, and the sample waits for
`docker/bin/import-sample.sh`. The Statistics chart fills from the hourly snapshots, so a new store's chart
is empty until the first full hour.

## Ship the bundle

This page runs the stack from a repository checkout. A person without the repository gets a **bundle** instead:
one archive with one flat compose file, the files it mounts, the sample, and the scripts folder
`docker/bin/` (ADR 067, increments 17.3 and 17.4). The release publishes it on the release's download page,
and it needs only Docker, `docker compose`, `bash`, and `openssl`.

From a checkout, `npx nx standalone-bundle -- --version v1.2.3` builds the same archive under `dist/`. The tool
is `tools/standalone_bundle.py`. The bundle is never a committed file (SBD-01). Unpack it, read its `README.md`,
and the three steps in that file start the stack: `bash docker/bin/make-certs.sh`, fill the empty secrets in
`docker/.env`, and `docker compose -f docker/docker-compose.yaml up -d`. The bundle ships the other scripts
too, so the sample and the tenants stay one command away (SPC-11, DD-699).

The bundle's one compose file is this stack resolved by `docker compose config`, so its services and its rules
are the ones on this page, and every `${VAR}` setting still applies. Its folder paths are relative to the
bundle, and the folder answers sit in its `docker/.env` (DD-690). It carries no secret, no certificate, and no
private key (SBD-04), and it names the release images instead of the `:local` tags (SBD-06). A `docker/` change
reaches a bundle only when the release rebuilds it.
