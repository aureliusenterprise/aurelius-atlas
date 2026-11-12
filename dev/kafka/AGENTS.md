# aurelius-atlas-dev-kafka

Local development Kafka for the Kafka cluster scanner (increment 13.1, rules
KSC-01 to KSC-10). This file covers wiring specific to this project;
workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — `broker` (KRaft single node), `schema-registry`, and
  the one-shot `sasl-init` (it writes the SCRAM user into the cluster and exits)
- `.env` / `.env.enc` — SOPS-encrypted dev defaults (the three host ports, the
  SCRAM user and its secret)

## Wiring Checklist

- Exposes the Docker network `aurelius-atlas-dev-kafka-network`.
- `apps/aurelius-atlas-kafka-scanner` lists this project in its `e2e`
  dependsOn (`up`); its settings default to `localhost:29092` and
  `localhost:28081`, the two loopback publishes below.
- The realm client `aurelius-atlas-kafka-scanner` lives in
  `dev/keycloak/import/master.json` (and its helm mirror), not here. The
  broker's plain host listener stays anonymous (the dev default scan needs no
  credential); its SASL listener carries the dev SCRAM user `sasl-init`
  creates (DD-471). The scanner's `.env` mirrors `KAFKA_SASL_USER`/`_SECRET`
  so its e2e suite signs in there — keep the two pairs equal when either
  changes, and re-encrypt both.
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
- Three advertised listeners: `INTERNAL://broker:9092` (compose DNS),
  `HOST://localhost:${KAFKA_BROKER_PORT}` (host tools, anonymous), and
  `SASL://localhost:${KAFKA_SASL_PORT}` (host tools that authenticate,
  SASL_PLAINTEXT with SCRAM-SHA-512). A consumer that bootstraps through a
  host publish learns the host address from metadata, so the `localhost`
  advertises must stay. The SASL listener's server-side login is the SCRAM
  handler (`listener.name.sasl.scram-sha-512.sasl.jaas.config`, spelled
  through the image's env mapping: `_` a dot, `___` a hyphen); its users live
  in the cluster metadata, so the login line itself carries no secret.
- `sasl-init` runs `kafka-configs.sh --alter --entity-type users` once the
  broker is healthy and exits 0; SCRAM users are metadata, so it is idempotent
  across recreates — a volume-wipe (`down -v`) calls for it again, which
  `up` does on its own.
- Replication factors are 1 everywhere: a single node has no peer.

## Commands

```bash
nx up aurelius-atlas-dev-kafka      # detached, waits for healthy
docker compose -f dev/kafka/docker-compose.yaml down -v   # reset all data
```

## Conventions

- Keep it stateless for tests: e2e suites create their own topics with a
  run-unique prefix and delete them at the end (DD-223 — no suite restarts
  this stack; a rule that can only be proven by a restart stays untested by
  choice).
- `KAFKA_BROKER_PORT` (29092), `KAFKA_SASL_PORT` (29095) and
  `SCHEMA_REGISTRY_PORT` (28081) are part of the workspace contract —
  coordinate before changing.

## Removal

Remove with `apps/aurelius-atlas-kafka-scanner` (see its `AGENTS.md` for the
full checklist).
