# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-465. The broker door is `kafka-python-ng`, and the Registry door is plain HTTP

- **Status:** Proposed (the library clause is superseded by DD-470; the Registry clause stands)
- **Increment:** 13.1
- **Date:** 2026-11-10

**Decision.** The scan reads the broker with `kafka-python-ng` (admin client plus one consumer)
and the Schema Registry with its plain REST API over `httpx2` (KSC-02, KSC-04, KSC-05). The legacy
job's `confluent_kafka` library is not used, and no Kafka wire-format decoding lands with this
increment.

**Reason.** The image is `dhi.io/python:3.14-alpine3.24` and the wheel install is
`--only-binary :all:` (no compiler in the build). `confluent-kafka` ships native `librdkafka`
wheels for glibc and macOS only — there is no musllinux wheel — so it cannot install in this
workspace at all (checked against PyPI at the time of writing). `kafka-python-ng` is pure Python,
answers everything the scan needs (the metadata request carries the cluster id and the internal
flag from v2 on, and one `assign`/`seek` consumer reads a topic's tail), and installs everywhere
this workspace runs. The Registry's wire protocol is one JSON document per subject; speaking its
REST directly keeps the dependency list at pure-Python wheels and the sniff honest — the magic
byte and schema id of KSC-05 are four lines of parsing, not a serializer stack.

**Alternatives.** `confluent-kafka`, as the legacy job used: the right library on paper, and
undeployable here — a glibc base image or a compiled wheel build was rejected for one scanner
job when a pure-Python door covers its whole contract (a bounded read of a topic's tail).
`aiokafka`: async, but no admin surface at all (no topic list, no cluster id), so the scan would
need a second library anyway. Redpanda's `pandaproxy` or the Kafka REST Proxy: one more service
to deploy between the job and the broker, for a batch job that runs next to it.

**Consequences.** The scan's broker contract is what `kafka-python-ng` answers: PLAINTEXT and SSL
with a CA file (KSC-10), and SASL/OAUTHBEARER lands later only if a real deployment needs it
(KSC-10's clause). The consumer is used in a managed `assign` mode with no group membership, so
the fresh-group rewind of KSC-05 never registers a consumer group on the broker. A future
increment that needs transactions, idempotent producing, or librdkafka's tuning knobs reopens this
entry.

### DD-466. One bulk write with request-local temp guids carries the whole tree

- **Status:** Proposed
- **Increment:** 13.1
- **Date:** 2026-11-10

**Decision.** One scan builds every entity of its tree — the System, the Collection, each Dataset,
each field — as request entities under request-local temporary guids (`-0`, `-1`, …), with the
ends stated once as `relationshipAttributes` naming those temp guids, and writes them in one
`create_or_update_bulk` call (KSC-07). The store resolves the ends inside the request (EWR-11: an
end resolves through the request's guid assignments, and a re-scan resolves an entity by its
unique `qualifiedName`). The legacy per-entity retry loop is gone with the per-entity writes.

**Reason.** The legacy job created each entity on its own, retried each singly ten times, and
still lost ordering races: a field written before its dataset existed resolved nothing. The
server already answers the whole graph in one request — the webapp e2e seeder is this idiom in
production use, and a bulk request is one atomic authorisation, one `runId` worth of audit
events, and one round trip per scan instead of one per entity. Idempotence comes from the store's
own identity rules at no cost to the job: the re-scan path needs no read-before-write of its own.

**Alternatives.** Read the tree first and diff, then write only changes: a second read surface
and a second race — the store's unchanged-skip (EWR-08) already saves the write of anything that
did not change. Topologically ordered single writes with retries, as the legacy: one hundred
round trips for a fifty-field cluster, and the retry loop hides a store that is refusing rather
than slow. Kafka Connect or a source system: a deployment of its own for a batch read.

**Consequences.** The graph builder is a pure function (topic list and field trees in, entity
list out) and is unit-tested without a store (KSC-07's first half). The e2e proves the real
resolution: a re-scan of the same topics must not duplicate the dataset. A cluster larger than
the server's bulk limit would need batching; no cluster in scope comes close, and the scan says
so loudly by failing (KSC-01) rather than writing half a tree.

### DD-467. A topic is internal by its name, and `TOPICS` filters the rest

- **Status:** Proposed
- **Increment:** 13.1
- **Date:** 2026-11-10

**Decision.** A topic is internal, and never a dataset, when its name starts with `_` or ends
with `-offsets`, `-status`, or `-configs` (KSC-02). The rest pass unless `TOPICS` names patterns
that exclude them: a comma-separated list, case-insensitive, `*` as the wildcard, any match
admits. `--topic` on the CLI adds exact names the same way (KSC-08).

**Reason.** The broker's metadata answers the internal flag only for `__consumer_offsets` (and
only from Metadata v1), while Connect and MirrorMaker keep their bookkeeping in ordinary topics
(`connect-configs`, `mm2-offsets.*`) that carry the flag false. The legacy filter asked
`not name.startswith("_") or name.endswith(("-offsets", "-status", "-configs"))` — an `or` that
lets every non-underscore name through whatever it ends with, so the filter only ever worked for
`__consumer_offsets`. One name rule, true for all of them, is honest about what it is: a
convention, not a protocol fact. The pattern list is the feature the legacy job never had — a
1,000-topic cluster is not a 1,000-dataset catalogue unless the operator said so.

**Alternatives.** Trust the metadata's `is_internal` flag alone: correct for the consumer offsets
topic and wrong for every bookkeeping topic, which is the dataset soup the legacy scanner's output
was famous for. A regex list: stronger, and an operator-facing foot-gun (one bad pattern fails a
scan) where glob patterns fail safe — a pattern that matches nothing skips everything, visibly.
Per-topic `--dataset` flags only: fine for three topics, unusable for three hundred.

**Consequences.** A new bookkeeping convention (a connector that names its state `my-connector-
state`) is a dataset until `TOPICS` excludes it — the same judgement the legacy job made, now
under the operator's control. The glob translation is four lines and fully unit-tested (KSC-02).
A missing named topic is a notice (KSC-08), so a renamed topic changes the scan's output loudly
without failing it.

### DD-468. The field tree comes from the Schema Registry first, then from the topic's own messages

- **Status:** Proposed
- **Increment:** 13.1
- **Date:** 2026-11-10

**Decision.** A topic's fields come from the Registry subject `<topic>-value` when it exists and
is Avro or JSON schema (KSC-04); otherwise the job reads up to `SNIFF_MESSAGES` (default 100) of
the topic's newest records through a managed assign at the log end — no consumer group is
created — and takes the first that answers: the wire-format magic byte names a schema id the
Registry resolves, else a JSON object infers a field per key (KSC-05). Nothing answers: the
dataset is registered with no fields and a notice. The parsers are pure functions of the schema
text (KSC-06), shared by all three doors.

**Reason.** This ladder is what the legacy scanner did, and its output was the good part of it:
Registry-backed topics get the real schema with nesting, and group-`_item`/`_value` children;
schemaless JSON topics get their shape inferred; a binary topic registers as a dataset without
invented fields. The managed-assign read keeps the scan from the side effect the legacy consumer
had: the legacy `subscribe`/`poll` joined a real consumer group, so scanning a cluster created
groups and committed offsets as a side effect of reading metadata. Reading the newest messages
through `assign_at_end` plus a rewind of N offsets answers the same question (what does a record
here look like) without leaving anything on the broker, and never waits: a topic with no new
records is the field-less notice, not a five-second poll per topic.

**Alternatives.** Registry only: clean, but the legacy corpus's schemaless JSON topics — the
IoT ones the demo corpus is full of — would register field-less, a visible quality loss against
the scanner being replaced. Consume from the earliest offset, as the legacy: a week-old record
describes a deleted schema, and a busy topic's first message can be a full poll timeout away.
Avro decoding of a sniffed record: the scan needs the schema, not the row; decoding needs the
writers' schemas and buys nothing KSC-05 asks for.

**Consequences.** The Avro door uses the `avro` package's schema compiler (pure Python, same
wheel policy as DD-465), not `confluent_kafka.avro`; the union and named-type renders of KSC-06
keep their unit pairs. `SNIFF_MESSAGES` is one bound, applied once per topic, and it costs one
metadata plus one fetch request per schemaless topic. The JSON inference is first-record only: a
topic whose producers disagree gets the first shape seen, marked by the same qualified-name rule
as everything else (KSC-03).

### DD-469. The dev broker stays PLAINTEXT on loopback; the catalogue identity carries the scan

- **Status:** Proposed (superseded by DD-471)
- **Increment:** 13.1
- **Date:** 2026-11-10

**Decision.** `dev/kafka` runs one KRaft broker (single node, `auto.create.topics` on) with a
PLAINTEXT listener published on `127.0.0.1:29092` and a Schema Registry published on
`127.0.0.1:28081` (KSC-10, CHT-101's loopback rule). The scan speaks to both without credentials.
The job's own security boundary is its catalogue service identity (KSC-09, the DD-458 pattern).
A broker that demands SASL or TLS gets that decision with the prod chart (13.2), not here.

**Reason.** The template's dev Kafka carried five listeners (SSL, mTLS-required, two OAuth, and a
controller plane) because it served a streaming platform: Java producers, Connect, Node-RED, and
a UI all rode it, and ADR 013's machine identity applied to each. Aurelius has one consumer of a
Kafka broker — this batch job — and its write path is the catalogue server: every entity the scan
registers is authorised and audited as the scanner's own service account, whatever transport it
used to read the topic. A credentialless read of a credentialless broker inside the dev machine
is therefore exactly as strong as the legacy TLS-only stack was, and costs no realm, no
truststore generation, and no password plumbing — the plumbing the legacy job's README apologised
for. Keeping the listener set at one also keeps the compose file reviewable, which the five-
listener original was not.

**Alternatives.** The template's full TLS/OAuth broker again: proven, and the reason this task
exists — the user's own word for the legacy implementation was "hard to use." PLAINTEXT with a
SASL/OAUTHBEARER listener ready but unused: a listener no test rides is drift waiting to happen.
mTLS-only with the scan carrying a client certificate: moves the scan's secret story from one
(SOPS) to three (SOPS plus the truststore password plus a keytool import), for a dev-only
transport.

**Consequences.** The scan's SSL settings (`CA_FILE`, a `bootstrap.servers` list) are still
implemented and unit-tested (KSC-10) — a SASL broker needs a door change, not a rewrite, and 13.2
owns when. `dev/kafka` ships no metrics-puller sidecar yet: the realm has no `otel-kafka` client,
and adding one belongs with the prod identity round the chart increment takes. The loopback pins
join the root contract suite (`tests/test__dev_stack.py`) so a widened bind fails CI.

### DD-470. The broker door is upstream `kafka-python` 3.x, not the `ng` fork

- **Status:** Proposed
- **Increment:** 13.1
- **Date:** 2026-11-11
- **Supersedes:** DD-465 (its library clause)

**Decision.** The broker door (DD-465) speaks the revived upstream `kafka-python` at 3.x.
The `kafka-python-ng` fork named there is gone from the dependency list; the Registry clause
of DD-465 stands as written.

**Reason.** The fork is archived on GitHub: its last release (2.2.3, October 2024) stops at
Python 3.12, and this workspace runs 3.14 (an archived broker door cannot follow the image).
The upstream project answers again — 3.0.13 shipped November 2026, is classified through
Python 3.14, and its wheel is `py3-none-any`, pure Python like the fork, so the musl image
still installs it with `--only-binary :all:`. DD-465 chose the fork over `confluent-kafka`
because that library has no musl wheel; the same reason picks the revived upstream now.

**Alternatives.** Stay on the fork: an archived dependency, untested on the workspace's own
Python, carrying a security-fix debt with no maintainer. `confluent-kafka`: still undeployable
here (DD-465's reason stands). `aiokafka`: still no admin surface (DD-465's reason stands).

**Consequences.** The 3.x API differs from the fork where the door touches it, and the door
follows: `describe_topics` answers each topic under `name` (the fork said `topic`) and each
partition under `partition_index` (the fork said `partition`); the SASL plumbing moved from
`kafka.conn`/`kafka.sasl` to `kafka.net`/`kafka.net.sasl`; an OAUTHBEARER provider must be an
instance of `kafka.net.sasl.oauth.AbstractTokenProvider`, where the fork accepted any object
with a `token()` method. Both distributions ship the same top-level `kafka` package, so the
machine must hold exactly one: an environment that carried the fork was uninstalled before the
upstream went in, because a side-by-side install merges the two trees into a broken module.

### DD-471. The broker door speaks an auth ladder; the dev broker rides it

- **Status:** Proposed
- **Increment:** 13.1
- **Date:** 2026-11-11
- **Supersedes:** DD-469

**Decision.** The broker door speaks the four security protocols Kafka names — `PLAINTEXT`,
`SSL`, `SASL_PLAINTEXT`, `SASL_SSL` — over the settings `SECURITY_PROTOCOL`, `SSL` with a CA
file (`CA_FILE`, KSC-10), and SASL over either with `PLAIN`, `SCRAM-SHA-256`, `SCRAM-SHA-512`,
or `OAUTHBEARER` (`SASL_MECHANISM` and its credentials, KSC-10). The settings validator is the
ladder's gate: a SASL protocol without a mechanism, a mechanism without a SASL protocol, a
password mechanism without its principal and secret, and `OAUTHBEARER` without its issuer trio
are each a configuration error (KSC-01). `OAUTHBEARER` rides the same client-credentials mint
the catalogue and the OTLP legs ride (`aurelius_atlas_otel.ClientCredentialsTokenSource`),
wrapped in the provider library DD-470 demands; a refused mint fails the run rather than
speaking anonymously. `GSSAPI` is out of the ladder: a Kerberos client the image does not ship,
and no Aurelius deployment asks for it. `dev/kafka` grows a second host listener,
`SASL_PLAINTEXT` with `SCRAM-SHA-512`, and a one-shot `sasl-init` service that writes the dev
SCRAM user into the cluster; the plain listener stays, so the dev default scan stays
credentialless. The e2e suite scans over the SASL listener with SCRAM (a dry run: metadata and
the sniff both ride the authenticated connection) and proves a refused secret is the same
run-level failure as a silent broker.

**Reason.** Customer clusters typically answer an authenticated listener — often `SASL_SSL`
with `OAUTHBEARER` against the same Keycloak the platform already runs (the user's own
deployment pattern, and KSC-10's open clause in this spec). DD-469's reasoning that a broker
that demands credentials is a 13.2 decision left the door unable to answer the deployments
the job actually meets; the seam it deferred is the ladder, and a listener no test rides is
the drift DD-469 itself feared. The SCRAM listener — not OAuth — is the dev stand-in because
it needs no issuer plumbing on the broker: the Kafka broker verifies SCRAM against its own
cluster metadata, while an `OAUTHBEARER` listener wants a JWKS or introspection endpoint wired
into the broker config, which belongs with the prod chart's identity round (13.2). The mint
seam itself is unit-proved here (the provider's token and its refusal), and the e2e rides
SCRAM: the ladder's read leg runs on a live broker either way.

**Alternatives.** Defer the whole ladder to 13.2 (DD-469): rejected above. Full OAUTHBEARER on
the dev broker: the broker needs the issuer's public key material and a listener config per
mechanism; that plumbing is the prod chart's own decision, and carrying it in dev now would
make the dev stack a second copy of prod's identity story. OPA or Ranger authorization on the
broker: out of scope — the scan reads metadata and message tails; its write path is already
authorised as its own service identity (KSC-09).

**Consequences.** The door carries a wider constructor (the transport, its mechanism, its
credentials) — one keyword each, and the scan passes them straight from the settings. The
`KafkaCluster` door maps a refused credential to the same `BrokerUnreachableError` it raises
for a silent broker: `kafka-python` refuses both inside the bootstrap, and the run cannot —
and must not — tell them apart (KSC-01). The SCRAM credentials are dev-only values mirrored
in `apps/aurelius-atlas-kafka-scanner/.env` (SOPS, like every dev secret); the e2e conftest
reads them from there and nowhere else. Telemetry's OTLP leg (DD-196) is unchanged. The prod
chart (13.2) inherits the settings and chooses the rung.

### DD-472. The settings model is the CLI

- **Status:** Proposed
- **Increment:** 13.1
- **Date:** 2026-11-11

**Decision.** One pydantic-settings model carries every setting and the run's flags, and its
CLI source parses the command line over the environment: `--dry-run` / `--no-dry-run`,
repeatable `--topic`, and a kebab-case flag for every other key (`--system-name`,
`--security-protocol`, …). The hand-written `argparse` parser goes. A malformed flag and a
malformed environment value are both configuration errors that exit 1 (KSC-01). The secret
fields (`CLIENT_SECRET`, `SASL_PASSWORD`, `SASL_OAUTH_CLIENT_SECRET`, `OTEL_CLIENT_SECRET`)
carry `CliSuppress`, so `--help` never advertises them: the documented interface is the knobs,
not the secrets.

**Reason.** The increment shipped a second argument parser next to the settings model, and
the two could drift: a new setting was half the work from being a flag and fully invisible
when it was not made one. pydantic-settings gives every field its flag for free, with the
same validation as the environment path. Precedence lands where an operator expects: flag
over environment (the source order puts the CLI first). The CLI parses only when the caller
hands it the arguments (`_cli_parse_args`), so a test process never reads its own pytest
arguments as scanner flags. `cli_exit_on_error=False` turns a malformed flag into the same
`SettingsError` family as a bad setting, which `run()` already maps to exit 1 — the tool never
exits 2 from argparse's own error path.

**Alternatives.** Keep the two parsers in step: drift, and the flags exist only for the two
settings the parser named. Typer or Click: another dependency for what the settings model
already does, and neither reads the environment for free. A `--client-secret` flag: a secret
in every process list and shell history, for a key an operator sets in the environment anyway
in every deployment (SOPS, K8s secret) — `CliSuppress` keeps it out of the documented surface.

**Consequences.** `--help` lists every knob with the field's own docstring as help text, so
the configuration table of the app README stays true by construction. `CliSuppress` hides a
field's flag from `--help` (proved by a test that reads the help text); the library's
suppression does not reject such a flag if typed by hand, and the flag still resolves over
the environment — the deployment story (secrets through the environment, always) keeps the
gap harmless, and it is recorded here rather than papered over. The scan's flags ride settings
fields (`dry_run`, `topic`), so `run_scan`'s keyword seam is unchanged.

### DD-533. The broker and Registry move from `dev/kafka` into the scanner's e2e stack

- **Status:** Proposed
- **Increment:** 13.1 (a follow-up to the landed increment: it moves the placement of
  DD-469's and DD-471's dev broker, not their listener or ladder decisions)
- **Date:** 2026-11-12

**Decision.** `dev/kafka` is removed as a shared dev stack. The KRaft broker, the one-shot
`sasl-init`, and the Schema Registry join `apps/aurelius-atlas-kafka-scanner/e2e/docker-compose.yaml`
as the suite's own services, started with the e2e stack and discarded with it. The host ports
stay 29092, 29095, and 28081, spelled as literals in the compose so the advertised listeners
and the publishes cannot drift apart. The SCRAM pair stays in the app's `.env` and reaches
`sasl-init` through `${VAR:?}` compose guards — one value, two places, as db-scanner's Postgres
password does (DD-507). The broker carries no named volumes: the cluster lives in the container
layer, and the suite's teardown (`docker compose down --volumes`) discards it. The e2e target
drops its `up` dependency on the dev Kafka stack, and `tests/test__dev_stack.py` drops the
`kafka` entry from `DEV_COMPOSES`.

**Reason.** Kafka serves exactly one consumer: this scanner's e2e suite. A shared `dev/*`
stack says "several projects ride this", and nothing else does, so every `nx serve` of the
server and every other suite paid for a broker no one read. db-scanner already proves the
shape: its disposable Postgres rides its own e2e compose (DD-507), the suite seeds it, and the
stack drops at the end. A per-run cluster also fits the suite's own rules better — it already
namespaces every topic to `zz<run>` and deletes it, because it shares the broker with nothing
in fact.

**Alternatives.** Keep `dev/kafka` and add a compose under `e2e/` that attaches its network:
rejected — that keeps the always-on stack, the thing the move removes. Keep the stack shared
but make it opt-in (drop the `up` dependency): rejected — a stack the suite must remember to
start is a flake, and conftest had to keep a start-guard for it anyway. Named volumes on the
e2e broker: rejected — `down --volumes` removes them each run, so they only add indirection;
the db-scanner precedent runs its database the same way.

**Consequences.** The e2e run pays the broker and Registry boot once per session (about a
minute, waited by `up --wait` healthchecks) and comes down clean, so no foreign topic or
subject can survive into the next run. DD-223's no-restart rule is untouched: the shared dev
stacks (Keycloak, Elasticsearch, observability) ride exactly as before. `nx scan` of a dev
cluster now needs a broker the operator runs or owns, as db-scanner's dev scan needs a
database (its README spells both); the settings' loopback defaults simply name the e2e stack's
ports. The CHT-101 loopback guard keeps its force on the remaining dev stacks, and the e2e
publishes stay loopback-pinned under CIA-03 like the server's own publish.
