# Using the Lineage Graph

The OpenMetadata lineage graph brings together all three lineage mechanisms — scanning, static edges, and dynamic events — into a single visual interface. This page explains how to use it.

## Accessing the Lineage Graph

Open the OpenMetadata interface at `http://localhost:8585` and log in. From the home page, you can:

- **Search for any data asset** — Use the search bar to find tables, topics, APIs, or pipelines by name.
- **Browse by category** — Navigate through databases, messaging systems, APIs, and pipelines.
- **View lineage for any asset** — Click on any asset to see its upstream and downstream connections.

## Understanding the Graph

The lineage graph shows data assets as nodes and data flows as directed edges (arrows). Reading the graph is straightforward:

```
graph LR
    A[(Database<br/>Table)] -->|"data flows to"| B[API<br/>Endpoint]
    C[Kafka<br/>Topic] -->|"data flows to"| A
```

- **Arrows point in the direction of data flow** — From source to destination.
- **Upstream** — Assets to the left (where data comes from).
- **Downstream** — Assets to the right (where data goes).
- **Node types** — Different shapes and colors represent tables, topics, APIs, and pipelines.

## Common Use Cases

### Change Impact Analysis

Before modifying a database table or API, check the lineage graph to understand what will be affected:

1. Find the asset you plan to change (e.g., the `entity` table).
2. Look at **downstream connections** — these are the systems that depend on this data.
3. Assess the impact — if the `entity` table feeds three API endpoints, changing its schema will affect all three.

> [!TIP]
>
> **Practical Example**
>
> You need to rename a column in the `entity` table. The lineage graph shows that this table feeds: - `GET /entities` — list endpoint - `GET /entities/{guid}` — detail endpoint - `PUT /entities` — update endpoint - JDBC Sink Connector — writes to this table from Kafka
>
> You now know to coordinate the change with the teams owning these endpoints and the connector configuration.

### Root-Cause Analysis

When data quality issues appear, trace them back to the source:

1. Find the asset with the problem (e.g., an API returning incorrect data).
2. Look at **upstream connections** — these are the sources of the data.
3. Follow the chain upstream until you find where the issue originated.

> [!TIP]
>
> **Practical Example**
>
> The `/entities/get` endpoint is returning stale data. The lineage graph shows: - The endpoint reads from the `entity` table - The `entity` table is populated by the JDBC Sink Connector - The connector reads from the `example.entity` Kafka topic - The topic is produced by the Java Producer
>
> Checking the Java Producer's dynamic events, you find it emitted a `FAIL` event two hours ago — the producer stopped sending data, so the table has stale records.

### Data Inventory and Discovery

New team members or stakeholders can use the lineage graph to understand the data landscape:

1. Browse the data catalog to see all registered assets.
2. Click on any asset to see its lineage — what feeds it and what it feeds.
3. Use the graph to understand how different systems are connected.

### Compliance and Auditing

For regulatory reviews, the lineage graph provides evidence of data handling:

- **Data provenance** — Where did sensitive data originate?
- **Data movement** — Through which systems did it pass?
- **Data consumption** — Which applications access it?
- **Processing history** — When did pipelines run and did they succeed?

## Navigating the Graph

The lineage graph supports interactive exploration:

- **Expand upstream** — Click to trace data back to its origin.
- **Expand downstream** — Click to see all consumers of a data asset.
- **Filter by type** — Show only tables, only topics, or only APIs.
- **Search within the graph** — Find a specific asset in the lineage view.

## Interpreting Runtime Information

When dynamic events are available, the lineage graph shows additional information:

| Indicator | Meaning |
| --- | --- |
| **Green node** | Pipeline is running or last completed successfully |
| **Red node** | Pipeline has failed recently |
| **Record count** | Number of records processed in the last run |
| **Last run time** | When the pipeline last executed |

## Tips for Effective Use

- **Start with the asset you care about** — Don't try to understand the entire graph at once. Focus on one table, topic, or API and expand from there.
- **Check both directions** — Always look upstream (where data comes from) and downstream (where it goes) for a complete picture.
- **Combine static and dynamic views** — Static edges show the planned data flow; dynamic events show what's actually happening. Discrepancies between the two can indicate configuration issues.
- **Use search effectively** — The data catalog search is the fastest way to find a specific asset by name.
