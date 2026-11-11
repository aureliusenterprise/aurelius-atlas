# aurelius-atlas-kafka-scanner

The Aurelius Atlas Kafka scanner: a batch job that reads a Kafka cluster and
registers what it finds — the broker's topics and each topic's fields — in the
catalogue. It is the first cut of the Kafka scanning track
([ADR 051](../../docs/architecture/adr/051-the-conversion-proceeds-in-specified-increments.md),
increment 13.1). The legacy job worked but was hard to use: it needed an admin's
username and password, read every topic it found, and hung on a broker it could
not reach. This one signs as its own service identity, filters topics by
pattern, and fails loudly (
[DV-147](../../docs/architecture/conversion/deviations.md)).

One scan lists the broker's external topics, hangs them under a System and a
Collection named for the cluster, reads each topic's schema from the Schema
Registry — or infers one from the topic's own messages when no subject exists —
and writes the whole tree in one bulk request. A re-scan updates the same
entities in place; it never duplicates and never deletes a removed topic.

The [spec](specs/13-1-kafka-cluster-scanner/spec.md) states the KSC-01..10
rules. The Helm chart and the schedule land with the planned
[13.2](../../docs/architecture/conversion/index.md).

## Scan

```bash
npx nx scan aurelius-atlas-kafka-scanner                 # one scan, writes the tree
uv run python -m aurelius_atlas_kafka_scanner --dry-run  # print the tree, write nothing
uv run python -m aurelius_atlas_kafka_scanner --topic orders --topic payments.avro
```

Exit 0 means the scan completed. A topic whose fields cannot be read is a
dataset with no fields and a notice, not a failed run (KSC-05). Exit 1 means the
run itself failed: bad configuration, a refused token, a broker that answers no
metadata, or a refused write (KSC-01).

## Configuration

Every key carries the `AURELIUS_ATLAS_KAFKA_SCANNER_` prefix and has a
command-line flag (`--system-name`, `--security-protocol`, …): the flag beats
the environment, and `--help` lists them all. The secret keys have no
advertised flag — they are environment settings, so a secret never lands in a
shell history or a process listing (DD-472). The required one:

| Key             | Meaning                                                                                     |
| --------------- | ------------------------------------------------------------------------------------------- |
| `CLIENT_SECRET` | the secret of the scanner's realm client (DD-469's sibling of DD-458) — without it, no scan |

The rest have defaults: `SERVER_URL` (the Atlas server to write to, default
`https://localhost:21000`), `TOKEN_URL`, `CLIENT_ID` (default
`aurelius-atlas-kafka-scanner`), `BOOTSTRAP_SERVERS` (default
`localhost:29092`, the dev broker), `SCHEMA_REGISTRY_URL` (unset means every
topic is sniffed, KSC-04), `SYSTEM_NAME` (default `Kafka Broker`, KSC-03),
`TOPICS` (a comma-separated list of case-insensitive name patterns, `*`
standing for any run of characters, default `*`, KSC-02), `SNIFF_MESSAGES`,
`POLL_TIMEOUT_SECONDS`, `ADMIN_REQUEST_TIMEOUT_MS` (the metadata timeout — the
legacy job had none, KSC-01), `REGISTRY_TIMEOUT_SECONDS`, `CA_FILE` (the CA that
verifies the server, the issuer, the broker, and the Registry, KSC-10), and the
optional `OTEL_*` block for OTLP export.

The broker auth ladder (KSC-10, DD-471) rides four more keys. The settings
validator refuses a half-filled ladder, so a mis-set run fails at start instead
of silently speaking the wrong protocol:

| Key                                                  | Meaning                                                                                                                          |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `SECURITY_PROTOCOL`                                  | `PLAINTEXT` (default), `SSL`, `SASL_PLAINTEXT`, or `SASL_SSL` — what the broker's listener answers                               |
| `SASL_MECHANISM`                                     | with a SASL protocol: `PLAIN`, `SCRAM-SHA-256`, `SCRAM-SHA-512`, or `OAUTHBEARER`                                                |
| `SASL_USERNAME`/`_PASSWORD`                          | the principal and secret for `PLAIN` and the `SCRAM-*` mechanisms                                                                |
| `SASL_OAUTH_TOKEN_URL`/`_CLIENT_ID`/`_CLIENT_SECRET` | the issuer trio for `OAUTHBEARER`: the job mints the broker token with the same client-credentials source the catalogue legs use |

## Run in dev

```bash
npx nx scan aurelius-atlas-kafka-scanner   # dev Keycloak, server, and [dev/kafka](../../dev/kafka/README.md) must be up
npx nx test aurelius-atlas-kafka-scanner -c ci
npx nx e2e aurelius-atlas-kafka-scanner    # the scanner in-process against a real server image
```

The job has no port and no liveness endpoint: it runs to completion and exits,
so the image carries no healthcheck. In production a scheduler starts it (the
Helm CronJob lands with 13.2).
