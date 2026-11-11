# aurelius-atlas-dev-kafka

Local development Kafka: one broker and a Schema Registry, for the Kafka
cluster scanner (increment 13.1). The scanner reads topics and schemas here
during development and end-to-end tests.

Part of the Kafka scanning track (13.1), with `apps/aurelius-atlas-kafka-scanner`.

## Services

| Service         | Image                                   | Host port                         |
| --------------- | --------------------------------------- | --------------------------------- |
| broker          | `dhi.io/kafka:4.3-debian13`             | `${KAFKA_BROKER_PORT}` (29092)    |
| schema-registry | `confluentinc/cp-schema-registry:8.2.1` | `${SCHEMA_REGISTRY_PORT}` (28081) |

- Single KRaft node (broker and controller in one process), no ZooKeeper
- PLAINTEXT on loopback by decision (DD-469): the host listener at
  `localhost:29092` answers anonymous clients, and the catalogue identity of
  the scanner carries authorization. A broker that demands machine identity
  gets its own decision with the prod chart.
- The in-network door is `broker:9092`; host tools use `localhost:29092`.
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
