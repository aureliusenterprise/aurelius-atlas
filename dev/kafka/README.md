# aurelius-atlas-dev-kafka

Local development Kafka: one broker and a Schema Registry, for the Kafka
cluster scanner (increment 13.1). The scanner reads topics and schemas here
during development and end-to-end tests. The broker answers two kinds of
client: anonymous on the plain listener, and SCRAM-authenticated on the SASL
one — the dev stand-in for the authenticated clusters a scan meets in the
field (DD-471).

Part of the Kafka scanning track (13.1), with `apps/aurelius-atlas-kafka-scanner`.

## Services

| Service         | Image                                   | Host port                         |
| --------------- | --------------------------------------- | --------------------------------- |
| broker          | `dhi.io/kafka:4.3-debian13`             | `${KAFKA_BROKER_PORT}` (29092)    |
| broker (SASL)   | `dhi.io/kafka:4.3-debian13`             | `${KAFKA_SASL_PORT}` (29095)      |
| schema-registry | `confluentinc/cp-schema-registry:8.2.1` | `${SCHEMA_REGISTRY_PORT}` (28081) |

- Single KRaft node (broker and controller in one process), no ZooKeeper
- The plain host listener at `localhost:29092` answers anonymous clients, and
  the catalogue identity of the scanner carries authorization (DD-469).
- The SASL host listener at `localhost:29095` speaks SASL_PLAINTEXT with
  SCRAM-SHA-512 (DD-471). The user `KAFKA_SASL_USER` is written into the
  cluster by the one-shot `sasl-init` service; the scanner's `.env` mirrors
  the pair so its e2e suite authenticates here too.
- The in-network door is `broker:9092`; host tools use `localhost:29092` or
  `localhost:29095`.
- The Registry speaks PLAINTEXT to the broker's internal listener and serves
  its REST API at `localhost:28081`.
- Attached to the `aurelius-atlas-dev-kafka-network` Docker network

## Running

```bash
nx serve aurelius-atlas-dev-kafka   # docker compose up (foreground)
nx up aurelius-atlas-dev-kafka      # detached, waits for healthy
```

```bash
# from dev/kafka, after nx up (which decrypts .env)
uv run python -c "from kafka import KafkaAdminClient; \
print(sorted(KafkaAdminClient(bootstrap_servers='localhost:29092').list_topics()))"
curl -s http://localhost:28081/subjects

# the SASL door, with the SCRAM user from .env
export KAFKA_SASL_USER=$(grep '^KAFKA_SASL_USER=' .env | cut -d= -f2)
export KAFKA_SASL_SECRET=$(grep '^KAFKA_SASL_SECRET=' .env | cut -d= -f2)
uv run python -c "import os; from kafka import KafkaAdminClient; \
print(sorted(KafkaAdminClient(bootstrap_servers='localhost:29095', \
security_protocol='SASL_PLAINTEXT', sasl_mechanism='SCRAM-SHA-512', \
sasl_plain_username=os.environ['KAFKA_SASL_USER'], \
sasl_plain_password=os.environ['KAFKA_SASL_SECRET']).list_topics()))"
```

!!! NOTE

    Data lives in the named volumes `kafka-data` and `kafka-kraft`. It
    survives restarts until you remove it with `docker compose down -v`.

## Removal

Delete `dev/kafka/`, the `kafka` entry in `DEV_COMPOSES` in
`tests/test__dev_stack.py`, the `aurelius-atlas-dev-kafka` service name in
`apps/aurelius-atlas-kafka-scanner/project.json` (`e2e` dependsOn), and the
`KAFKA_SCANNER_CLIENT_SECRET` lines in `dev/keycloak/` (the realm client
itself belongs to the scanner, 13.1).
