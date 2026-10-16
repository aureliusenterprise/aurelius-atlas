# aurelius-dev-kafka

Local development Kafka cluster. This file covers wiring specific to this
project; workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `docker-compose.yaml` — broker (KRaft), Schema Registry, Kafka UI
- Broker config lives in `docker-compose.yaml` as `KAFKA_*` environment variables
  (RF 1, 3 partitions); the image entrypoint writes them into its own
  `server.properties` in the container layer — no config file is bind-mounted
- `config/metrics-puller.yaml` — OTel Collector config for the
  `metrics-puller` sidecar: broker metrics pushed to dev/observability
  (see Wiring Checklist)
- `.env` / `.env.enc` — SOPS-encrypted dev settings

## Wiring Checklist

- Part of the Kafka streaming slice (see root `AGENTS.md` module map).
- Exposes the external Docker network `aurelius-dev-kafka-network`; the Java
  producer, Node-RED, JDBC sink connector, Lambda E2E, and governance's
  OpenLineage ingestion loop (plus its topic-init) attach to it and
  reach the broker at `broker:9094` (host apps use `localhost:9092`).
- Those projects order against this one in their `project.json` — either
  `implicitDependencies: ["aurelius-dev-kafka"]` (the inferred `serve`/`up`
  then chain via `^serve`/`^up`; governance and the e2e suites do this) or a
  direct `dependsOn` on this project's `serve`/`up` target. New Kafka
  consumers/producers should do the same.
- Schema Registry uses `RecordNameStrategy`; subject names follow
  `example.entity` from `Entity.avsc`'s namespace.
- `implicitDependencies: ["aurelius-dev-keycloak"]` — the OAUTHBEARER listeners
  validate JWTs against the `kafka` realm there; Keycloak must import
  `dev/keycloak/import/kafka.json` before the broker's OAuth path works.
- OAuth listeners: `SECURE` (`broker:9095`, in-network) and `SECUREHOST`
  (`localhost:9096`, host/devcontainer). Both are SASL_SSL + OAUTHBEARER
  with `aud=kafka`; they are certificate-optional (machine identity = the
  JWT). `INTERNAL` (`broker:9094`) and `PUBLIC` (`localhost:9092`) enforce
  mTLS (`KAFKA_LISTENER_NAME_INTERNAL_SSL_CLIENT_AUTH` and
  `KAFKA_LISTENER_NAME_PUBLIC_SSL_CLIENT_AUTH`, both `required`) for the
  clients without OAuth support: Schema Registry kafkastore
  (`schema-registry.p12`), the broker healthcheck (`broker.p12`), Kafka UI
  (`kafka-ui.p12`), and Node-RED (`node-red.pem` from its own project's
  certgen — its Kafka module can do kafkajs TLS client certs but no
  OAuth). Exception clients therefore need a keystore/cert from
  `tls.json`: adding a new consumer of these listeners means adding its
  service there.
  The KRaft `CONTROLLER` listener likewise sets
  `KAFKA_LISTENER_NAME_CONTROLLER_SSL_CLIENT_AUTH=required` — no anonymous
  peer joins the quorum; the controller plane authenticates with the same
  broker keystore (`broker.p12`).
- Broker metrics are collected by the **`metrics-puller`** service — a
  slice-owned OTel Collector (same pattern as dev/governance and
  dev/postgres) whose `kafka_metrics` receiver reads topics/partitions/
  offsets/consumer-groups over the Kafka protocol and pushes OTLP to the dev
  collector (external `aurelius-dev-observability-network` attach; Prometheus
  series carry `exported_job="dev-kafka"`). It is the zero-footprint option:
  the broker otherwise exposes metrics only via JMX, and a Prometheus JMX
  exporter would add a third-party jar to the hardened image. As an
  `INTERNAL`-listener client it needs a certificate: the `metrics-puller`
  entry in `tls.json` (see the exception-clients note above). Long-running by
  rule (see Conventions), and it presents no consumer-visible port.
- Gotchas (verified):
    - Kafka 4.x fails fast if the JWKS endpoint is set without
      `KAFKA_SASL_OAUTHBEARER_EXPECTED_ISSUER`/`_AUDIENCE`.
    - The broker's JWKS/token HTTPS calls to Keycloak use the JVM default
      trust (not `ssl.truststore.*`) → `JAVA_TOOL_OPTIONS` truststore +
      `org.apache.kafka.sasl.oauthbearer.allowed.urls` (exact URLs, comma-
      separated) — required in every JVM doing OAuth, clients included.
    - Re-importing the `kafka` realm rotates its signing keys; Keycloak does
      NOT overwrite an existing realm (delete it via the admin API first), and
      the broker caches JWKS — restart the broker after a realm re-import or
      tokens fail with `invalid_token` (UnresolvableKeyException).
    - `keycloak.localhost` resolves in-network via the network **alias** on the
      Keycloak service (`dev/keycloak` compose); OAuth client composes join the
      external `aurelius-dev-keycloak-network` instead of using `extra_hosts`
      (`host-gateway` maps to `docker0`, which is link-down in the dev
      container → intermittent "Failed to connect").
    - **librdkafka cannot use a `.localhost` token URL in-container**: its
      c-ares resolver short-circuits every `*.localhost` name to loopback
      (RFC 6761), ignoring Docker DNS and even `/etc/hosts`. Python (librdkafka)
      clients must set the token endpoint to `https://keycloak:8443/...` (plain
      service name) in their e2e compose — Keycloak's `KC_HOSTNAME` pins the
      token `iss` to `keycloak.localhost` regardless, so the broker still
      accepts it. JVM clients (JVM resolver) keep `keycloak.localhost`.
    - Client certificates need the `clientAuth` extended key usage: `mkcert`
      issues `serverAuth`-only leaves, and a peer enforcing
      `ssl.client.auth=required` rejects them with "Extended key usage does not
      permit use for TLS client authentication". `tools/tls/certgen.sh`
      therefore issues leaves itself (`issue_leaf`, signed by the same mkcert
      root) with both usages — do not switch it back to plain `mkcert` calls.
      Kafka UI's client keystore goes through
      `KAFKA_CLUSTERS_0_PROPERTIES_SSL_KEYSTORE_*` (its cluster-level `ssl`
      config is truststore-only).

## Commands

```bash
nx serve aurelius-dev-kafka   # compose up (foreground)
nx up aurelius-dev-kafka      # detached, waits for healthy
nx decrypt aurelius-dev-kafka # SOPS: .env.enc → .env (serve does this for you)
```

## Conventions

- Change broker behaviour via the `KAFKA_*` variables in `docker-compose.yaml` —
  that IS the broker config now; there is no properties file. Never set them in
  a bind-mounted file: the entrypoint cannot write bind mounts as uid 65532.
- Ports 9092/8081/8082 are part of the workspace contract (apps' `.env` files
  point at them) — coordinate before changing.
- Keep every service long-running: the e2e fixtures start this stack through
  testcontainers, which runs `docker compose up --wait` — and `--wait` treats
  _any_ container exiting during the wait as a failed deployment (even
  exit 0), so a one-shot here breaks every Kafka consumer's e2e (a removed
  `topic-init` did). Topic provisioning belongs to the consuming stacks
  (governance pre-creates `openlineage-events`; e2e suites create their own
  app topics).

## Removal

Removing this project means removing the whole Kafka streaming slice per the
root `AGENTS.md` module map (java-producer, node-red, aurelius-kafka,
aurelius-java-example, the JDBC sink connector, and the Lambda slice's Kafka
event source).
