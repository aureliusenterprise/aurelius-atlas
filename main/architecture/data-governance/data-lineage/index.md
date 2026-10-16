# Data Lineage

Data lineage is the ability to trace data from its origin, through every transformation and movement, to its final destination. It answers three fundamental questions:

- **Where did this data come from?**
- **What happened to it along the way?**
- **Where is it being used now?**

## Why Data Lineage Matters

Data lineage is not just a technical concern — it has direct business value:

| Business Need | How Lineage Helps |
| --- | --- |
| **Regulatory compliance** | Demonstrates data provenance for GDPR, SOX, and other frameworks |
| **Change impact analysis** | Shows what downstream systems break if you modify a table or API |
| **Root-cause analysis** | Traces bad data back to its source quickly |
| **Stakeholder trust** | Provides transparency about where data comes from and how it's processed |
| **Data quality** | Identifies where quality issues originate in a pipeline |

## Key Terms

> [!NOTE]
>
> **Terminology**
>
> - **Data Lineage** — The complete history of data movement and transformation across systems.
> - **Data Catalog** — A searchable inventory of all data assets (tables, topics, APIs) in the organization.
> - **OpenMetadata** — An open-source data catalog platform that discovers, catalogs, and visualizes data assets and their relationships.
> - **OpenLineage** — An open standard for capturing and sharing data lineage information across tools and platforms.
> - **Lineage Edge** — A directional relationship between two data assets, showing that data flows from one to the other.
> - **Pipeline** — A named process or job that moves or transforms data from one place to another.

## How We Track Lineage

Our approach uses three complementary mechanisms that build on each other:

```
graph LR
    subgraph Discovery["🔍 Discovery Layer"]
        A[Kafka Topics]
        B[Database Tables]
        C[API Endpoints]
    end

    subgraph Relationships["🔗 Relationship Layer"]
        D[Static Lineage Edges]
    end

    subgraph Runtime["⚡ Runtime Layer"]
        E[Dynamic Lineage Events]
    end

    subgraph Visualization["📊 Visualization"]
        F[OpenMetadata<br/>Lineage Graph]
    end

    Discovery --> Relationships
    Discovery --> Runtime
    Relationships --> Visualization
    Runtime --> Visualization
```

### 1\. Scanning &amp; Discovery

OpenMetadata automatically scans our data sources to discover and catalog every data asset — Kafka topics, database tables, and API endpoints. This gives us a complete inventory of what data exists and where.

👉 See [Scanning &amp; Discovery](<https://aureliusenterprise.github.io/main/architecture/data-governance/data-lineage/lineage-scanning/index.md>) for details.

### 2\. Static Lineage Edges

Not all data relationships are discoverable automatically. We define manual lineage edges in project configuration files to declare known relationships — for example, "the `entity` table feeds the FastAPI pipeline, which serves the `/entities/get` endpoint."

👉 See [Static Lineage Edges](<https://aureliusenterprise.github.io/main/architecture/data-governance/data-lineage/lineage-static-edges/index.md>) for details.

### 3\. Dynamic Lineage Events

Applications emit runtime events as data flows through the system. These events capture actual execution — when a pipeline started, how many records it processed, whether it succeeded or failed — providing a live view of data movement.

👉 See [Dynamic Lineage Events](<https://aureliusenterprise.github.io/main/architecture/data-governance/data-lineage/lineage-dynamic-events/index.md>) for details.

## Using the Lineage Graph

Once all three layers are in place, OpenMetadata presents a unified lineage graph that shows the complete picture of how data moves through the organization.

👉 See [Using the Lineage Graph](<https://aureliusenterprise.github.io/main/architecture/data-governance/data-lineage/lineage-visualization/index.md>) for practical guidance.

## Example Data Flow

The following diagram shows a typical data flow in our platform, with all three lineage mechanisms working together:

```
graph LR
    subgraph origin["Data Origin"]
        P["Java Producer<br/>(dynamic events)"]
    end

    subgraph messaging["Messaging"]
        K["Kafka Topic<br/>(scanned)"]
    end

    subgraph processing["Processing"]
        S["JDBC Sink Connector<br/>(static edges + dynamic events)"]
    end

    subgraph storage["Storage"]
        DB[("Postgres Table<br/>(scanned)")]
    end

    subgraph consumption["Consumption"]
        API["REST API Endpoint<br/>(scanned + static edges)"]
    end

    P -->|"emits events"| K
    K -->|"consumed by"| S
    S -->|"writes to"| DB
    DB -->|"feeds"| API
```

## Setup

See [Data Governance Stack](<https://aureliusenterprise.github.io/main/architecture/data-governance/index.md>) for infrastructure setup and quick-start instructions.
