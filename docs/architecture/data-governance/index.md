# Data Governance Stack

The data governance stack provides data lineage tracking and visualization using OpenMetadata and OpenLineage.

## Architecture

```plaintext
Java Producer (OpenLineage event) → Kafka → Debezium JDBC Sink (OpenLineage event) → Postgres
                                                              ↓
                                                    OpenMetadata (lineage graph)
```

## Components

| Component     | Version   | Purpose                                |
| ------------- | --------- | -------------------------------------- |
| OpenMetadata  | 2.0.4     | Data catalog and lineage visualization |
| OpenLineage   | 1.47.1    | Data lineage standard                  |
| Elasticsearch | 9.5 (DHI) | Search and indexing                    |
| PostgreSQL    | 18 (DHI)  | OpenMetadata metadata storage          |
| Keycloak      | latest    | Authentication (OIDC)                  |

The OpenMetadata server, Elasticsearch, and PostgreSQL run on Docker Hardened
Images (`dhi.io/openmetadata`, `dhi.io/elasticsearch`, `dhi.io/postgres`) and
are configured for TLS-only communication with the server; the server image is
built from the hardened `dhi.io/openmetadata` base with the OpenTelemetry Java
agent added (its `Dockerfile`), since OpenMetadata exposes no metrics endpoint
Prometheus can scrape; ingestion uses the upstream `openmetadata/ingestion`
image (no hardened variant is published).
Elasticsearch and the metadata Postgres are monitored by a governance-owned
metrics puller (an OpenTelemetry Collector sidecar in `dev/governance`) that
scrapes them locally and pushes OTLP to the dev observability stack — keeping
the scrape credentials inside the governance slice.
The version is pinned once — `OPENMETADATA_VERSION` in `dev/governance/.env.enc`
— and shared by the server, ingestion, and scan images; the ingestion client
refuses to talk to the server across major versions.

## Quick Start

### 1. Start Keycloak (if not already running)

```bash
docker compose -f dev/keycloak/docker-compose.yaml up -d
```

### 2. Start Governance Stack

```bash
npx nx up aurelius-dev-governance
```

### 3. Ingest metadata and register lineage

```bash
npx nx run aurelius-dev-governance:init-openmetadata   # scan Postgres, Kafka, ...
npx nx run aurelius-dev-governance:init-openlineage    # static pipeline/edge registration
npx nx run aurelius-dev-governance:ingest-openlineage  # live OpenLineage events (foreground loop)
```

### 4. Access OpenMetadata

Open `http://localhost:8585` and sign in through Keycloak (the OpenMetadata
realm client). The realm ships one user, `admin` (password `admin`); OM maps
its username from the token's email local-part (OM's default claim order),
so the realm user's `admin@aureliusenterprise.com` lands on the seeded
OpenMetadata admin (an admin principal) with full rights. Machine clients
(ingestion, lineage registration) authenticate the same way through the
`openmetadata-bot` service-account client: a short-lived Keycloak token
whose hardcoded `email=ingestion-bot@open-metadata.org` claim resolves to
the seeded ingestion bot — no API tokens are stored anywhere.
See `dev/governance/AGENTS.md`.

## Data Lineage

### Java Producer

The Java producer emits OpenLineage events for each message sent to Kafka:

```java
OpenLineage.RunEvent runEvent = openLineage
    .newBuilder()
    .runId(runId)
    .eventTime(eventTime)
    .eventType(OpenLineage.RunEventType.START)
    .job(openLineage.newJob("kafka-producer", topicName))
    .inputs(List.of(openLineage.newInputDataset("kafka://broker:9094", topicName, null, null)))
    .build();

openLineageClient.emit(runEvent);
```

### Debezium JDBC Sink

The Debezium JDBC sink connector runs the native Debezium OpenLineage
integration (Debezium >= 3.3.0; the plugin tarball bundles
`debezium-openlineage-core` + `openlineage-java`). The transport YAML — Kafka
topic, bootstrap servers, and SASL/SSL settings — is rendered at worker start
into `/tmp/openlineage.yml` (the connector runs as a non-root user), and
pipeline/edge registration is handled by the project-level `openlineage.yaml`:

```properties
# connector.properties
openlineage.integration.enabled=true
openlineage.integration.config.file.path=/tmp/openlineage.yml
openlineage.integration.job.namespace=aurelius-openlineage
openlineage.integration.job.description=Debezium JDBC sink for ${env:AURELIUS_CONNECTOR_TABLE_NAME}.
openlineage.integration.dataset.kafka.bootstrap.servers=localhost:9092
```

The `job.namespace` above and the pipeline name in `openlineage.yaml`
(`{jobNamespace}-{jobName}`, with Debezium's fixed `{connectorName}.{taskId}`
job name) are the stitching contract: live events from the connector merge
into the statically registered pipeline instead of creating a parallel one.

Project-level registration and ingestion config files:

- `dev/kafka/openmetadata.yaml`
- `dev/postgres/openmetadata.yaml`
- `dev/governance/integrations/openlineage.yaml`
- `connectors/aurelius-kafka-connect-jdbc-sink-example/openlineage.yaml`

Run project-level governance workflows through Nx:

```bash
npx nx run aurelius-dev-governance:init-openmetadata
npx nx run aurelius-dev-governance:init-openlineage
```

## Port Allocation

| Port      | Service                        | Notes                     |
| --------- | ------------------------------ | ------------------------- |
| 8585      | OpenMetadata server (API + UI) | Default, no conflict      |
| 8586      | OpenMetadata admin port        | Default, no conflict      |
| 9200      | Elasticsearch                  | No conflict               |
| 5433:5432 | PostgreSQL (metadata storage)  | Mapped to 5433 externally |

## Troubleshooting

### OpenMetadata not starting

Check the logs:

```bash
docker compose -f dev/governance/docker-compose.yaml logs openmetadata-server
```

### Service registration fails

Ensure Keycloak is running and the OpenMetadata realm is imported:

```bash
docker compose -f dev/keycloak/docker-compose.yaml up -d
```

### Lineage not appearing

1. Verify the Java producer is emitting OpenLineage events (check logs)
2. Verify the Debezium connector is configured correctly
3. Check the ingestion loop logs (`openmetadata_openlineage_ingestion`) for
   connection or auth errors

### Ingestion fails with 401

Machine clients authenticate with short-lived Keycloak tokens (see Quick
Start step 4). A 401 means Keycloak is not reachable or the `openmetadata-bot`
client secret in `dev/governance/.env` does not match
`CLIENT_SECRET_OPENMETADATA_BOT` in `dev/keycloak/.env` (both dev defaults
must be the same value). Check with `python3 tools/openmetadata/kc_token.py`
— it prints a fresh token or the Keycloak error.
