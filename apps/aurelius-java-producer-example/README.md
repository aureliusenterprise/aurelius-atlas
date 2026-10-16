# aurelius-java-producer-example

Example Java 21 console application demonstrating the Aurelius Kafka producer
pattern: it publishes Avro-serialised `Entity` records to a Kafka topic on a fixed
interval, using Confluent's Schema Registry.

Part of the optional **Kafka streaming slice** — remove this project together
with the rest of that slice.

## How it works

- `App.java` — main loop: load config, produce a record every
  `AURELIUS_JAVA_PRODUCER_MESSAGE_INTERVAL_MILLIS`, shut down cleanly via a shutdown hook.
- `EntityProducer` — wraps `KafkaProducer<String, Entity>` with a
  `KafkaAvroSerializer` (header schema-id framing, `RecordNameStrategy` naming).
- `AppConfig` — a record populated from environment variables, with a small `.env`
  file loader used by the `run` target.
- The `Entity` Java class is **generated** by the sibling `aurelius-java-example`
  library from the Avro schemas in `schemas/avro/` — never edit it by hand.

## Configuration

Every setting is read from the environment with the `AURELIUS_JAVA_PRODUCER_`
prefix (`AppConfig.ENV_PREFIX`), so other projects' environment variables can
never populate this app by accident.

| Variable                                                | Default                          | Purpose                                              |
| ------------------------------------------------------- | -------------------------------- | ---------------------------------------------------- |
| `AURELIUS_JAVA_PRODUCER_KAFKA_TOPIC_NAME`               | `example.entity`                 | Target topic                                         |
| `AURELIUS_JAVA_PRODUCER_KAFKA_BOOTSTRAP_SERVERS`        | `localhost:9096`                 | Broker address (OAuth listener)                      |
| `AURELIUS_JAVA_PRODUCER_SCHEMA_REGISTRY_URL`            | `https://localhost:8081`         | Schema Registry                                      |
| `AURELIUS_JAVA_PRODUCER_MESSAGE_INTERVAL_MILLIS`        | `10000`                          | Delay between messages                               |
| `AURELIUS_JAVA_PRODUCER_KAFKA_TRUSTSTORE_FILE`          | `certs/truststore.p12`           | PKCS12 truststore (enables TLS when set)             |
| `AURELIUS_JAVA_PRODUCER_KAFKA_TRUSTSTORE_PASSWORD`      | (encrypted in `.env.enc`)        | Truststore password (required with file)             |
| `AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_TOKEN_ENDPOINT_URL` | Keycloak `kafka` realm token URL | When set, the producer uses SASL_SSL + OAUTHBEARER   |
| `AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_CLIENT_ID`          | `kafka-producer`                 | Keycloak client (required with the token URL)        |
| `AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_CLIENT_SECRET`      | (encrypted in `.env.enc`)        | Keycloak client secret (required with the token URL) |

Kafka and Schema Registry connections use TLS verified against the local
development CA (`nx certgen` generates this project's `certs/`). When the
`AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_*` variables are set, the producer
authenticates to the broker
with an OAuth bearer token from the `kafka` realm (ADR 013) instead of mTLS.
The OAuth login also needs JVM-wide properties (the JSSE truststore for the
Keycloak TLS connection and, on Kafka 4.x, the token URL in
`org.apache.kafka.sasl.oauthbearer.allowed.urls`). The Gradle `run` task derives
them from `AURELIUS_JAVA_PRODUCER_KAFKA_TRUSTSTORE_*` and
`AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_TOKEN_ENDPOINT_URL` as JVM system
properties — they are deliberately _not_ set via `JAVA_TOOL_OPTIONS` in `.env`,
because Nx injects `.env` into every task's environment and JVM-wide options
there would leak into unrelated tools.

## Running

```bash
nx serve aurelius-dev-kafka        # start broker + Schema Registry first
nx run aurelius-java-producer-example:run
```

Confluent artifacts come from the Confluent Maven repository declared in
`build.gradle.kts`.

## Testing

```bash
./gradlew :aurelius-java-producer-example:test   # JUnit 5 + JaCoCo coverage
nx e2e aurelius-java-producer-example            # pytest E2E against a real broker
```
