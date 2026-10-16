# aurelius-java-producer-example

Example Java Kafka producer application. This file covers wiring specific to this
app; workspace-wide rules live in the root `AGENTS.md`.

## Layout

- `src/main/java/com/aureliusenterprise/producer/` — `App` (main loop + shutdown
  hook), `EntityProducer` (KafkaProducer wrapper), `AppConfig` (env-backed record)
- `src/test/java/` — JUnit 5 + Mockito
- `e2e/` — pytest suite against a real broker (runs via `uv`, not Gradle)
- Build config lives in `build.gradle.kts` — including the Nx target metadata
  (`nx { ... }` blocks) that registers `e2e` and `sonar` with the Nx graph

## Configuration

- `.env` in this directory is loaded into the `run` task's process environment by a
  hand-rolled loader in `build.gradle.kts` (comments and quotes supported). The
  loader additionally converts `AURELIUS_JAVA_PRODUCER_KAFKA_TRUSTSTORE_FILE`/`_PASSWORD` and
  `AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_TOKEN_ENDPOINT_URL` into `run`-task JVM system properties
  (`javax.net.ssl.trustStore*`, `org.apache.kafka.sasl.oauthbearer.allowed.urls`).
- All app settings use the `AURELIUS_JAVA_PRODUCER_` prefix (`AppConfig.ENV_PREFIX`)
  so other projects' injected env can never populate this app. Runtime keys:
  `AURELIUS_JAVA_PRODUCER_KAFKA_TOPIC_NAME`, `..._KAFKA_BOOTSTRAP_SERVERS`,
  `..._SCHEMA_REGISTRY_URL`, `..._MESSAGE_INTERVAL_MILLIS`, and the OAuth trio
  `..._KAFKA_OAUTH_TOKEN_ENDPOINT_URL`/`_CLIENT_ID`/`_CLIENT_SECRET` (all-or-none;
  when set, `App.buildProducerProperties` switches to SASL*SSL + OAUTHBEARER
  against the `kafka` realm — ADR 013). `TLS_TRUSTSTORE_PASSWORD` (shared compose
  interpolation) and the `KAFKA_E2E_OAUTH*\*` e2e-suite role stay bare by
  convention (third-party/shared names).

> [!WARNING]
> Never add `JAVA_TOOL_OPTIONS` to `.env`. Nx injects `.env` into **every** task's
> environment for this project, so a JVM-wide options string there leaks into
> unrelated JVMs (e.g. `sonar-scanner`, which then fails to load a relative
> `certs/truststore.p12` from the workspace root). The OAuth login's JVM
> properties belong in the `run` task's `systemProperty` wiring instead; the
> e2e/compose JVMs get their own (container-path) `JAVA_TOOL_OPTIONS` from
> `e2e/docker-compose.yaml`, which Nx never sees.

## Wiring Checklist

- `settings.gradle.kts` (root) — this module is `include`d there; renaming or
  moving it means updating that file.
- `build.gradle.kts` — `implementation(project(":aurelius-java-example"))` pulls
  in the generated Avro `Entity` class; Confluent artifacts need the
  `packages.confluent.io` repository.
- `gradle/libs.versions.toml` — add new dependencies to the version catalog, not
  inline.
- `kafka-clients` OAuth needs `jackson-databind` and `jose4j`, which are
  _optional_ in the kafka-clients POM — declared explicitly in
  `build.gradle.kts`; without jose4j the OAUTHBEARER login fails with
  `ClassNotFoundException: ...VerificationKeyResolver`.
- `Dockerfile` — the `e2e` target depends on `docker-build`; keep the image entry
  point in sync with `application.mainClass`.
- `nx { array("implicitDependencies", "aurelius-dev-kafka") }` — controls what
  `e2e`/`up` starts.

## Commands

```bash
nx run aurelius-java-producer-example:run       # produce messages (needs Kafka up)
./gradlew :aurelius-java-producer-example:test  # JUnit 5 + JaCoCo
nx e2e aurelius-java-producer-example           # pytest E2E
nx sonar aurelius-java-producer-example
```

Offline-safe: `./gradlew test`, `nx sonar`. Needs Docker: `run` (Kafka), `e2e`.

## Conventions

- The `Entity` class is generated — change `schemas/avro/` (and the Python model in
  `libs/python/aurelius-example`), then regenerate via
  `./gradlew :aurelius-java-example:generateAvro`.
- Avro serializer config must stay: `SERIALIZABLE_PACKAGES=com.aureliusenterprise.example`,
  header schema-id, `RecordNameStrategy` — consumers depend on it.
- Keep `AppConfig` as the only place reading environment variables.

## Removal

Part of the optional Kafka streaming slice. Removing this app also removes (or
makes dead): `libs/java/aurelius-java-example`, its `settings.gradle.kts` include,
the slice row in the root `AGENTS.md` module map, and `mkdocs.yaml` nav entries.
