# aurelius-atlas-dev-kafka

Local development Kafka for the Kafka cluster scanner (increment 13.1, rules
KSC-01 to KSC-10). This file covers wiring specific to this project;
workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — `broker` (KRaft single node) and `schema-registry`
- `.env` / `.env.enc` — SOPS-encrypted dev defaults (the two host ports)

## Wiring Checklist

- Exposes the Docker network `aurelius-atlas-dev-kafka-network`.
- `apps/aurelius-atlas-kafka-scanner` lists this project in its `e2e`
  dependsOn (`up`); its settings default to `localhost:29092` and
  `localhost:28081`, the two loopback publishes below.
- The realm client `aurelius-atlas-kafka-scanner` lives in
  `dev/keycloak/import/master.json` (and its helm mirror), not here. The
  broker itself holds no credentials (DD-469): its host listener is anonymous
  PLAINTEXT on purpose.
- `tests/test__dev_stack.py` lists `kafka` in `DEV_COMPOSES`: every publish
  must stay loopback-pinned (CHT-101).

## Broker notes (dhi.io/kafka)

- The image entrypoint writes every `KAFKA_*` environment variable into its
  own `server.properties` inside the container layer; there is no mounted
  config file.
- KRaft boot: `KAFKA_PROCESS_ROLES=broker,controller` with a `CONTROLLER`
  listener on 9093 and `KAFKA_CONTROLLER_QUORUM_VOTERS=1@broker:9093`. The
  cluster id comes from the image's storage-format step; the `kafka-kraft`
  volume keeps it stable across restarts.
- Two advertised listeners: `INTERNAL://broker:9092` (compose DNS) and
  `HOST://localhost:${KAFKA_BROKER_PORT}` (host tools). A consumer that
  bootstraps through the host publish learns the host address from metadata,
  so `localhost:29092` must stay the advertised host.
- Replication factors are 1 everywhere: a single node has no peer.

## Commands

```bash
nx serve aurelius-atlas-dev-kafka   # compose up (foreground)
nx up aurelius-atlas-dev-kafka      # detached, waits for healthy
docker compose -f dev/kafka/docker-compose.yaml down -v   # reset all data
```

## Conventions

- Keep it stateless for tests: e2e suites create their own topics with a
  run-unique prefix and delete them at the end (DD-223 — no suite restarts
  this stack; a rule that can only be proven by a restart stays untested by
  choice).
- `KAFKA_BROKER_PORT` (29092) and `SCHEMA_REGISTRY_PORT` (28081) are part of
  the workspace contract — coordinate before changing.

## Removal

Remove with `apps/aurelius-atlas-kafka-scanner` (see its `AGENTS.md` for the
full checklist).
