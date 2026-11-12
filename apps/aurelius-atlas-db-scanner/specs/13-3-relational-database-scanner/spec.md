# 13.3 The relational database scanner

- **Status:** in review
- **Pull request:** #323
- **Records:** adds DBS-01..12 and DD-502..507 (here; the numbers sit past open #321's
  DD-498..501 so no renumber lands at merge); relies on KSC-03/06/07/09 (the qualified-name
  rule, the field shape, the one bulk write, the service identity, 13.1), AUT-02/AUT-10 (azp
  audiences, scrubbed reads), DD-362 (the m4i models load at boot), EWR-08/EWR-11 (the
  unchanged skip, an end resolves by guid or unique attribute), DD-223 (e2e rides the shared
  dev stack, never restarted), and ADR 051/056.

## Scope

A relational database is the catalogue's oldest kind of asset: its tables, their columns,
types, comments, primary keys and foreign keys describe data people search for. The legacy
platform registered such schemas only through its registered hooks or a CSV import; there was
no job that looked at a live database and registered what it found. The starting point of this
increment is a standalone reflection script that exported a JSON catalog to a documents folder
for a different product's file-based pipeline; its reflection core is ported and its output
contract is replaced (DV-150).

This increment delivers `apps/aurelius-atlas-db-scanner`: a batch CLI, in the shape of the
Kafka scanner (13.1), that reflects one live relational database through SQLAlchemy and
registers what it finds in the catalogue. One scan opens the database (DBS-02), reflects each
admitted table (DBS-04, DBS-05), maps each one to a Dataset whose columns are its Fields
(DBS-06), hangs the tables under a System and one Collection per schema (DBS-03), records each
foreign-key column pair as a Process (DBS-08), and writes the whole tree in one bulk request as
its own service identity (DBS-09, DBS-10). A re-scan updates the same entities in place (DBS-11). The
genericity is the reflection: the same scan answers for every dialect SQLAlchemy reflects, so
the job names no database product (DBS-01).

Delivered here:

| Module        | Holds                                                              |
| ------------- | ------------------------------------------------------------------ |
| `settings.py` | the app configuration under `AURELIUS_ATLAS_DB_SCANNER_`           |
| `database.py` | the database door: connect, schema names, table names, one reflect |
| `reflect.py`  | the reflection: an inspector's table to the scan's table model     |
| `graph.py`    | the table list to catalogue entities, the qualified names, the FKs |
| `scan.py`     | one scan: the steps, the notices, the one bulk write               |
| `__main__.py` | the CLI: the run, the Keycloak token, telemetry, the exit code     |

Also delivered: the dev realm's `aurelius-atlas-db-scanner` service-account client and the e2e
proof against a disposable Postgres the suite starts on its own (a sample `dhi.io/postgres`
image it creates and removes, never the shared Keycloak store).

Explicitly not delivered, with the increment that will:

| Not delivered                                                  | Lands with | Why                                                                     |
| -------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------- |
| The Helm chart, the CronJob schedule, the server audience join | 13.4       | The chart track owns deployment (13.1's split, same rule)               |
| A registered view as a dataset                                 | –          | Reflection reads table metadata only; views need a second read (DBS-04) |
| A row, a value, or a statistic                                 | –          | The scan registers metadata; 12.2's readers read data                   |
| Stored procedures, triggers, sequences, partitions             | –          | They are not in the m4i tree, as in Kafka scanning (13.1)               |
| Lineage from query logs                                        | –          | Foreign keys are the only relationships the scan can prove (DBS-08)     |
| A second database in one run                                   | –          | One DSN per run; a deployment runs the job once per database            |
| A `database` reader in the quality scanner's router            | 12.4       | The 12.4a envelope keeps one kind (`file`) until its umbrella lands     |

## Semantics

Python tests name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056). The tree, the
qualified-name rule, and the catalogue write are 13.1's contracts (KSC-03, KSC-06, KSC-07) and
are cited, not restated.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DBS-01 | The scan speaks no database product. It reflects through SQLAlchemy, so every dialect with a driver in the job's environment works (delivered here: Postgres through `psycopg` for the e2e, and SQLite from the standard library for the offline tests; a deployment adds a driver and gains its dialect with no code change). The vendor tooling of no product is used, and no `information_schema` SQL is written. A DSN whose dialect has no driver in the image is a configuration error at start naming the driver to install (DBS-12).                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| DBS-02 | The scan runs as one process: it connects, reflects, builds, writes, and exits. Exit 0 is a completed scan — a table whose reflection fails is data with a notice, not a failure (DBS-05). Exit 1 is a run-level failure: a bad configuration, a refused token, a database that answers no connect in the timeout, a refused write. The connect timeout is a setting, and a silent database fails the run naming the DSN's host and database, never its credentials.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| DBS-03 | The tree hangs under the configured System (`SYSTEM_NAME`, no default — the operator names the system the database belongs to). It holds one Collection per schema the scan reads (DBS-04). Each table is one Dataset under its schema's Collection. The qualified names follow the legacy rule, as the Kafka scanner applies it (KSC-03): a Collection is `<system>--<schema>`, and a table's is `<system>--<schema>--<table>`. `SCHEMA_NAME` overrides the Collection's name for the default schema of a dialect that has none (the nameless-schema case, DBS-04).                                                                                                                                                                                                                                                                                                                                                                                                                              |
| DBS-04 | The schemas to scan are every schema the dialect answers, minus a fixed system set: `pg_catalog`, `information_schema`, `pg_toast`, any name starting with `pg_`, `mysql`, `sys`, and `performance_schema` (a dialect's metadata lives in its own system schemas, and a scan must not register them). A schema whose reflection the dialect refuses is skipped with a debug notice, not a failure (the SQLite case: it answers schema names it cannot introspect). `SCHEMAS` is a comma-separated list of patterns a schema must match, case-insensitive, each `*` standing for any run of characters, the default `*`. On a dialect with one nameless schema (SQLite), the nameless schema is scanned as the default and `SCHEMA_NAME` names its Collection.                                                                                                                                                                                                                                     |
| DBS-05 | `TABLES` is a comma-separated list of patterns a table name must match, case-insensitive, `*` the wildcard, the default `*` (the Kafka scanner's filter rule, KSC-02, applied to table names). A table the patterns admit but the inspector fails to reflect keeps no fields and gets a notice naming the table and the failure reason; its dataset is still registered (the field-less case, as KSC-05). The scan reflects table metadata only: a view is not in `get_table_names`, so it stays unregistered (the spec's Scope).                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| DBS-06 | A table's columns are its Fields, by the Kafka scanner's field shape (KSC-06): each field's `fieldType` is the rendered column type — `str(column["type"])`, so the dialect's own name reads back (`VARCHAR(255)`, `INTEGER`) — and its `definition` is the column comment when one exists. A primary-key column is marked in the field's `definition` only when it carries no comment of its own (the mark reads `Primary key`). No attribute of the m4i field type is invented for a database (the m4i model is fixed, DV-139).                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| DBS-07 | A table's Dataset carries the table comment as its `definition` when one exists. Every reflected table becomes a dataset, including a table with no columns and a table whose reflection failed (DBS-05). The dataset's `name` is the table's own name; its qualified name follows DBS-03.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| DBS-08 | A foreign key becomes one Process per constrained column pair: `name` `<schema>.<table>.<column>`, qualified name `<system>--<schema>--<table>--<column>` (KSC-03's composition, one level below the table), with the referring table's Dataset as its `inputs` end and the referred table's as its `outputs` (Atlas's `Process` ends, which `m4i_generic_process` inherits). A composite key therefore yields one Process per pair — the column-level edges the legacy JDBC hook's `columnPair` meant — because the m4i process type carries no column attribute and none is invented (DV-139). A referred column that is None names the referred table's primary-key column in the same position; a key whose referred columns cannot be resolved, or whose referred table sits outside the scan's admitted set (a filtered schema or table), is dropped with a notice — a process end must name two registered datasets. A self-referencing key gives a process the same dataset on both ends. |
| DBS-09 | The scan writes one bulk request per run: the System, each Collection, each Dataset, each Field, each Process, each new entity under a request-local temporary guid with the ends riding `relationshipAttributes` through those guids (KSC-07, DD-466). A re-scan is idempotent: an entity the store holds by its unique qualified name updates in place, no entity duplicates, and an unchanged tree is skipped whole (EWR-08). A dropped table's dataset stays as it is — the scan registers what is, never what was (KSC-07's clause).                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| DBS-10 | The job authenticates to the catalogue as its own service identity: client credentials of the `aurelius-atlas-db-scanner` confidential client (DD-458's pattern, 13.1's sibling), whose token the server accepts for read and write; the audience join follows the same wiring (`AURELIUS_ATLAS_SERVER_AUTH_AUDIENCES`). All catalogue traffic goes through `aurelius-atlas-server-client` — the job never touches the store directly (KSC-09). A refused mint is a run-level failure (DBS-02). The DSN, with its credentials, is a secret setting: it is required, and its flag is suppressed from the help like every other secret key (DD-472's pattern).                                                                                                                                                                                                                                                                                                                                      |
| DBS-11 | The settings model is the CLI (DD-472): every key has a flag, parsed over the environment, under the `AURELIUS_ATLAS_DB_SCANNER_` prefix. `--dry-run` runs the whole read and writes nothing; it prints one line per entity the run would write, and every notice. `--table` (repeatable) limits the scan to named tables, matched like `TABLES`; a database that lacks a named one is a notice, not a failure. `--schema` (repeatable) limits the schemas, matched like `SCHEMAS`. A malformed flag or setting is a configuration error (DBS-02). Telemetry rides the same OTLP ingest client the quality scanner uses (DD-196).                                                                                                                                                                                                                                                                                                                                                                 |
| DBS-12 | The settings stand or fall as a whole: a DSN that is absent or not a database URL, a `SYSTEM_NAME` that is empty, or a timeout that is not positive is a configuration error that names the key (DBS-02's exit-1 case). An `--out`-style file option does not exist: the catalogue is the only output of this job.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

## Ported from

No Apache Atlas class is involved. The starting point is the user's standalone reflection
script (a `scan_database.py`: SQLAlchemy reflection to a JSON catalog for a different
product's file-based pipeline); this increment ports its reflection core and replaces its
output contract with the catalogue write (DV-150). The tree, the qualified-name rule, the
field shape, the filter idiom, and the service identity are the Kafka cluster scanner's
(13.1, itself the legacy `apps/m4i-data-dictionary-io` shape). The legacy platform's registered
JDBC hooks (`hook-runtime`'s `JdbcConsumer`, the `classic_jdbc_*` models) registered tables
from query-lineage events, not from a live database, and land with no increment
([java-map](../../../../docs/architecture/conversion/java-map.md)).

## Deviations

One row joins [Deviations](../../../../docs/architecture/conversion/deviations.md) in the
same PR:

- **DV-150** (DB scanning): Apache Atlas learns a database's tables and columns only from hook
  messages a registered application pushes (`classic_jdbc_*`, `dataset_db`); Aurelius Atlas
  reflects the live database itself and registers the m4i tree, needing no hook install
  (DBS-01, DBS-09). The starting script's JSON-to-folder handoff is not delivered, because no
  such pipeline exists in this architecture.

## Acceptance

| Ids    | Proven by                                                                                                                                                                                  |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| DBS-01 | `tests/test__database.py` (the door against a SQLite inspector — a product no driver of this job talks to)                                                                                 |
| DBS-02 | `tests/test__scan.py` (a completed scan with a notice; a dead database fails the run naming host and name, not the password), `e2e/` (a refused connect exits 1)                           |
| DBS-03 | `tests/test__graph.py` (the tree, the qualified names, the nameless-schema override)                                                                                                       |
| DBS-04 | `tests/test__database.py` (the system-schema set per dialect, the patterns, the un-introspectable schema skip)                                                                             |
| DBS-05 | `tests/test__database.py` (the table patterns), `tests/test__scan.py` (a failing table: a field-less dataset and a notice)                                                                 |
| DBS-06 | `tests/test__reflect.py` (the rendered type, the comment, the primary-key mark, a comment that keeps its text)                                                                             |
| DBS-07 | `tests/test__reflect.py`, `tests/test__graph.py` (the comment as definition; a zero-column table still becomes a dataset)                                                                  |
| DBS-08 | `tests/test__graph.py` (one Process per column pair, the composite key's pair of processes, the referred-primary-key resolution, the dropped edge and its notice, the self key)            |
| DBS-09 | `tests/test__graph.py` (temp guids and ends), `e2e/` (a re-scan: one dataset, updated in place)                                                                                            |
| DBS-10 | `e2e/` against the dev stack (the scanner's own token writes the tree, and it reads back; the DSN stays out of help and logs)                                                              |
| DBS-11 | `tests/test__settings.py` (the flags over the environment, suppressed secrets out of the help), `tests/test__scan.py` (dry-run writes nothing; the filters and their missing-name notices) |
| DBS-12 | `tests/test__settings.py` (each refused setting, naming its key)                                                                                                                           |

Run: `uv run pytest apps/aurelius-atlas-db-scanner/tests` offline; `npx nx test
aurelius-atlas-db-scanner -c ci`; `npx nx e2e aurelius-atlas-db-scanner` against the dev stack
plus the suite's own disposable Postgres.
