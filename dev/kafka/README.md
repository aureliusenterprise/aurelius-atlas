# aurelius-dev-kafka

Local development Kafka cluster: a KRaft-mode broker, Confluent Schema Registry,
and a browser-based Kafka UI, wired onto a shared Docker network for the other
Kafka-slice projects.

Part of the optional **Kafka streaming slice** — remove this project together
with the rest of that slice.

## Services

| Service         | Image                       | Host port | Notes                      |
| --------------- | --------------------------- | --------- | -------------------------- |
| Kafka broker    | `dhi.io/kafka:4.3-debian13` | 9092      | KRaft mode, no ZooKeeper   |
| Schema Registry | `cp-schema-registry:8.2.1`  | 8081      | Avro, `RecordNameStrategy` |
| Kafka UI        | `kafbat/kafka-ui:v1.5.0`    | 8082      | Browse topics, schemas     |

Inside the `aurelius-dev-kafka-network` Docker network, containers reach the broker
at `broker:9094` (host apps use `localhost:9092`; the controller runs on 9093).

The broker publishes several TLS listeners; the one a client uses depends on
where it runs and how it authenticates:

| Listener     | Address (from client) | Protocol   | Who uses it (client certificate presented)                                                                                  |
| ------------ | --------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------- |
| `SECURE`     | `broker:9095`         | SASL_SSL   | OAuth clients on the Docker network                                                                                         |
| `SECUREHOST` | `localhost:9096`      | SASL_SSL   | OAuth clients on the devcontainer/host                                                                                      |
| `INTERNAL`   | `broker:9094`         | SSL (mTLS) | SR kafkastore (`schema-registry.p12`), healthcheck (`broker.p12`), Kafka UI (`kafka-ui.p12`), Node-RED e2e (`node-red.pem`) |
| `PUBLIC`     | `localhost:9092`      | SSL (mTLS) | Host-path TLS-only clients: Node-RED serve / e2e test clients (`node-red.pem`)                                              |
| `CONTROLLER` | `localhost:9093`      | SSL        | KRaft controller plane (internal)                                                                                           |

Producers and consumers authenticate with OAuth (OAUTHBEARER): they fetch a JWT
from the dedicated `kafka` realm of the dev Keycloak
(`dev/keycloak`, issuer `https://keycloak.localhost:8443/realms/kafka`,
`aud=kafka`) and the broker validates it against the realm's JWKS endpoint.
Infrastructure clients that cannot speak OAuth (Schema Registry's kafkastore,
Kafka UI, Node-RED's Kafka module) stay on the `INTERNAL`/`PUBLIC` listeners,
which enforce real mTLS (`ssl.client.auth` required per listener): every such
client presents a certificate signed by the dev CA (`nx certgen`, `tls.json`).
Without a client certificate the handshake fails — no anonymous access. The
SASL listeners stay certificate-optional; machine identity there is the JWT.

## Configuration

- Broker configuration is passed as `KAFKA_*` environment variables in
  `docker-compose.yaml` (replication factor 1, 3 default partitions); the image
  entrypoint applies them to its own config inside the container. The PKCS12
  password comes from the project's encrypted dev default — never committed
- The compose project exposes the `aurelius-dev-kafka-network` network, which other
  projects (e.g. the JDBC sink connector) attach to from their own compose files
- OAuth clients (Keycloak client credentials per role) are defined in the
  `kafka` realm import of `aurelius-dev-keycloak`; this project
  `implicitDependencies` on it so Keycloak is up before the broker starts
- `JAVA_TOOL_OPTIONS` on the broker (and any Java OAuth client) must contain
  the Keycloak token/JWKS URLs in
  `org.apache.kafka.sasl.oauthbearer.allowed.urls` — Kafka 4.x blocks OAuth
  endpoint fetches unless each exact URL is allowlisted
- In-container OAuth clients reach Keycloak through the external
  `aurelius-dev-keycloak-network` (the service carries a `keycloak.localhost`
  network alias). Note: librdkafka (confluent-kafka) resolves every
  `*.localhost` name to loopback and ignores Docker DNS, so Python clients
  must point at `https://keycloak:8443/...` instead — see `AGENTS.md`.

## Running

```bash
nx serve aurelius-dev-kafka   # docker compose up (foreground)
nx up aurelius-dev-kafka      # detached, waits for healthy
```

Other projects (Java producer, Node-RED, Lambda E2E, JDBC sink) declare a
`dependsOn` on this project's `serve`/`up` target, so `nx serve` on them starts
Kafka automatically.
