# Scanning &amp; Discovery

OpenMetadata automatically scans our data sources to discover and catalog every data asset. This process — called **ingestion** — connects to each data source, reads its metadata, and registers it in the data catalog.

## What Gets Scanned

| Data Source | What's Discovered | Example |
| --- | --- | --- |
| **Kafka** | Topics, partitions, schemas | `example.entity` topic with Avro schema |
| **PostgreSQL** | Databases, schemas, tables, columns | `entity` table with column definitions |
| **REST APIs** | API endpoints, request/response schemas | `GET /entities` endpoint with JSON schema |
| **Kafka Connect** | Connectors, tasks, connector status | `aurelius-kafka-connect-jdbc-sink-example` sink |
| **Grafana** | Dashboards, panels (charts), data models | FastAPI observability dashboard |

## How It Works

The scanning process runs on a schedule and performs the following steps:

```
graph LR
    A["Data Source<br/>(Kafka, Postgres, API)"] -->|"1. Connect"| B[Ingestion Workflow]
    B -->|"2. Read metadata"| C["Schema, structure,<br/>and properties"]
    C -->|"3. Register in catalog"| D[OpenMetadata]
    D -->|"4. Available for<br/>search and lineage"| E[Data Catalog]
```

1. **Connect** — The ingestion workflow connects to a data source using configured credentials.
2. **Read metadata** — It reads structural information: table names, column types, topic schemas, API endpoints.
3. **Register** — Each discovered asset is registered in OpenMetadata as a catalog entry.
4. **Available** — The asset appears in the data catalog and can be searched, tagged, and linked to lineage edges.

## Schema Registry Integration for Kafka

When Kafka topics use Avro schemas, the scanner integrates with the Confluent Schema Registry to discover and register schema details.

### What the Schema Registry Provides

The Schema Registry stores the canonical version of every schema used to serialize and deserialize messages on Kafka topics. During scanning, OpenMetadata queries the Schema Registry to retrieve:

- **Schema definitions** — The full Avro schema for each topic, including field names, types, and nested structures.
- **Schema versions** — The evolution history of a schema, showing how the message format has changed over time.
- **Compatibility rules** — Whether schemas are backward-compatible, forward-compatible, or fully compatible.

### How Schema Discovery Works

```
graph LR
    A[Kafka Topic] -->|"1. Topic discovered"| B[Ingestion Workflow]
    B -->|"2. Look up schema"| C[Schema Registry]
    C -->|"3. Return Avro schema"| B
    B -->|"4. Register with schema"| D[OpenMetadata]
```

1. **Topic discovered** — The Kafka scanner finds a topic (e.g., `example.entity`).
2. **Schema lookup** — The scanner queries the Schema Registry for the topic's schema.
3. **Schema retrieved** — The Schema Registry returns the Avro schema definition.
4. **Registered** — OpenMetadata stores the schema with the topic entry, making it searchable and visible in the catalog.

### What Stakeholders See

With schema registry integration, each Kafka topic in the catalog includes:

- **Field-level details** — Every field in the Avro schema, with its type and documentation.
- **Schema evolution** — A history of schema changes, showing when fields were added, removed, or modified.
- **Compatibility status** — Whether the current schema is compatible with previous versions.

> [!TIP]
>
> **Why This Matters**
>
> Schema visibility helps stakeholders understand message formats without accessing the Kafka cluster directly. It also helps detect breaking schema changes before they cause consumer failures.

## What Stakeholders See

After scanning, every data asset appears in the OpenMetadata data catalog with:

- **Name and description** — What the asset is called and what it represents.
- **Schema details** — Column definitions for tables, message schemas for topics, request/response formats for APIs.
- **Lineage connections** — Upstream and downstream relationships (when defined through static edges or dynamic events).

## Scanning Coverage

Our platform currently scans the following data sources:

| Source | Service Name | Type |
| --- | --- | --- |
| Kafka cluster | `aurelius-dev-kafka` | Messaging (topics) |
| PostgreSQL database | `aurelius-dev-postgres` | Database (tables) |
| FastAPI application | `aurelius-fastapi-example-api` | REST API (endpoints) |
| Kafka Connect worker | `aurelius-kafka-connect` | Pipeline (connectors) |
| Grafana instance | `aurelius-observability` | Dashboard |

Each source is configured with filters to include only relevant assets — for example, the Kafka scanner excludes internal topics (those starting with `_`), and the database scanner excludes system schemas.

### Sources Without a Native Scan Path

Some platform components have no OpenMetadata connector and are catalogued through other means — recorded here so the gap reads as a decision:

| Component | Why there is no scan |
| --- | --- |
| Schema Registry | No standalone connector; covered through the Kafka scanner |
| Keycloak, kafka-ui | Infrastructure, not data assets |
| AWS Lambda application | No Lambda service type in OpenMetadata |
| Node-RED flow | No connector; catalogued with static edges |
| Frontend application | SPAs have no catalog entity type; static pipeline only |

Two connectors are adopted for **metadata only**, not lineage:

- **Kafka Connect** — the worker REST API exposes the connector's `${env:VAR}` configuration placeholders rather than resolved values, and the sink-lineage heuristic requires the table name to match the topic name. Connector discovery/status lands; the sink's lineage stays with the OpenLineage events (see [Dynamic Events](<https://aureliusenterprise.github.io/main/architecture/data-governance/data-lineage/lineage-dynamic-events/index.md>)).
- **Grafana** — dashboards and charts are catalogued; panel queries target Prometheus/Loki/Tempo, which have no catalog entities to link to.

## Keeping the Catalog Current

Scanning runs periodically to pick up changes:

- **New tables or topics** — Automatically discovered on the next scan.
- **Schema changes** — Column additions, type changes, or new API endpoints are reflected in the catalog.
- **Deleted assets** — Marked as deprecated or removed from the catalog.

> [!NOTE]
>
> **How often does scanning run?**
>
> Scanning is triggered through Nx workflow targets. In production, these workflows run on a schedule. During development, they can be run manually to refresh the catalog.

## Benefits for Stakeholders

- **Single source of truth** — One place to find all data assets across the organization.
- **Searchable inventory** — Find any table, topic, or API by name or tag.
- **Schema visibility** — Understand the structure of data without accessing the source directly.
- **Foundation for lineage** — Scanned assets become the nodes in the lineage graph.
