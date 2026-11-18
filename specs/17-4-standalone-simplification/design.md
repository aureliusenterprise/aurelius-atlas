# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-694. The stack serves localhost and holds no host value

- **Status:** Proposed
- **Increment:** 17.4
- **Date:** 2026-11-19
- **Supersedes:** DD-678 (one host value reached through the proxy's `extra_hosts`) and the host-rendering
  mechanism of DD-680 (the realm host comes from the import). DD-679's certificate rule stays, narrowed to
  the one host the stack serves, and DD-681's certificate script stays unchanged. DD-693 already retired the
  Python resolver this increment's suites would otherwise have needed.

**Decision.** The stack serves `https://localhost:9000` and names no other host. `docker/gateway/nginx.conf`
carries `server_name localhost` as it sits in the repository, and the proxy mounts it straight into
`/etc/nginx/conf.d` as a bind, so the proxy reads the file the person edits. The webapp's browser
configuration `config.json` keeps its place in `apps/aurelius-atlas-webapp/docker/`, carries `"url":
"https://localhost:9000/auth"`, and is served by the webapp through the proxy's catch-all `location /`. The
proxy's dedicated `location = /config.json` block, which existed only to serve a host-rendered copy ahead of
the webapp's own file, is deleted, and the `gateway-conf` and `gateway-static` named volumes go with it. The
variable `STANDALONE_HOST` disappears from every piece, the realm asset, and the roster. The proxy's
`extra_hosts` entry goes with it, because the in-network applications dial `localhost:9000` and share the
proxy's network namespace, where that address already is the proxy. The realm's five host placeholders
become the literal host, and the runtime option `-Dkeycloak.migration.replace-placeholders=true` goes with
them. A person who wants another host runs the optional script `docker/bin/set-host.sh`, which rewrites the
three host-bearing files and re-issues the edge leaf for the new name (SPC-01, SPC-02, SPC-03).

**Reason.** The user asked for the least custom logic that stays inside Docker Compose. The whole host
subsystem exists to move one string into two files at start, and it costs three services to do it:
`gateway-config` renders both files into two named volumes, `webapp-config` renders the webapp's own nginx
configuration, and the realm import needs a placeholder pass. The stack serves `localhost` today, in the
README, in `nx serve`, in the e2e stacks, and in the bundle check. The level 2 runs of 17.2 and 17.3
measured the non-localhost path once each and recorded that a host change on a store that holds the realm
needs a wipe or an admin-API re-point (SPS-07). A customer evaluation runs on the machine that holds the
Docker daemon, which is the machine the browser is on. The host that no container can dial is the host no
container needs, so the substitution buys nothing that a static file does not already give.

The script keeps the door open without keeping the machinery. It runs once, before the start, and writes the
host into files the person can also edit with an editor. That is the same posture `make-certs.sh` took in
17.2 for certificates: the stack ships its own default, and a person who wants something else runs one
script.

**Alternatives.**

- Keep `STANDALONE_HOST` and render the files with the proxy's own image at start. Rejected: that is the
  `gateway-config` one shot the increment removes, and it keeps two named volumes plus a `depends_on` chain
  to write one word.
- Render the files with `envsubst` in the proxy, as upstream nginx images do. Rejected: the hardened
  `dhi.io/nginx` image carries no entrypoint directory and no `envsubst`, which is the fact that created
  `gateway-config` in 17.2.
- Keep the placeholder and resolve it with a Compose interpolation. Rejected: nginx reads its own file, not
  Compose's output, so interpolation only reaches a file Compose writes. That is a render step under a
  different name.
- Serve the host-rendered `config.json` from the proxy ahead of the webapp's own copy, as the stack does
  now. Rejected: the only reason the proxy overrode the webapp's file was to put the browser host in it.
  With one host written in, the webapp's own file is correct, and the override, its dedicated location, and
  its volume are machinery.
- Ship the whole subsystem behind a Compose profile so a plain `up` skips it. Rejected: the profile does not
  help the person who turns it on, and it keeps three services, two volumes, and one realm option in the
  flat file the bundle ships.

**Consequences.** Five suites lose their host assertions: `tests/test__standalone_host.py` keeps the
certificate rules and loses the issuer and realm host rules, `tests/test__standalone_gateway.py` and
`tests/test__standalone_webapp.py` pin the static `nginx.conf` mount and the webapp's literal `config.json`
instead of the render volumes and the proxy override, and `tests/test__standalone_demo_realm.py` and
`tests/test__standalone_paths.py` read the literal host. The gateway piece drops two named volumes and one
service, and its `nginx.conf` moves from a render template to a bind mount, which the bundle's asset walk
already copies like any other mounted file (SBD-03). `make-certs.sh` keeps its rules and moves into the
scripts folder of DD-699: its edge line names `$HOST` with `localhost` as the default and already adds
`localhost` to every edge leaf. `docker/README.md` loses its host section and gains the script's one line.
The `set-host.sh` script is not a service and appears in no compose file, so the bundle's service set is
unchanged by it (SBD-02).

### DD-695. The webapp serves a static nginx configuration

- **Status:** Proposed
- **Increment:** 17.4
- **Date:** 2026-11-19
- **Supersedes:** the standalone half of the webapp config rendering that DD-679 carried for the stack. The
  chart's webapp init container (DD-262) stays as it is.

**Decision.** The stack ships `docker/webapp/nginx.conf` as an asset and mounts it at the webapp's nginx
configuration path. It names the upstreams and the TLS paths the stack uses, in the same shape the chart's
init container renders, and it carries no ingest token. The `webapp-config` service, the `webapp-nginx-conf`
volume, and `apps/aurelius-atlas-webapp/docker/resolve-nginx.sh` no longer exist in the stack's pieces
(SPC-04).

**Reason.** `webapp-config` fills the webapp image's own nginx template. `resolve-nginx.sh` makes seventeen
substitutions. Two read the container's environment, and both carry a default: the collector's OTLP
endpoint, and the ingest token whose default is the literal `none`. The other fifteen are constants of this
stack: four upstream addresses, four peer names, the Docker DNS resolver, the certificate paths, and three
clauses that resolve to nothing. A one shot that writes fifteen constants, plus two values whose defaults
already name this stack, is a template rendered for the sake of the template.

The token is not needed in the file. The browser's OTLP push reaches the collector through the proxy at
`/otel/` (`docker/gateway/nginx.conf`), which is where the webapp's `otelExporterUrl` sends it. The webapp's
own nginx proxy for that leg is a spare path, and the chart's own copy of it carries the same bearer only
because the chart has no proxy in front of the webapp's port. Leaving it empty keeps the one shot's only
real job undone by choice, so the file can be static.

**Alternatives.**

- Keep `webapp-config` and let it stand. Rejected: it is the second render step the user asked to remove,
  and its whole input set is one optional token plus constants.
- Mount the webapp image's own template and let nginx fail on the placeholders. Rejected: nginx reads
  `${...}` as a variable name it does not define and exits, which is why the chart's init container exists
  (DD-262).
- Move the rendering into the webapp image's entrypoint. Rejected: it would change what the image does for
  the chart and the e2e stacks too, and the chart already has its own init container that does the job.
- Render the file at build time with the bundler. Rejected: the repository stack and the bundle then read
  different files, which breaks the rule that the bundle holds what the pieces mount (SBD-03) and duplicates
  the chart's template a second time.

**Consequences.** The webapp's compose piece loses a service, a volume, and a `depends_on` entry, so the
suite `tests/test__standalone_webapp.py` asserts the mounted file instead of the render. `resolve-nginx.sh`
stays in the repository only if a consumer still reads it. The chart's webapp init container (DD-262) is
unaffected, because it renders the same template for a runtime that has no proxy at the webapp's port. If a
person later needs the browser OTLP leg on the webapp's own port in this stack, the static file gains one
`location` block, which is one edit instead of one service.

### DD-696. The stack's Keycloak starts without a build stage

- **Status:** Proposed
- **Increment:** 17.4
- **Date:** 2026-11-19
- **Supersedes:** nothing. It removes the mechanism DD-676 added for this stack, and it leaves the chart's
  build stage (DD-282, Tier 3) standing.

**Decision.** The stack's Keycloak runs `kc.sh start` with `--import-realm` and the same options it passes
today. The `keycloak-build` one shot no longer exists, and the `keycloak` service keeps the `kc-home` named
volume at `/opt/keycloak`. Docker seeds that volume from the image on a fresh start, and the first start
re-augments the build once into it. A later start finds a current build and writes nothing (SPC-05).

**Reason.** DD-676 added the build stage for the chart's reason, and the chart's reason does not exist here.
The chart's values file states it: the build copies the home to an empty directory and augments there "so
the read-only-rooted runtime finds a current build and rewrites nothing at start". Kubernetes mounts the
container root read-only, so the runtime cannot re-augment at all. Docker Compose has no such rule.

A spike against the image in this workspace (2026-11-19) shows what Compose does give. The image runs as uid
65532, and its home `/opt/keycloak` belongs to root, so the image's own root cannot be written. Compose's
volume seed fixes this where it matters: on a fresh named volume at `/opt/keycloak`, the seeded tree belongs
to 65532 and is writable. The image carries its build as `lib/quarkus-run.jar`, owned by 65532, and `kc.sh
build` reports "Server configuration updated and persisted" when run as 65532 in that volume. So the
runtime's own re-augmentation writes where it needs to, with no extra service and no root user. The same
mechanism already runs in this stack for Elasticsearch, whose volume needs a chown because it holds a data
directory the image does not ship.

Dropping the stage removes a JVM start from every cold boot, and it removes the parity burden of keeping the
build options and the start options equal. DD-676 named that burden itself: the four telemetry flags are
build options in production mode, so the build must pass the exact values the start passes, or the runtime
re-augments and the stage buys nothing.

**Alternatives.**

- Keep the build stage for parity with the chart. Rejected: the chart needs it because Kubernetes mounts a
  read-only root, and Compose does not. Parity for its own reason costs a JVM start on every cold boot.
- Drop `kc-home` and let the runtime re-augment into the image's writable layers. Rejected: the home is
  root-owned for the image's uid (spike: `drwxr-xr-x 1 0 0`), so the re-augmentation cannot create the files
  it needs. The volume is what makes the home writable.
- Run the service as root so the image root becomes writable. Rejected: it trades one added service for a
  root container, and the hardened image runs as 65532 on purpose.
- Use `start-dev`. Rejected: it is the development listener the chart and the stack both rule out (CHT-16),
  and it skips the production build check the increment wants to keep.

**Consequences.** `docker/keycloak/compose.yaml` loses one service, one `depends_on` entry, and the four
build options the start no longer needs to mirror. The cold boot pays one re-augmentation instead of a
separate build container, and the measured re-augmentation took 2.7 seconds in the spike.
`tests/test__standalone_demo_realm.py` drops its build-stage assertion. The first start after `down -v` logs
the Quarkus augmentation once, which is expected and not a broken setup. The chart's statefulset and its
`kcBuild` values stay, with the read-only reason already recorded in DD-282.

### DD-697. The demo one-shots move behind a profile and a script

- **Status:** Proposed
- **Increment:** 17.4
- **Date:** 2026-11-19
- **Supersedes:** nothing. It widens the tenancy profile 15.4's `tenants` one shot already used, and it
  retires the bundle's auto-import of 17.3 (the `SAMPLE_ZIP` line of DD-684's roster).

**Decision.** `sample-import` gains the profile `demo` and keeps everything else. `tenants` keeps its
profile `tenancy`. The always-on stack starts neither. Two scripts start them on demand, both in the scripts
folder of DD-699: `docker/bin/import-sample.sh` runs `docker compose run --rm sample-import`, and
`docker/bin/provision-tenants.sh` runs `docker compose run --rm tenants`. Each passes the stack's env files
and names no secret. The bundle's `.env` drops the `SAMPLE_ZIP` line the bundler wrote for it (SPC-06, SPC-07).

**Reason.** A demo import that runs on every start surprises a person who wants an empty store, and it costs
an authentication round trip and a server wait on boots that import nothing. The import needs the server,
the issuer, and the truststore all up, so it also extends the start. The tenants one shot already sits
behind a profile, and the README names it as a step a person takes when they want tenancy, not as part of
the start.

The user asked for these two to leave the stack as external scripts. A Compose profile is the tool's own way
to hold a service back, and `docker compose run` is the tool's own way to start a service once with its own
configuration, its own `network_mode`, and its own `depends_on` conditions resolved. A script that shells
out to `docker run` would rebuild that wiring by hand: the network namespace, the certificates, the env
files, and the sample folder. The scripts therefore stay thin: one `docker compose run` each, with the env
files the umbrella's own start passes.

**Alternatives.**

- Delete the two services and put their whole service definition in a script. Rejected: the script repeats
  the image, the mounts, the network mode, and the environment, which is the second copy of a service
  definition that SBD-07 forbids.
- Keep both behind profiles with no script. Rejected: the person then types a five-line `docker compose run`
  with three `--env-file` arguments, and the README step becomes something they copy from the source instead
  of run.
- Keep the auto-import and let it run only on an empty store. Rejected: the one shot cannot tell an empty
  store from one that failed to import, and a retry on a partially imported store duplicates the sample.
- Move the import into the server's own boot as a start-up task. Rejected: it couples the server's start to
  the sample and moves the failure into a readiness check the server does not own.

**Consequences.** The flat file still carries both services, so SBD-02's service-name equality and SBD-07's
no-copy rule stay green, and the bundle's asset walk still copies `import_sample.py` and `tenants.py`. A
profile changes the `up` behaviour and nothing else, so the three e2e stacks that extend these pieces are
unchanged. The bundle README gains two lines, and the person's first start is shorter by the import.
`tests/test__standalone_bundle.py` loses the `SAMPLE_ZIP` assertion and `tests/test__standalone_store.py`
keeps the store's own rules. The two scripts travel in the bundle because DD-699 ships their folder.

### DD-698. Two one shots stay, with the reason for each

- **Status:** Proposed
- **Increment:** 17.4
- **Date:** 2026-11-19
- **Supersedes:** nothing. It records the answer to the question this increment started from, which was
  whether any one shot is a symptom rather than a need.

**Decision.** `jwks-fetch` stays in `docker/observability/compose.yaml`, and `elasticsearch-volume-init`
stays in `docker/elasticsearch/compose.yaml`. Each carries a comment that names the constraint it answers,
and this entry is the record those comments point to (SPC-08, SPC-09).

**Reason.** The user's question for this increment was which of the stack's mechanical fixes are needs and
which are symptoms of a fixable design. Five are symptoms and this increment removes them. These two are
not, and the reason is the same shape in both: a container that cannot do the thing at the moment it needs
it.

`jwks-fetch` exists because the collector validates the stack's issuer `https://localhost:9000/auth`, and
that address is the proxy's browser address. No in-network container can dial it: `localhost` inside a
container is that container, and the proxy's published port is on the host. The collector's OIDC extension
has no key-file option and no separate JWKS URL, so the keys must be a file the collector reads. The one
shot dials the issuer through the proxy's network namespace, where the address does work, and writes the
file the collector mounts. The alternative that removes the service is to run the collector in the proxy's
network namespace, which mixes a telemetry collector into the edge and gives the browser leg a second route
it does not need.

`elasticsearch-volume-init` exists because the store's volume holds directories the image does not ship, and
Elasticsearch refuses to start when they belong to the wrong user. Compose has no `fsGroup`. The chart
answers the same rule with `fsGroup: 1000` on its pod, which its own header comment names as the in-cluster
shape of this one shot. The alternative that removes the service is a root `chown` command inside the
Elasticsearch entrypoint, which means running a hardened image as root.

**Alternatives.**

- Remove both and accept a broken start. Rejected: the collector answers every OTLP push with a token error,
  and the store refuses its data directory.
- Keep them silent, as they are today. Rejected: a reader who finds a one shot with no reason writes a spec
  to remove it, which is how this increment began.
- Fold `jwks-fetch` into the observability slice. Rejected: the dev slice's Keycloak publishes real
  listeners the slice can dial, so the slice needs no fetcher. The need belongs to the stack's proxy-fronted
  issuer.

**Consequences.** The two services appear in the flat file and in the bundle, and
`tests/test__standalone_observability.py` and `tests/test__standalone_store.py` keep their assertions. The
next person who audits the stack for custom logic finds the reason beside each service instead of
discovering it at a failed start. The removal of the other five one shots leaves these two as the only
services that run once before another service starts.

### DD-699. Every script a person runs sits in `docker/bin/`

- **Status:** Proposed
- **Increment:** 17.4
- **Date:** 2026-11-19
- **Supersedes:** the location of `docker/make-certs.sh` that DD-681 and DD-691 recorded for increment 17.2.
  Their rules about what the script makes and how it finds its password stay as written.

**Decision.** The stack keeps the scripts a person runs by hand in one folder, `docker/bin/`. It holds
`make-certs.sh`, which 17.2 placed at `docker/make-certs.sh` and which this increment moves, plus the three
scripts this increment adds: `set-host.sh`, `import-sample.sh`, and `provision-tenants.sh`. Every script in
the folder finds the stack's root two folders above its own file, so the folder's depth is the one fact each
script holds about its place in the tree. The bundler copies the whole folder, which becomes part of the
files a bundle ships (SPC-11).

**Reason.** The stack's folder already holds three kinds of thing: the umbrella compose file and its pieces,
the roster and the certificate material, and now four scripts a person types by hand. The scripts are the
only kind with no home of their own, and 17.4 was about to add three more beside the existing one. One folder
names the set for the reader, and the README points at one place instead of four lines.

The bundler has a harder reason. It ships the files the compose file mounts, plus the roster, the script, and
the manifest named in its own list. A script that no service mounts travels only if that list names it. The
three new scripts name no mount, so a bundle would ship a README telling a person to run
`docker/bin/import-sample.sh` beside a folder that does not hold it. Copying the folder fixes that for every
script the stack adds later, and it keeps the rule mechanical: the folder is shipped.

**Alternatives.**

- Leave the four scripts loose in `docker/`, as this increment's first draft did. Rejected: the folder then
  holds the umbrella, the pieces, the cert material, the roster, and four scripts, and nothing tells a reader
  which files they are meant to run.
- Name the folder `scripts/`. Rejected: the repository's two `scripts/` folders hold scripts a machine runs,
  `infra/observability/scripts/init-grafana.sh` on a start and
  `apps/aurelius-atlas-webapp/scripts/check-webapp-purity.sh` from an Nx target. `bin/` is the name for
  programs a person runs.
- Put the folder at the repository root. Rejected: the scripts belong to the standalone stack in `docker/`,
  and a root `bin/` would compete with `tools/` and the Nx targets that already cover a developer's work.
- Ship only the scripts the bundle's README names. Rejected: the list would be a second copy of the folder's
  contents inside the bundler, which is the second list SBD-07 forbids.

**Consequences.** `make-certs.sh` moves with `git mv`, and its two anchor lines change: the stack's root
becomes two folders up instead of one. The paths it writes stay the same, because the folder's depth replaced
the script's own. `tests/test__standalone_host.py` reads the script at its new path, and
`tests/test__standalone_bundle.py` gains the assertion that a bundle holds all four scripts. The bundler's
file list names the folder instead of the one script. `docker/README.md` and `docker/AGENTS.md` name the new
path, and increment 17.3's design record DD-688 keeps its sentence about the script computing its root from
its own location: that entry is superseded by DD-689, and this entry records the one-line change to the
anchor.
