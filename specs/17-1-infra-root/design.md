# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log
apply: an accepted entry is never edited except its status line, and a changed
decision is a new entry that supersedes the old one.

## Entries

### DD-667. The three infrastructure slices move to `infra/`, names and all

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17
- **Supersedes:** DD-006, DD-193 and the other dev-slice placements, for the folder; the
  placement element of the series 9.5 and 11.2 DDs that name `dev/*` paths

**Decision.** The three slices move as folders: `dev/<name>` becomes `infra/<name>`. In the same
change, each Nx project takes the name `aurelius-atlas-infra-<name>`, each compose file's `name:`
takes `aurelius-atlas-infra-<name>`, and each Docker network takes
`aurelius-atlas-infra-<name>-network`. The umbrella's `file://../dev/<name>/helm` dependencies and
their lock entries, the root `project.json` inputs, and every live reference in source, tests and
live docs follow. The historical records (accepted specs, the design-log archive, accepted ADRs other
than 065's path citations) keep the old text; ADR 066 names the move.

**Reason.** The folder holds production artifacts: the umbrella installs its charts (ADR 057), and
the specs that grew them are named "Elasticsearch infrastructure" (0.2) and "prod realm" (10.7).
The name `dev/` describes the compose's biggest consumer, not the content. The name pair
`infra/` and the `aurelius-atlas-infra-*` projects say what the folder is at every layer at once,
because a half-renamed layer is the drift this increment exists to end. Doing the folder and the
names in one change leaves one grep to prove the sweep (`IRT-03`); two changes would each prove half.

**Alternatives.**

- Folder only, names kept: cheaper, and it puts the lie in writing again — the project named
  `-dev-` living at `infra/` is what a reader trips on.
- `components/` or `platform/`: `infra/` matches how the root `AGENTS.md` already words the spine,
  and `infra/arc/` shows the folder's word is already in use for infrastructure that is not an app.
- A `file://` alias to keep the old chart paths: hides the move from the lock file, which is the
  record that must show it.

**Consequences.** The rename touches about 130 live references and about 70 historical ones (left
as written). Consumers that attach the networks externally (the libs' e2e conftests, the app guides)
change with it. `git log --follow` still works because each file moves with `git mv` in its own
commit.

### DD-668. The stack's store extends the infra Elasticsearch service

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17
- **Supersedes:** DD-363, for the store's definition; DD-367's rule that the stack owns an Elasticsearch service

**Decision.** The stack's Elasticsearch and its chown one shot become fragments that `extends:` the
services of `infra/elasticsearch/docker-compose.yaml`. The fragment resets `ports` (no published
port), `volumes` and `depends_on`, declares the stack's own named volumes, and sets the heap and the
password from the stack's environment. The image pin, the configuration file, the roles file, the
certificate, the java agent, the healthcheck and the ulimits arrive by inheritance and are no longer
written in `docker/`.

**Reason.** The stack and dev ran the same component from one owner's configuration but two
definitions, and the suite even pinned the duplication (SST-01 compared the two healthchecks as
written copies). `extends` makes the copy one-way: infra owns the definition, the stack states its
differences, and the drift a reviewer had to watch for becomes a parse error.

**Alternatives.**

- `include` of the infra file: impossible as written — the two projects run two Elasticsearch
  services under one name and compose refuses a name clash.
- Keep the copy and keep SST-01's byte-compare: the test then guards a copy that has no reason to
  exist once ownership is settled.

**Consequences.** SST-01's byte-compare becomes an inheritance proof (IRT-05). The infra compose's
placeholders become part of the stack's env contract (DD-669). A change to the infra service reaches
the stack at once, which is the point and the risk this shares with the chart dependencies.

### DD-669. The stack answers the infra placeholders with its env-files, and passes the guards it replaces

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17

**Decision.** The stack runs with three env-files: the server's, `infra/elasticsearch/.env` and
`infra/keycloak/.env`. Where the infra services require a variable the stack answers differently
(`ELASTICSEARCH_PASSWORD`), the stack's own env supplies that name too, so the base's `${VAR:?}`
guards pass while the fragment's `!reset` environment carries the stack's value.

**Reason.** Compose interpolates an `extends` base with the consuming project's environment before it
applies the fragment's overrides (measured on compose v5.7.1). A guard in the base therefore fires
even when the fragment replaces the guarded variable. Passing the guard with the stack's real value
keeps one source of truth — the stack's own password — while the base stays runnable standalone.

**Alternatives.**

- Relax the infra guards to defaults: deletes the fail-loud property the infra comments and
  DD-008's history exist to protect.
- `--env-file` the same file twice under two names: works, and says nothing truer than mapping the
  server's password into the dev-named variable in the stack's env.

**Consequences.** The stack's README, `AGENTS.md` and `docker/docker-compose.yaml` header state the
three env-files. The interpolated value of a replaced guard is never read — the fragment's override
wins — which the README states so a reader does not chase it.

### DD-670. The stack's Keycloak keeps the production topology behind the proxy

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17
- **Supersedes:** the stack's H2 Keycloak of DD-367 and the series 9.5b wiring that runs it in-memory

**Decision.** The stack's Keycloak extends the infra `postgres-keycloak` service as it is — the
image pin, the certificate-copy boot, the healthcheck, the `${KEYCLOAK_DATABASE_*}` credentials and
the named data volume arrive by inheritance — and extends the infra `keycloak` service for its image
pin, memory cap and Postgres dependency, with the listener shape the stack needs written in the
fragment: `command` reset (no RSS, no telemetry leg), `environment` reset (the realm's placeholders,
the `/auth` relative path behind the proxy with `KC_PROXY_HEADERS`, the issuer
`https://localhost:9000/auth`), `ports` reset (none), `networks` reset (the stack's default), and
`volumes` reset to the stack's import folder, the shared theme and the named database volume. The
Postgres service's certificate bind mounts rebase to `infra/keycloak/`.

**Reason.** The stack is a deployment shape of the system, not a demo: the same Keycloak the charts
run, with the same database backing, so a visitor exercises what an operator installs. The H2 copy
existed because the colleague's stack started as a try-me, and it hid real failures a Postgres-backed
issuer shows (the cert-copy boot of the hardened images, the placeholder import path). The issuer
must stay `https://localhost:9000/auth` because the server verifies exactly that issuer (ADR 039's
one-answer rule), which the proxy wiring already gives.

**Alternatives.**

- H2 with a persistent volume: one fewer container, and it keeps the deviation this increment is
  meant to delete; the direction to treat the compose as production-worthy rules it out.
- Extend the Keycloak service for its environment too (map merge): the base's env carries the
  telemetry leg, the truststore `JAVA_OPTS` and the HTTPS listener keys, and `extends` cannot delete
  one key of an inherited map. Resetting the map and writing the stack's values is the honest form.
- Point the stack at the dev Keycloak: shares a realm the e2e suites mutate, and breaks the stack's
  promise of a store apart from dev's (DD-363's separation, kept).

**Consequences.** The stack grows a Postgres container and two volumes; `down -v` clears them with
the rest. DMO-01..03 keep proving the realm, now imported by a Postgres-backed server. The demo's
cold start grows by the Postgres and Keycloak boot (about a minute), which the README's start
section states.

### DD-671. The tests resolve `extends` in a loader, and pin the merged stack

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17
- **Supersedes:** DD-253's loader of 17.1 alone (the standalone merge), for the extends step

**Decision.** `tests/conftest.py` resolves the stack's compose the way compose does: the umbrella,
then each `include`d fragment, then each service's `extends` (a deep merge under the fragment's own
keys, with `!reset` honoured as a replacement marker — PyYAML needs one constructor line for the
tag). The standalone tests pin the merged services, and each fragment declares the named volumes its
services need.

**Reason.** The suite's rule is "read the stack as written," and `docker compose config` needs the
real secrets, which the offline suite (Level 0) must not carry. Resolving the two clauses the stack
actually uses (not a compose engine) keeps the failure messages in rule terms. A missing top-level
volume declaration is compose's `refers to undefined volume` error, so declaring per fragment is
both compose-correct and locally checkable.

**Alternatives.**

- Assert against `docker compose config` output: makes the root suite depend on a Docker daemon and
  decrypted secrets.
- Keep per-file assertions (each fragment alone): proves the pieces, not the merged contract the
  stack ships.

**Consequences.** The loader knows compose's merge rules for the clauses in use and asserts on a
service-name clash, as compose warns. When compose adds a clause the stack uses, the loader grows a
rule or the suite stops passing — loudly, in the suite that exists for this contract.

### DD-672. The rename sweep stops at the ledger line

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17

**Decision.** Live text changes everywhere: source, tests, live docs (`docs/architecture` pages,
`docs/user-guide`, `docs/contributor-guide`, the moved slices' `README.md`/`AGENTS.md`, the mkdocs
nav). Historical text does not: accepted specs and their `design.md` files, the design-log archive,
the conversion index's increment tables, and ADRs other than their path citations to the moved
folders. In `docs/architecture/conversion/spec-map.md`, the live home cells of the moved slices
(`dev/keycloak`, `dev/observability`, `dev/elasticsearch`) change to `infra/<name>`, and this
increment's own row records its home and its `IRT` namespace.

**Reason.** A historical record names the path that was true when it was accepted; editing it
destroys the audit trail (the ledger's own rule). The pointer forward is one ADR plus the spec-map
row, the pattern ADR 065 set one increment ago. A reader who follows an old path into ADR 066 lands
on the truth in one hop.

**Alternatives.**

- Sweep the history too: rewrites 70+ accepted sentences, and turns `git blame` on the ledger into a
  lie.
- Leave the live docs' `dev/` wording with a redirect note: live docs that contradict the tree are
  the drift the whole increment removes.

**Consequences.** `grep -rn "aurelius-atlas-dev\|dev/elasticseach..."` keeps hitting history, so
IRT-03's acceptance command lists the history files it expects. The ADR 065 file is edited only for
its `dev/keycloak/themes` citation, which names a moved path, not a decision. The same holds for
citations of the two sibling folders.

### DD-673. The stack's realm is the production realm's posture: `aurelius-atlas`, no users

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17
- **Supersedes:** DMO-02 and the demo-users element of the 9.5b realm (DD-366, DD-641), for the
  stack's realm; the sample import's `atlas` sign-in of DMO-03

**Decision.** The stack's realm file is `docker/keycloak/aurelius-atlas.json`: the realm
`aurelius-atlas`, the same name as the Helm chart's production asset. It carries the production
service identities — the public `aurelius` client, the confidential `aurelius-atlas-server`,
`aurelius-atlas-provisioning`, `aurelius-atlas-admin` and `aurelius-atlas-validate-entity` clients,
each secret a `${...}` placeholder the Keycloak replace-placeholders migration fills from the
stack's env-files — the `operators` organization with its four role groups, and the service
accounts of the three service clients. It holds no person: no demo users, no per-tenant users, no
passwords of anybody. The realm matches the Helm asset where both speak: same client shape, same
password policy, same themes, and the Helm realm's service accounts are a subset of the stack's
(the validator's joins the stack alone, as the chart mounts its secret at deploy). Because the
realm holds no users, the sample one shot signs in as `aurelius-atlas-admin` by the
client-credentials grant (its service account holds the server's four roles), and the browser
sign-in is bring-your-own-user: an operator creates a person in the console. The tenants one shot
names no administrator either, and adds members afterward.

**Reason.** The stack is a deployment shape of the system (DD-670's own reason), and DD-670 made
its Keycloak the production topology; a realm of demo users is the same mismatch one layer up. The
production posture already proves every flow the stack exercises — the webapp's public sign-in
(client `aurelius`, PKCE), the server's code flow, the service identities' client credentials —
and keeping the two realms alike means one drift guard (`test__the_realm_matches_the_helm_realms_
service_identities`) instead of two estates. Demo users were convenient while the stack was a
try-me; with Helm as the delivery (ADR 057) a visitor who wants a person makes one, exactly as an
operator does.

**Alternatives.**

- Keep the demo users beside the service identities: the stack's realm then grants rights no
  production realm grants, and the password placeholders keep six secrets in `infra/keycloak/.env`
  whose only consumers are users the production posture refuses.
- A separate `docker/keycloak/aurelius-atlas-demo.json` for the try-me path: two realm files to
  keep alike, and the umbrella includes one Keycloak.
- Keep the realm's name `atlas`: the name is the point of the drift guard, and `aurelius-atlas` is
  what the charts import (DD-641 renamed `demo` for the same reason).

**Consequences.** The webapp and server sign-in pages are unchanged (same clients, same realm
name in `config.json` and `AUTH_REALM`). The six user-password keys leave `infra/keycloak/.env`;
`DEMO_USER_OPERATOR_PASSWORD` stays, as it is a store user (the tenants one shot's Postgres role),
not a realm user. The server's audiences gain the admin and validator clients (AUT-02's azp rule
covers the validator; the admin identity's token is what the sample import presents). DMO-01/02/03
keep their ids with the new text, and the 9.5b spec's accepted body stays as history — this entry
is the pointer forward, per DD-672's rule.

### DD-674. Each service owns one compose piece, and the umbrella and its e2e layers both sit on it

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17
- **Supersedes:** nothing. It extends ADR 065's fragment rule to the three aux services and the
  webapp's e2e service

**Decision.** The extractor, the lineage API and the validator each own a piece
`apps/<project>/docker/compose.yaml`: the standalone service in the proxy's network, with its image
variable, its certificate bind mount, its issuer `https://localhost:9000/auth/`, its realm and its
audience — the chart's posture, made standalone (the lineage pair keeps its own client plus
`aurelius` as the extra audience, DD-385). The umbrella `include`s all three, always on, beside the
server, webapp, embedder, store and identity provider pieces. The webapp piece gains the same
standing: its e2e service now `extends` the piece instead of restating the image, volumes and
dependency shape. The server keeps its own two files (its compose carries the tenants profile and
the sample import), and the embedder's existing piece already fitted. The three e2e bases become
layers over the pieces: they reset `network_mode` back onto the stack network and add their master-
realm environment, fixed ports and the external network — the names an e2e suite needs differ from
the standalone stack's, so none of them move into the piece (DD-669's guard rule).

**Reason.** Before this, the umbrella carried no aux service and the aux e2e files each carried a
full service definition of their own, so the standalone story ("try the whole system") was missing
three services that the webapp's pages call, and one service was written twice. A piece beside its
owner is ADR 065's own rule; an e2e layer over a piece is the extends pattern the store and the
identity provider already use, with the same split — the piece is the standalone truth, the layer
states the test's differences.

**Alternatives.**

- E2E-only bases, inherited by the umbrella: a test file is not a deliverable, and the umbrella then
  reads its service definitions from `e2e` folders.
- Profiles for the aux services (`--profile aux`): the webapp's lineage and validator pages fail
  without them, so a default `up -d` shows a broken system. Always on is the honest default.
- One hand-written piece per file with no `extends` in e2e: re-states the env maps the layers
  already override by key, and keeps two copies of each service.

**Consequences.** `docker compose up -d` starts thirteen services; the aux legs inside the proxy
dial `https://localhost:2100x`, which their certificates' SANs cover. The webapp's nginx reaches
the aux services as `proxy:21002`/`proxy:21003` with their service names as SNI. Each aux e2e file
drops to its differences (its ports, master realm, OTel leg), which is where suite-specific fixes
land from now on. `nx e2e` of each aux project is unchanged: the layer still answers the same
service names and ports.

### DD-675. The stack runs its own observability piece, and its collector trusts the stack's issuer from a file

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17
- **Supersedes:** nothing. It answers the "An `infra/` compose for the observability slice's
  consumer side: not planned" line of this increment's scope, and it completes DD-670's
  "no telemetry leg" of the stack's Keycloak

**Decision.** The umbrella gains a ninth piece, `docker/observability/compose.yaml` (IRT-11): the
collector, Prometheus, Loki, Tempo and Grafana, each the infra observability slice's service
extended (ADR 066). The stack's differences are the volumes (named, cleared by `down -v`), the
collector's host publishes (`!reset`: every producer rides the stack's network, not the machine's
loopback), and one forked file, `docker/observability/config/otel-collector.yaml`. The fork keeps
the slice's three credential-typed legs, its identity processors and its pipelines; it changes the
OIDC validator. The slice's validator dials the dev Keycloak's published listeners to discover its
keys; the stack's one issuer is `https://localhost:9000/auth/realms/aurelius-atlas` — the proxy's
browser address, which no container in any network can dial. So the stack's provider carries
`public_keys_file: /jwks/jwks.json`: the extension reads the realm's keys from a file and watches
it, with no discovery call and no extra_hosts. The piece's `jwks-fetch` one shot (the server image,
a 40-line script beside the piece) copies the realm's published JWKS to the shared volume after
Keycloak is healthy, and the collector starts only after it completed.

Every producer in the stack joins the collector: the server and the three aux apps mint through
the stack's issuer as the realm's four `otel-*` clients for the per-service leg
(`otel-collector:4319`), Keycloak pushes its native OTLP with the shared bearer to the legacy leg
(`otel-collector:4320`, the slice's DD-664 shape, truststore included), the webapp's edge exports
through its resolver script's two env-fed placeholders, and the browser pushes ride the stack
proxy's new `/otel/` route to the collector's browser leg. The realm carries the four ingest
clients and the `otel-ingest` audience scope on the public client `aurelius`, as the Helm asset
does; the four share the dev realm's one secret (`OTEL_INGEST_CLIENT_SECRET`, DD-197's dev shape),
and the pieces join every ingest secret unguarded (DD-669's rule): a stack started without them
exports nothing and still serves.

**Reason.** The user asked for one umbrella that includes the observability compose. The dev stack's
Prometheus already scrapes the collector and Grafana already ships the per-service dashboards, so
the whole telemetry system exists at `infra/observability` and only its consumer side was missing
from the stack (the scope's open question). Extending the slice beats including the slice's file:
`include` would run the services under the _slice's_ project name and network, apart from the
stack's, where the apps cannot reach them; `extends` keeps the pieces' services in the stack's
project, in its default network, on its volumes. The file-based validator is what makes the one
fork worth it (the extension's `public_keys_file` disables discovery entirely, checked against the
pinned 0.164.0): any issuer whose URL is a browser address — the chart's ingress, and this stack —
is undialable from inside the network, and a restart window over a dialing validator (the slice's
DD-195 pattern, built on published host ports) cannot be inherited by a stack that publishes none.
The JWKS travels by volume because the realm's key is born on Keycloak's first boot and lives in
its database: the fetch copies it once per start, and a fresh store after `down -v` lands a fresh
key.

**Alternatives.**

- Include `infra/observability/docker-compose.yaml` directly: the services run apart from the
  stack's project and network — the apps could not reach `otel-collector` — and the slice's
  validator would 401 every token of the stack, whose issuer it has never heard of.
- Point the slice's validator at the stack's Keycloak over the network (`http://keycloak:8080/auth/
realms/aurelius-atlas`): discovery and `iss` matching would compare two spellings of one realm —
  the tokens say `https://localhost:9000/auth/realms/aurelius-atlas` — and `ignore_issuer` exists
  only for a single-provider config. One issuer, one file, no split.
- Fork the whole observability config into the stack: four files, five dashboards, and the
  Grafana datasource trio, all copies the slice must keep in step by hand. The fork keeps the one
  file whose content must differ; the rest is read from the slice (ADR 066's read-not-copy rule),
  and one test (`test__the_stack_collector_validates_the_stacks_issuer_from_a_file`) pins exactly
  the difference.
- Pin the collector's issuer to the plaintext in-network URL and set `ignore_issuer`: it loosens
  the trust rule of the ingest legs (DD-193's "who writes" proof runs on the issuer match) to save
  one fetch.

**Consequences.** `docker compose up -d` starts nineteen services; Grafana answers on loopback
:3000, and the slice's dashboards (the server's, the webapp's, the store's, the identity's) read
the stack's series with no change — the stack's Prometheus scrapes the collector's exporter and
the collector stamps every producer's `service.name`, exactly as in dev. One observability stack
runs per machine: the stack and the dev slice share the :9090/:3000 publishes, so a machine that
starts both stops the dev slice first (its own `docker compose ... down`) — the piece's
header says it. The stack's `down -v` clears the telemetry volumes with the rest of the demo. The
e2e layers keep their own OTel world: they override the pieces' token URLs with the dev Keycloak's
(master realm, host-mapped), merge by key, and ride the slice's collector on the observability
network — the suites are unchanged. The slice's `nx up` and the dashboards' pins stay as they are;
the fork is the stack's burden, and its header names the slice's file as the source.

### DD-676. The stack's Keycloak boots in production mode, like the chart

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17
- **Supersedes:** nothing. It extends DD-670's "the production topology" of the stack's Keycloak
  from the database to the boot mode

**Decision.** The stack's Keycloak runs `kc.sh start`, never `start-dev` — the chart's rule for
the same image (CHT-16). Because prod mode persists its build options and the image's
`/opt/keycloak` is read-only for the image's uid, the piece gains a `keycloak-build` one shot:
the chart's `kc-build` init stage as compose. It `extends` the same slice service, builds
`--http-relative-path=/auth` with the database, health and features as env, and writes the home
into the named volume `kc-home`; Docker seeds that volume from the image on first mount, so the
stage needs no copy step, and the runtime mounts the volume over `/opt/keycloak`. The start
states the built options as env at their built values (`KC_DB`, `KC_HEALTH_ENABLED`,
`KC_HTTP_RELATIVE_PATH`, `KC_FEATURES`) so the runtime's parity check passes without
re-augmenting, and names the TLS relaxation off (`KC_HTTPS_ENABLED=false`): the proxy is the
TLS terminator and the issuer stays `https://localhost:9000/auth`, so the plaintext in-network
hop is unchanged (ADR 039's shape). The management interface stays plaintext `:9000` under that
relaxation, so the stack's healthcheck is unchanged.

**Reason.** The user asked for prod mode; the chart already is the prod-mode reference, and a
demo that boots its identity provider in dev mode drifts from what the deployment ships —
dev mode skips the build, the persistence and the checks that caught DD-664's and DD-256's
shape in prod. Measured live before writing this: the build succeeds as the image's uid into a
fresh named volume, and `start` with `KC_HTTP_ENABLED=true` and `KC_HTTPS_ENABLED=false` boots
without the secure-by-default refusal and keeps `:9000` plaintext — the two facts the design
rests on.

**Alternatives.**

- Stay on `start-dev`: the demo's identity provider would keep booting a mode no delivery
  includes, and "production topology" (DD-670) would keep meaning only the database.
- Build at the runtime's own start (bare `start` with no one shot): the boot re-augments into the
  image filesystem at every cold start — ~165 s on the chart's node (its probes' note) — and
  fails outright on a read-only root. The chart's init stage exists for this; the compose match
  is a one shot, not a slower boot.
- `user: "0:0"` on the runtime so it may write the image tree: it trades the image's unprivileged
  posture for a mode the delivery never runs. The volume keeps the runtime read-only-rooted.
- Bake the build into a derived image (`Dockerfile` over `dhi.io/keycloak`): a new build target,
  registry and pin to maintain for a demo; the volume carries the same result with no new
  artifact.

**Consequences.** `docker compose up` builds before it boots: a cold start pays the Quarkus
build (tens of seconds, one time — the home lives in `kc-home` until `down -v`, as the chart's
emptyDir lives until the pod is replaced). The stack runs nineteen-plus-one services with
`keycloak-build` among the one shots. The build's `KC_FEATURES` matches the slice's command line
(`opentelemetry-metrics,preview`) — the two spellings of one choice, pinned equal by the test.
The dev slice stays on `start-dev` (that is its job: fast boot, re-import on a warm store); the
chart and the stack now agree on the mode, and only they.

### DD-677. The gateway is a piece, and the umbrella holds no service

- **Status:** Proposed
- **Increment:** 17.1
- **Date:** 2026-11-17
- **Supersedes:** nothing. It moves the umbrella's only service into a piece of its own

**Decision.** The stack's gateway becomes the tenth piece, `docker/gateway/`: its
`compose.yaml` defines the `proxy` (the stack's only published port, loopback 9000, and the
TLS terminator), and `nginx.conf` moves beside it as the file that piece mounts. The umbrella
`docker/docker-compose.yaml` now only names the project and includes the ten pieces. It keeps
no service, and its `x-certs` anchor retires with the proxy (the gateway's own relative path
reaches the server's `certs/`). `docker/gateway/` sits beside `docker/elasticsearch/`,
`docker/keycloak/` and `docker/observability/`, the four pieces the root owns (IRT-12).

**Reason.** The user asked for a gateway folder beside the other two. The move also closes the
last gap in ADR 065's shape: after it, every folder of the stack is one compose file plus the
files it mounts, and every relative path rebases to its own fragment (DD-671's rule) instead
of one service reading its paths from the umbrella while its config file sits two folders up
in prose. `docker compose config` renders the proxy byte-for-byte as before the move, so the
pieces' include order and the `service:proxy` sharers are unchanged.

**Alternatives.**

- Keep the proxy in the umbrella: one service and one YAML anchor outside the piece rule, for a
  folder count of three instead of four. It was the shape until this entry, and the rule reads
  worse for it.
- Fold the gateway into the webapp's piece: two nginx containers with different owners and files
  in one folder, and the umbrella's comment would still have to explain which nginx is the entry.
- Name it `nginx/`: the folder's job is the role (the one entry, the TLS terminator, the issuer's
  address), not the package. The repo already calls it the gateway in the chart's ingress terms.

**Consequences.** Run the umbrella, never the gateway piece, as with the other nine. The SWA-03
test reads `docker/gateway/nginx.conf`, and a new IRT-12 test pins the umbrella's empty services
and the gateway's loopback publish. The README's layout bullets name the piece, and the
AGENTS.md layout says ten fragments.

### DD-700. The stack's realm seeds the operator; each tenant's users come with their tenant

- **Status:** Proposed
- **Increment:** 17.1 (a change, 2026-11-18)
- **Date:** 2026-11-18
- **Supersedes:** DD-673's "no person" for the operator, and its "the tenants one shot names no
  administrator"; the rest of DD-673 stands

**Decision.** The stack's realm file holds one person, the platform operator `operator`: the realm role
`atlas-operator` and the realm's default roles, a member of `operators` in its read group, with the password
`${DEMO_USER_OPERATOR_PASSWORD}` filled at import. No tenant's user is in the realm file. The profile
tenancy's one shot makes each tenant's users when it provisions the tenant, through the provisioning
client's admin API: `<tenant>_atlas` in all four role groups and the tenant's administrator,
`<tenant>_steward` in read and write, and `<tenant>_scientist` in read, each a member of its tenant alone,
with the password `<TENANT>_USER_<ROLE>_PASSWORD` from `infra/keycloak/.env`. A user already there keeps
its password; a role without a password gets no user. The six passwords of demo and meyn return to
`infra/keycloak/.env.enc`.

**Reason.** The operator is part of the platform, not of a tenant: every deployment of the stack has one,
it joins each tenant that trusts the operators, and the store's own `operator` user already shares its
password. Without it, trying tenancy started with no one who could read a tenant. A tenant's people, on
the other hand, belong to that tenant: they are made when the tenant is, so a stack without a tenant
carries none, a new tenant brings its own, and no tenant's password sits in the realm file.

**Alternatives.**

- No person at all (DD-673): every visitor builds the operator and each tenant's people by hand before
  tenancy can be tried.
- The tenant users in the realm file again: every stack carries the people of tenants it may never
  provision, and a new tenant edits the realm.
- The operator made by the one shot too: it would exist only with the profile tenancy, while the operator
  role and `operators` are in the realm from the start.

**Consequences.** The realm differs from the Helm realm by one person, which the drift guard allows: the
Helm realm's users stay a subset of the stack's. The provisioning client needs `manage-users`, which it
already holds. A Keycloak with its realm already imported keeps it (the import skips an existing realm),
so an existing stack gains the operator after `down -v` or by hand.
