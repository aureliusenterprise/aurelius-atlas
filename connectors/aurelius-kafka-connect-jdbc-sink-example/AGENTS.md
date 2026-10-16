# aurelius-kafka-connect-jdbc-sink-example

Standalone Kafka Connect JDBC sink deployment. This file covers wiring specific
to this project; workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — single `connect-standalone.sh` worker
- `workers/worker.properties` — worker config, `${env:VAR}` values via
  `EnvVarConfigProvider`
- `workers/connector.properties` — the sink connector definition
- `Dockerfile` — cp-kafka-connect base + Avro converter + Debezium JDBC sink
    - Debezium OpenLineage integration jars (see the `ol_libs` block)
- `openlineage.yaml` — static pipeline/edge registration
  (`nx openlineage-register aurelius-kafka-connect-jdbc-sink-example`)
- `.env` / `.env.enc` — SOPS-encrypted dev settings

## Wiring Checklist

- `project.json` `implicitDependencies`: `aurelius-dev-kafka`,
  `aurelius-dev-postgres`, `aurelius-example`, `aurelius-kafka`.
- Compose joins the external networks `aurelius-dev-kafka-network` and
  `aurelius-dev-postgres-network` — both must be up (`nx up aurelius-dev-kafka
aurelius-dev-postgres`) before `nx serve` here works.
- Compose also joins `aurelius-dev-keycloak-network` so the worker can reach
  the OAuth token endpoint (`keycloak.localhost` is a network alias there).
  The JVM needs `-Dorg.apache.kafka.sasl.oauthbearer.allowed.urls` with the
  exact token URL (`JAVA_TOOL_OPTIONS` in compose) — Kafka 4.x requirement.
  The SASL/OAUTHBEARER settings live in `workers/worker.properties` for all
  three client tiers (worker, `consumer.`, `producer.`).
- The connector writes Avro `Entity` records from `example.entity` into the dev
  Postgres with `insert.mode=upsert` on `guid`; transforms
  (`HoistField$Key`, `Flatten$Value`) assume the current `Entity` field set —
  update them when `libs/python/aurelius-example` changes.
- Failures go to the `example.entity-dlq` dead-letter topic.
    - Timestamp fields must arrive as Avro `timestamp-millis`: the Confluent
      converter maps only that logicalType to a Connect `Timestamp`, and the
      Debezium 3.7 JDBC sink binds anything else (raw `INT64`) as bigint, which
      Postgres rejects for the `timestamptz` column. After changing the schema,
      purge stale backlog records with `kafka-delete-records.sh` (offset -1) or
      the task re-fails on old rows until the DLQ absorbs them.
- REST API on port 8083 is part of the local contract.
- Native OpenLineage integration (`openlineage.integration.*` in
  `connector.properties`): the compose entrypoint renders the transport YAML
  to `/tmp/openlineage.yml` (worker runs as non-root, cannot write elsewhere)
  with the Kafka/OAuth/SSL settings from `.env`. The plugin dir must NOT ship
  jackson-databind/core — the Connect parent loader provides them and a split
  breaks `ObjectMapper.findModules()`; only `jackson-datatype-jsr310` (the
  parent's version) belongs there.
- Lineage stitching contract with OpenMetadata: `job.namespace` +
  `openlineage.yaml` pipeline name must stay
  `aurelius-openlineage` / `aurelius-openlineage-{connectorName}.{taskId}`.
- `openmetadata.yaml` adds a native `kafkaconnect` scan of the worker REST
  API (port 8083) — **discovery only** (`includeLineage: false`): the API
  reports the unresolved `${env:VAR}` placeholders from the
  EnvVarConfigProvider, and the connector's sink-lineage heuristic only
  links a table when its base name equals the topic name. Do not enable
  `includeLineage` without re-checking both against the running worker.
  The `openlineage.yaml` static edges stay this sink's lineage source, and
  the scan's pipeline (`aurelius-kafka-connect/<connectorName>`) is a
  separate operational-view object next to the OL-event pipeline — by
  design, not a duplicate.

## Commands

```bash
nx serve aurelius-kafka-connect-jdbc-sink-example
curl localhost:8083/connectors   # verify the sink is registered
```

## Conventions

- Config changes belong in the `workers/*.properties` files (with `${env:VAR}`
  for anything secret), not in compose `environment:` blocks beyond the
  injections those files reference.
- Converter/plugin versions in the `Dockerfile` must match the dev Kafka
  cluster's Schema Registry version line.

## Removal

Part of the Kafka streaming slice. Removing it is self-contained (its own
compose + image); also drop it from any docs referencing the streaming flow.
