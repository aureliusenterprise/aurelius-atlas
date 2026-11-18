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
and `npx nx certgen aurelius-atlas-webapp` make them. The stack also ships `docker/make-certs.sh`,
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

The six images are the `:local` tags `npx nx docker-build` of each project builds from the checkout. Each
piece names its image through a compose variable: `SERVER_IMAGE`, `WEBAPP_IMAGE`, `EMBEDDER_IMAGE`,
`DATA2MODEL_IMAGE`, `LINEAGE_MODEL_IMAGE`, `VALIDATE_ENTITY_IMAGE`. An install that runs published images
sets those six values and leaves the defaults alone. The embedder and the three aux
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

## Your host and your certificates

The stack serves `https://localhost:9000`. To serve a name of your own, set one value,
`STANDALONE_HOST`, on the start command:

```bash
STANDALONE_HOST=atlas.example docker compose -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env up -d
```

The name sets the address Keycloak signs its tokens with, the return addresses the realm allows, the
certificate the browser checks, and the address the applications dial inside the stack. You add the name
on the browser machine yourself — a hosts-file entry or a DNS record. Inside the stack you set nothing
per service: the proxy answers the name for the applications, so each dials exactly the browser's URL.
The stack publishes the port on this machine only, whatever the name is; reaching it from the local
network is out of scope.

Give the name its certificates before the first start, with the script that ships here:

```bash
docker/make-certs.sh atlas.example
```

The script creates a certificate authority and issues every certificate the stack mounts, with `openssl`
alone. It installs nothing into a trust store (17.2's rule SPS-09): the stack trusts the CA by mount, and
the browser warns once for the host because the CA is private. That warning is expected. Either trust
`docker/certs/ca.pem` in the browser, or accept it.

You can bring your own certificates instead, and then the script stays unused: place your CA and leaves at
the paths `docker/certs.txt` names. Your edge certificate names the host, `localhost` and `127.0.0.1`;
every other certificate names its own service. Changing the host re-issues the edge certificate alone —
the certificates between services never name the browser's host, because those calls go by service name.
The stack's Keycloak also opens a PKCS12 truststore, `infra/keycloak/certs/truststore.p12`, with
`TLS_TRUSTSTORE_PASSWORD`. The script writes that file with the value your env-files carry, so the two
match. Bring your own certificates and you write that file yourself, with the same password, or the
identity provider fails to start.

`docker/.env.example` lists every setting the stack needs. It states the eight folder names as comments rather
than empty keys. Compose prefers an empty value in `.env`, and an empty folder fails the start. In a checkout,
the three project `.env` files carry the secret defaults and `docker/stack.env` carries the folder paths, so
you normally change nothing. An install that ships the stack alone copies the example to `docker/.env` and
fills the secrets and the eight folders.

### Changing the host on a stack that holds data

Keycloak imports its realm when its database is empty and skips a realm that already exists. A restart with
a new `STANDALONE_HOST` therefore moves the issuer, the proxy and the applications, but not the return
addresses stored in the realm, and sign-in fails. Two paths fix it:

Empty the store. `down -v` and start again with the new host. Keycloak imports the realm for the new host
and the store begins empty, as the Stop section says. The catalogue is gone.

Keep the data. Move the realm's two browser clients to the new host through Keycloak's admin API, after
starting the stack on the new host. The bootstrap administrator in the `master` realm signs the calls:

```bash
NEW=atlas.example
KC="https://$NEW:9000/auth"
TOKEN=$(curl -ks -d grant_type=password -d client_id=admin-cli \
    -d username="$KC_BOOTSTRAP_ADMIN_USERNAME" -d password="$KC_BOOTSTRAP_ADMIN_PASSWORD" \
    "$KC/realms/master/protocol/openid-connect/token" | jq -r .access_token)
FIX='(.redirectUris |= map(gsub("//[^:]+:9000"; "//" + $NEW + ":9000")))
    | (.webOrigins |= map(gsub("//[^:]+:9000"; "//" + $NEW + ":9000")))
    | (.attributes["post.logout.redirect.uris"] |= gsub("//[^:]+:9000"; "//" + $NEW + ":9000"))'
for id in aurelius aurelius-atlas-server; do
    client=$(curl -ks -H "Authorization: Bearer $TOKEN" \
        "$KC/admin/realms/aurelius-atlas/clients?clientId=$id" | jq '.[0]')
    uuid=$(printf '%s' "$client" | jq -r .id)
    curl -ks -X PUT -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
        -d "$(printf '%s' "$client" | jq --arg NEW "$NEW" "$FIX")" \
        "$KC/admin/realms/aurelius-atlas/clients/$uuid"
done
```

Sign in afterwards to prove the move. The catalogue, the users and the sample survive both paths only in
the second one — the first deletes them.

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
  routing (the next bullet); the `gateway-config` one shot renders that file, and the webapp's
  `config.json`, for the browser host before the proxy starts (the hardened nginx image has no
  envsubst, SPS-01).
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
  (`apps/aurelius-atlas-webapp/docker/resolve-nginx.sh`, as the chart's init container does). The webapp
  fragment's `config.json` points the webapp at the realm `aurelius-atlas`; the proxy answers
  `/config.json` itself, from the host-rendered copy, because the file names the issuer the browser
  signs in to (SPS-01). Its nginx forwards
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

## Ship the bundle

This page runs the stack from a repository checkout. A person without the repository gets a **bundle** instead:
one archive with the compose pieces, the files they mount, the sample, and the certificate script (ADR 067,
increment 17.3). The release publishes it on the release's download page, and it needs only Docker,
`docker compose`, `bash`, and `openssl`.

From a checkout, `npx nx standalone-bundle -- --version v1.2.3` builds the same archive under `dist/`. The tool
is `tools/standalone_bundle.py`. The bundle is never a committed file (SBD-01). Unpack it, read its `README.md`,
and the three steps in that file start the stack: `bash docker/make-certs.sh`, fill the empty secrets in
`docker/.env`, and `docker compose -f docker/docker-compose.yaml up -d`.

The bundle mirrors this tree, so its pieces, its paths, and its rules are the ones on this page. It carries no
secret, no certificate, and no private key (SBD-04), and it names the release images instead of the `:local`
tags (SBD-06). A `docker/` change reaches a bundle only when the release rebuilds it.
