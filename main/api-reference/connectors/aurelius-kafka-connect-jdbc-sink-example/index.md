# aurelius-kafka-connect-jdbc-sink-example

This is an example Kafka Connect JDBC Sink application.

## Workflow

```
graph LR
    subgraph A["Kafka"]
        a[("example.entity")]
    end

    subgraph B["Connector"]
        b["JDBC Sink"]
    end

    subgraph C["Postgres"]
        c[("Entity")]
    end

    subgraph D["Kafka"]
        d[("example.entity-dlq")]
    end

    a -->|"Messages"| b
    b -->|"Records"| c
    b -->|"Errors"| d
```

The connector reads messages from the `example.entity` Kafka topic, processes each message, and writes the resulting data to the `Entity` table in Postgres.

> [!NOTE]
>
> **What happens if the database is unavailable?**
>
> If the database is unavailable, the connector will retry processing the messages at a later time.

> [!NOTE]
>
> **What happens if processing fails?**
>
> If processing fails, the connector forwards the problematic message to the dead-letter queue topic `example.entity-dlq`.

## Key Schema

Keys should be string representations of the entity's `guid` field.

## Value Schema

Values are expected to be Avro-encoded records that conform to the `Entity` schema.

> [!NOTE]
>
> **Entity Schema**
>
> ## aurelius\_example.models.Entity
>
> Bases: `AvroBase`, `SQLModel`
>
> A model that represents an simple entity that can be serialized to Avro and stored in a SQL database.
>
> **Show JSON schema:**
>
> ```
> {
>   "description": "A model that represents an simple entity that can be serialized to Avro and stored in a SQL database.",
>   "properties": {
>     "description": {
>       "anyOf": [
>         {
>           "maxLength": 255,
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "description": "A description of the entity",
>       "title": "Description"
>     },
>     "guid": {
>       "description": "The unique identifier for the entity",
>       "format": "uuid",
>       "title": "Guid",
>       "type": "string"
>     },
>     "name": {
>       "anyOf": [
>         {
>           "maxLength": 100,
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "description": "The name of the entity",
>       "title": "Name"
>     },
>     "time_created": {
>       "anyOf": [
>         {
>           "format": "date-time",
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "description": "The timestamp when the entity was created with timezone info",
>       "title": "Time Created"
>     },
>     "time_modified": {
>       "anyOf": [
>         {
>           "format": "date-time",
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "description": "The timestamp when the entity was last modified with timezone info",
>       "title": "Time Modified"
>     }
>   },
>   "title": "Entity",
>   "type": "object"
> }
> ```
>
> Fields:
>
> - `description` (`str | None`)
> - `guid` (`UUID`)
> - `name` (`str | None`)
> - `time_created` (`datetime | None`)
> - `time_modified` (`datetime | None`)
>
> ### \_\_mapper\_args\_\_
>
> ```
> __mapper_args__ = {'confirm_deleted_rows': False}
> ```
>
> ### description
>
> ```
> description: str | None = None
> ```
>
> A description of the entity
>
> ### guid
>
> ```
> guid: UUID
> ```
>
> The unique identifier for the entity
>
> ### name
>
> ```
> name: str | None = None
> ```
>
> The name of the entity
>
> ### time\_created
>
> ```
> time_created: datetime | None = None
> ```
>
> The timestamp when the entity was created with timezone info
>
> ### time\_modified
>
> ```
> time_modified: datetime | None = None
> ```
>
> The timestamp when the entity was last modified with timezone info
>
> ### \_\_lt\_\_
>
> ```
> __lt__(other: Entity) -> bool
> ```
>
> Compare entities based on their latest change timestamp.
>
> ### avro\_schema
>
> ```
> avro_schema(*args: Any, **kwargs: Any) -> dict[str, Any]
> ```
>
> Return the Avro schema with datetime fields encoded as timestamp-millis.
>
> pydantic-avro defaults `date-time` fields to `timestamp-micros`, but the Confluent Avro converter maps only `timestamp-millis` to the Connect `Timestamp` logical type. Without it, consumers that read through that converter (e.g. the Debezium JDBC sink) see a nameless raw `INT64` and try to bind it to a `timestamptz` column as a bigint, which fails.

The schema is registered in the schema registry as `com.aureliusenterprise.example.Entity`.

## Tombstone Messages

The connector also supports tombstone messages, which are used to delete records from the database. Tombstone messages should have a key that matches the entity's `guid` field and a value that is `null`.

## Configuration

This example runs Kafka Connect in standalone mode and uses two properties files:

- `workers/worker.properties` for worker runtime settings
- `workers/connector.properties` for this JDBC sink connector instance

### Standalone startup in Docker Compose

Set the service entrypoint to `connect-standalone.sh` and pass the worker file first, then the connector file:

```
services:
    kafka-connect:
        image: ghcr.io/aureliusenterprise/aurelius-kafka-connect-jdbc-sink-example:local
        entrypoint: ["/opt/kafka/bin/connect-standalone.sh"]
        command: ["/connect-worker", "/connect-connector"]
        configs:
            - connect-worker
            - connect-connector

configs:
    connect-worker:
        file: ./workers/worker.properties
    connect-connector:
        file: ./workers/connector.properties
```

### Worker configuration environment variables

These environment variables are referenced by `workers/worker.properties`:

All app settings carry the `AURELIUS_CONNECTOR_` prefix, so other projects' environment variables can never populate this app.

| Name | Description |
| --- | --- |
| `AURELIUS_CONNECTOR_KAFKA_BOOTSTRAP_SERVERS` | Kafka bootstrap servers. |
| `AURELIUS_CONNECTOR_CONFIG_STORAGE_TOPIC` | Connect config storage topic name. |
| `AURELIUS_CONNECTOR_GROUP_ID` | Connect worker group ID. |
| `AURELIUS_CONNECTOR_OFFSET_STORAGE_TOPIC` | Connect offset storage topic name. |
| `AURELIUS_CONNECTOR_STATUS_STORAGE_TOPIC` | Connect status storage topic name. |
| `AURELIUS_CONNECTOR_REST_ADVERTISED_HOST_NAME` | Hostname advertised by the Connect REST API. |
| `AURELIUS_CONNECTOR_REST_PORT` | Connect REST API port. |
| `AURELIUS_CONNECTOR_SCHEMA_REGISTRY_URL` | Schema Registry URL used by the Avro value converter. |

`worker.properties` also sets `offset.storage.file.filename`, which is required for standalone mode.

### Connector configuration environment variables

These environment variables are referenced by `workers/connector.properties`:

| Name | Description |
| --- | --- |
| `AURELIUS_CONNECTOR_DATABASE_URL` | JDBC URL for the target Postgres database. |
| `AURELIUS_CONNECTOR_DATABASE_USERNAME` | Database username. |
| `AURELIUS_CONNECTOR_DATABASE_PASSWORD` | Database password. |
| `AURELIUS_CONNECTOR_KAFKA_TOPIC_NAME` | Source topic consumed by the sink connector. |
| `AURELIUS_CONNECTOR_DLQ_TOPIC_NAME` | Dead-letter queue topic for records that fail processing. |
| `AURELIUS_CONNECTOR_TABLE_NAME` | Destination table name used by the JDBC sink connector. |
