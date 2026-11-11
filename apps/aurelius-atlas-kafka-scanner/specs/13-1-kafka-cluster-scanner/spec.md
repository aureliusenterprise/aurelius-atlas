# 13.1 The Kafka cluster scanner

- **Status:** in review
- **Pull request:** #314
- **Records:** adds KSC-01..10 and DD-465..472 (here; DD-470 supersedes DD-465's library
  clause, DD-471 supersedes DD-469); relies on DD-458 and DQS-10 (a service identity of its
  own, 12.2), AUT-02/AUT-10 (azp audiences, scrubbed reads), DD-362 (the m4i models load at
  boot), EWR-11 (a relationship end resolves by guid or unique attribute), DD-223 (e2e rides
  the shared dev stack, never restarted), and ADR 051/052/056.

## Scope

The legacy platform scanned a Kafka cluster into Atlas: an application listed the broker's topics
and registered each one as an `m4i_dataset`, with the topic's schema as its `m4i_field` tree, under
a System and a Collection. It worked, and people avoided it: one environment variable chose the
source, its authentication needed an admin's username and password, it read every topic it found
with no way to name the ones you wanted, it spoke only TLS-plus-OAuth or nothing, and a broker it
could not reach left it hanging instead of failing.

This increment ports the capability, not the friction: `apps/aurelius-atlas-kafka-scanner`, a batch
CLI that runs one scan to completion and exits. One scan lists the broker's external topics
(KSC-02), builds the System/Collection/Dataset tree under the legacy qualified-name rules (KSC-03),
reads each topic's schema from the Schema Registry — or infers one from the topic's own messages
when no subject exists (KSC-04, KSC-05) — and writes the tree through the catalogue server as its
own service identity (KSC-09). A re-scan updates the same entities in place (KSC-07). The job never
touches the store directly.

Delivered here:

| Module        | Holds                                                                  |
| ------------- | ---------------------------------------------------------------------- |
| `settings.py` | the app configuration under `AURELIUS_ATLAS_KAFKA_SCANNER_`            |
| `cluster.py`  | the broker door: the topic list, the cluster id, one message per topic |
| `registry.py` | the Schema Registry door: a subject's latest schema, a schema by id    |
| `fields.py`   | the field tree: Avro, JSON schema, or an inferred payload shape        |
| `graph.py`    | the field tree and topic list to catalogue entities                    |
| `scan.py`     | one scan: the steps, the notices, the one bulk write                   |
| `__main__.py` | the CLI: the run, the Keycloak token, telemetry, the exit code         |

Also delivered: the dev Kafka stack `dev/kafka` (one KRaft broker with a plain and a
SCRAM-authenticated host listener, and a Schema Registry, all loopback-pinned), the dev realm's
`aurelius-atlas-kafka-scanner` service-account client, and the e2e proof against the dev stack.

Explicitly not delivered, with the increment that will:

| Not delivered                                             | Lands with | Why                                                                                                          |
| --------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------ |
| The Helm chart, the CronJob schedule, the prod realm join | 13.2       | The chart track owns deployment (10.x's split); the app first                                                |
| An OAUTHBEARER listener on the dev broker                 | 13.2       | The broker's own identity round (its issuer wiring) is the prod chart's; the door's mint seam is proved here |
| Confluent wire-format decoding of message bodies          | –          | The scan reads schemas, not rows; the sniff only needs the schema id (KSC-05)                                |
| Partitions, replicas, configs, consumer groups            | –          | The legacy scanner registered none of them; the tree is topics and fields                                    |
| Lineage (a process per producer)                          | –          | The legacy scanner registered none; 7.21c reads whatever lands                                               |

## Semantics

Python tests name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056). The catalogue
write is this increment's own contract; the service-identity pairs are 12.2's (DQS-10) and are
cited, not restated.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| KSC-01 | A scan runs as one process: it lists, reads, builds, writes, and exits. Exit 0 is a completed scan — a topic whose fields cannot be read is data with a notice, not a failure. Exit 1 is a run-level failure: a bad configuration, a refused token, a broker that answers no metadata, a refused write.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| KSC-02 | The topics to scan are the broker's external ones. A topic is internal when its name starts with `_` or ends with `-offsets`, `-status`, or `-configs` (`__consumer_offsets`, `connect-configs`, and a MirrorMaker's internal topics are never datasets). `TOPICS` is a comma-separated list of patterns a name must match, case-insensitive, each `*` standing for any run of characters; the default `*` names all external topics. A broker that answers no metadata in the timeout is a run-level failure that names the bootstrap list (the legacy job hung instead).                                                                                                                                                                                                                                      |
| KSC-03 | The tree hangs under the configured System (`SYSTEM_NAME`, default `Kafka Broker`). Its Collection is the broker's cluster id, or `default-cluster` when the broker answers none. Each topic is one Dataset under the Collection. The qualified names follow the legacy rule: the components lowercased, the characters `&` and `-` removed, whitespace runs replaced by a single `-`, joined by `--` — `kafka-broker--<collection>--<topic>` (in that order: the removal runs first, so the hyphen the whitespace rule introduces survives it).                                                                                                                                                                                                                                                                |
| KSC-04 | A topic's schema is the Schema Registry's latest version of the subject `<topic>-value` when the Registry answers one and its type is `AVRO` or `JSON`; that schema's fields are the topic's. A subject that is absent, a type that is neither, or a Registry the settings do not name moves the topic to KSC-05. The field parser never guesses from a name: an unreadable schema is the topic's field-less case, with a notice (KSC-05).                                                                                                                                                                                                                                                                                                                                                                      |
| KSC-05 | A topic with no Registry subject is read from its own messages. The job reads the topic assigned at its log end — no consumer group, so a scan leaves no offsets behind — rewinds to the last `sniff_messages` offsets (default 100), and takes the first record that answers. A record that starts with the wire-format magic byte `0x00` names a schema id in its next four bytes (big-endian): the Registry's answer for that id is the topic's schema, through KSC-04's parsers. A record that is a JSON object is inferred: each key is one field, typed `string`/`integer`/`number`/`boolean`/`object`/`array`/`null`, an object's keys nested under it. A topic that answers no record, no known schema, or no JSON object keeps no fields and gets a notice — the dataset is still registered (KSC-03). |
| KSC-06 | A field carries a `fieldType` string and hangs under its dataset (`datasets` end), or under its parent field (`parentField` end) when nested. The Avro parser renders composite types as the legacy scanner did: `array<inner>`, `map<value>`, a union as `a \| b`, a named type by its name; a nested record becomes child fields under the field, an array's item a child named `<field>_item`, a map's value a child named `<field>_value`. The JSON-schema parser walks `properties` (a `$ref` resolves through `$defs`, `anyOf` renders as `a \| b`, `oneOf` as `a ^ b`, `allOf` as `a & b`), and nests an object, an array of objects, and each `$ref`'d definition the same way.                                                                                                                         |
| KSC-07 | The scan writes one bulk request per run: the System, one Collection, one Dataset per topic, and every field, each new entity under a request-local temporary guid, with the ends riding `relationshipAttributes` through those temp guids (the webapp suite's idiom, EWR-11). A re-scan is idempotent: an entity the store already holds by its unique qualified name updates in place, no entity duplicates, and an unchanged tree is skipped whole (EWR-08). A removed topic's dataset stays as it is — the scan registers what is, never what was.                                                                                                                                                                                                                                                          |
| KSC-08 | The settings model is the CLI (DD-472): every key has a flag, parsed over the environment. `--dry-run` runs the whole read and writes nothing; it prints one line per entity the run would write, and every notice. `--topic` (repeatable) limits the scan to named topics, matched like `TOPICS` (KSC-02); a broker that lacks a named one is a notice, not a failure. A malformed flag or setting is a configuration error (KSC-01); the secret keys carry no advertised flag.                                                                                                                                                                                                                                                                                                                                |
| KSC-09 | The job authenticates to the catalogue as its own service identity: client credentials of the `aurelius-atlas-kafka-scanner` confidential client (DD-458's pattern), whose token the server accepts for read and write. All catalogue traffic goes through `aurelius-atlas-server-client` — the job never touches the store directly, so auth and audits behave like any client's. A refused mint is a run-level failure (KSC-01): the scan does not speak anonymously.                                                                                                                                                                                                                                                                                                                                         |
| KSC-10 | The broker door speaks the auth ladder (DD-471): `PLAINTEXT`, `SSL` (with `CA_FILE` verifying the broker's and the Registry's certificates), and `SASL_PLAINTEXT`/`SASL_SSL` with `PLAIN`, `SCRAM-SHA-256/512`, or `OAUTHBEARER` (`SECURITY_PROTOCOL` with `SASL_MECHANISM` and its credentials — the settings validator refuses a protocol without its mechanism and a mechanism without its credentials). `OAUTHBEARER` mints its broker token with the same client-credentials source the catalogue legs use; a refused mint fails the run — the scan speaks anonymously to neither. A refused credential is a run-level failure naming the bootstrap list, like a silent broker (KSC-01). Telemetry rides the same OTLP ingest client the quality scanner uses (DD-196).                                    |

## Ported from

Aurelius `apps/m4i-data-dictionary-io` (`sources/kafka/`, ~630 lines). The legacy job chose the
source with `SOURCE=kafka`, authenticated with an admin's username and password, read every topic,
and retried each entity write singly; Aurelius runs its own app, signs as its own service identity,
filters by pattern, speaks an auth ladder, and writes once per scan (DD-465..472). No Java class is
involved.

## Acceptance

| Ids    | Proven by                                                                                                                                                                                                                                      |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| KSC-01 | `tests/test__scan.py` (a completed scan with a field-less notice; a dead broker fails the run)                                                                                                                                                 |
| KSC-02 | `tests/test__cluster.py` (the internal filter, the patterns, the dead-broker message)                                                                                                                                                          |
| KSC-03 | `tests/test__graph.py` (the qualified-name rule, the tree, the cluster-id fallback)                                                                                                                                                            |
| KSC-04 | `tests/test__registry.py`, `tests/test__fields.py` (subject naming, the two kinds, the move to sniff)                                                                                                                                          |
| KSC-05 | `tests/test__fields.py`, `tests/test__scan.py` (the magic byte and id, the JSON inference, the field-less notice)                                                                                                                              |
| KSC-06 | `tests/test__fields.py` (Avro and JSON-schema trees: renders, `_item`, `_value`, nesting)                                                                                                                                                      |
| KSC-07 | `tests/test__graph.py` (temp guids and ends), `e2e/` (a re-scan: one dataset, updated in place)                                                                                                                                                |
| KSC-08 | `tests/test__settings.py` (the flags over the environment, suppressed secrets out of the help), `tests/test__scan.py` (dry-run writes nothing; the topic filter and its missing-topic notice), `tests/test__main.py` (an unknown flag exits 1) |
| KSC-09 | `e2e/` against the dev stack (the scanner's own token writes the tree, and it reads back)                                                                                                                                                      |
| KSC-10 | `tests/test__cluster.py` (the config shapes: CA, SCRAM, the OAuth provider and its refusal; the ladder validator in `tests/test__settings.py`), `e2e/` (the scan reads the real broker plain and over SCRAM; a wrong secret fails the run)     |
