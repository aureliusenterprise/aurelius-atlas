# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-465. The broker door is `kafka-python-ng`, and the Registry door is plain HTTP

- **Status:** Proposed
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

- **Status:** Proposed
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
