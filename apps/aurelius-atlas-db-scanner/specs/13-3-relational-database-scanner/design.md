# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-502. The database door is SQLAlchemy Core reflection, per dialect

- **Status:** Proposed
- **Increment:** 13.3
- **Date:** 2026-11-11

**Decision.** The scan reads the database through SQLAlchemy Core's `inspect(engine)` —
`get_schema_names`, `get_table_names`, `get_columns`, `get_pk_constraint`,
`get_foreign_keys`, `get_table_comment` — behind one door class (`DatabaseDoor`, DBS-01..05).
No `information_schema` SQL is written, no vendor CLI is called, and the scan's walk imports
nothing dialect-specific. The dialect branches the reflection honestly needs (the nameless
default schema, the per-dialect system-schema set) live in the door, keyed by
`engine.dialect.name`.

**Reason.** The starting script proved the reflection core works across products with one
API, and SQLAlchemy's inspector is the only layer that hides five vendor catalogs behind
one contract. The m4i tree (DBS-03..08) needs exactly what the inspector answers: names,
rendered types, comments, primary keys, foreign keys. Writing the vendor catalogs by hand
would re-decide, per product and per version, what one library already resolves — and would
break DBS-01's claim. The user's script's own bug is the argument for the door seam: it
skipped Postgres `pg_*` schemas only after its reflection attempt had already failed on
them, relying on a broad `except` to hide the order. The door checks the dialect's system
set first (DBS-04), so a skip is a decision, not a swallowed error.

**Alternatives.** `inspect` from `sqlalchemy` directly at each call site: no seam, and the
unit tests would need a live database for every rule. Vendor catalogs through `psycopg`
and friends: five readers for the one tree, and every new dialect is new code. The
Atlas JDBC hook model (a registered application pushes metadata): it inverts the ask —
the point is to scan a database that runs no hook.

**Consequences.** The door is a Protocol the unit tests fake (13.1's idiom), so DBS-02..05
run offline. The dialect set that works is exactly the drivers installed (DBS-01), and the
image's driver list is a dependency decision the e2e enforces: `psycopg` rides in for the
Postgres suite, and SQLite stands on the standard library. A dialect whose inspector
behaves differently (a name it cannot introspect) is the door's case to skip with a debug
notice, never the walk's (DBS-04).

### DD-503. One scan, one database: one DSN per run

- **Status:** Proposed
- **Increment:** 13.3
- **Date:** 2026-11-11

**Decision.** A run takes exactly one `DSN` and registers one database (DBS-02, DBS-12). A
deployment with n databases runs the job n times with n configurations, the same as the
Kafka scanner runs once per broker.

**Reason.** One database is one failure domain and one service identity audit line. A
multi-DSN list would split the run's exit into partial successes, and DBS-02's clean rule
(exit 0 is a completed scan, exit 1 is a run-level failure) would need a third answer. It
would also pool credentials for n databases into one process's environment, where n
schedules each holding one secret keeps a leaked configuration small (the DD-472 secret
rule, per job).

**Alternatives.** A `DATABASES` list of DSNs: the exit-code ambiguity above, and no real
saving — a scheduler loops by itself. A per-schema process fork: parallelism nobody asked
for, and one bulk write per schema would trade KSC-07's one-request atomicity for nothing.

**Consequences.** The settings keep one required secret key (DBS-10). The 13.4 chart's
CronJob renders one Job per configured database from the same image, which is the shape
13.2 already plans for brokers.

### DD-504. The tree hangs tables under a System and a per-schema Collection

- **Status:** Proposed
- **Increment:** 13.3
- **Date:** 2026-11-11

**Decision.** The scan builds `m4i_system` (named by `SYSTEM_NAME`, no default) holding one
`m4i_collection` per scanned schema, each holding its tables as `m4i_dataset` (DBS-03).
Qualified names compose by KSC-03's rule: `<system>--<schema>` for a Collection,
`<system>--<schema>--<table>` for a Dataset. A dialect with no real schemas (SQLite) gets
one Collection named by `SCHEMA_NAME` (default `default`). The Kafka scanner's builder
idioms are reused as patterns — qualified-component sanitizing, temp guids,
`relationshipAttributes` — by porting the four small helpers, not by importing across apps
(ADR 002: apps are removable slices).

**Reason.** The m4i model's own vocabulary fits a database exactly: a System is the
platform, a Collection is a named grouping of datasets, a Dataset is the asset. Schema is
the grouping a relational database actually has, and one Collection per schema keeps a
10,000-table database browsable one schema at a time. Skipping the Collection level would
push the schema into the table's qualified name anyway (two components joined), inventing
in a string what the model already offers as an entity. The legacy data-dictionary IO app
used exactly this shape for its database source (`System`/`Collection`/`Dataset`/`Field`),
so a catalogue scanned by the legacy job and by this one converges on the same names.

**Alternatives.** One Collection for the whole database, the Kafka scanner's shape (its
cluster id): a relational database's schemas are meaningful boundaries (ownership,
synonyms, access), and flattening them loses the DBS-04 filter's unit. Datasets directly
under the System: the model allows it and the webapp renders it, but it makes the schema
nameless in search facets. A second `--schema-depth` knob: nothing to configure until a
real database needs it (ponytail).

**Consequences.** The qualified-name contract (KSC-03) is the reuse point: a table
re-registered under a changed `SYSTEM_NAME` is a new entity, and the spec says so by
naming the System required (DBS-03). The ported helpers are small and tested here; if 13.x
grows a third scanner, a shared library extracts them (the 12.4a `SourceRouter` precedent
for pulling a seam out of the second user).

### DD-505. A foreign-key column pair is an `m4i_generic_process` between the two datasets

- **Status:** Proposed
- **Increment:** 13.3
- **Date:** 2026-11-11

**Decision.** Each constrained-column pair of a foreign key becomes one
`m4i_generic_process` entity: its `inputs` end names the referring table's Dataset, its
`outputs` end the referred table's, with the qualified name
`<system>--<schema>--<table>--<column>` (DBS-08). A composite key therefore yields one
Process per pair. A referred table the scan does not register drops its Processes with a
notice, because a process end that resolves to nothing fails the whole bulk write
(EWR-11's resolution is by stored or request entity, and a filtered table is neither).

**Reason.** A foreign key is a relationship between two datasets with a direction, which is
what Atlas's `Process` means (`inputs`/`outputs`). One Process per column pair matches the
legacy JDBC hook's `columnPair` granularity, and it is the only shape the shipped model
carries: `m4i_generic_process` has no column attribute, so a key-wide entity would have
nowhere honest to say which columns it joins — inventing one edits the fixed m4i model
(DV-139). The alternative homes are worse: the m4i dataset type has no peer end to point at
a sibling dataset (its `parentDataset`/`childDataset` is a composition hierarchy, and
abusing it invents a hierarchy the database does not claim), and a custom relationship type
would add a typedef the same rule forbids. The webapp's details page renders a process page
with its inputs and outputs (7.21c), so the FK becomes navigation without new UI. The
starting script's FK bugs die here: it kept only `constrained_columns[0]` of a composite
key and guessed `ref_column or "id"`, a guess that is wrong whenever the referred primary
key is not named `id`. The scan walks every constrained column in order and resolves a None
`referred_column` against the referred table's actual primary key, position by position
(DBS-08).

**Alternatives.** One Process per key with the columns as a JSON attribute string: the
string is invisible to lineage and the process page, and it re-creates the starting
script's flat catalog in the store. Atlas's own `classic_jdbc_*` types: they hang off the
hook model (a registered application's columns), not off reflected metadata, and DV-139
keeps the shipped models as they are. Nothing at all: FKs are the strongest signal a
relational database gives, and the scan would be weaker than the script it ports.

**Consequences.** A composite two-column key writes two processes between the same two
datasets, and they differ only by their column-level qualified names — a tree that reads
slightly literal, and honest about what the store can carry. Self-referencing keys produce
a process with the same dataset on both ends (a valid graph, an honest fact). A cycle of
FKs is a cycle of processes (Atlas graphs allow it; the lineage page walks it). The notice
for a dropped edge keeps the filter's effect visible: an operator who filters
`TABLES=orders,%` sees which FK edges the filter removed (DBS-05, DBS-08).

### DD-506. The DSN is the job's required secret, and its driver set is the image's

- **Status:** Proposed
- **Increment:** 13.3
- **Date:** 2026-11-11

**Decision.** `DSN` is a required, `CliSuppress`ed setting under the app's prefix (DD-472's
pattern: the value reaches the process only from the environment, and `--help` never shows
the flag). It joins `.env.enc` like every other secret and is excluded from every log
line, notice, and error body — the connect-failure message names the URL's host, port, and
database through `engine.url.render_as_string(hide_password=True)` (DBS-02, DBS-10). The
delivered drivers: `psycopg` (Postgres, the e2e) and the standard library's `sqlite3`
(offline tests). A DSN naming another dialect fails at start naming that driver to
install (DBS-01).

**Reason.** The DSN of a production database carries credentials in one string, so it is
exactly the class DD-465..472's secret rules protect. `render_as_string(hide_password=
True)` is SQLAlchemy's own scrubbing, so the rule is one call, not a regex. The minimal
driver set follows DD-465's musl-wheel rule: `psycopg` (v3) ships musllinux wheels; a
deployment that scans Oracle adds `oracledb` (also pure-ish, thin mode) to its own image
layer — the door answers any dialect, so the image choice is deployment's (DBS-01).

**Alternatives.** Split `HOST`/`PORT`/`USER`/`PASSWORD` keys: more secrets to hold, and it
re-invents the URL parser's job badly; a single DSN is what SQLAlchemy and every operator
already speak. An advertised `--dsn` flag: it puts a password in shell history and the
process list, the DD-472 gap exactly.

**Consequences.** The e2e's Postgres credentials come from the suite's own compose file,
namespaced per run (DD-223: the suite creates and drops its own database inside the
disposable container, and never touches the shared dev stores). The start-up driver check
is one `sqlalchemy.dialects.registry` lookup wrapped as a configuration error (DBS-12).

### DD-507. e2e runs on the suite's own disposable Postgres, never a shared one

- **Status:** Proposed
- **Increment:** 13.3
- **Date:** 2026-11-11

**Decision.** The e2e suite starts its own Postgres service in its `docker-compose.yaml`
(the `dhi.io/postgres` image, loopback-pinned, digested like every other image, CHT-92),
seeds a small fixture schema with `psycopg`, runs the scan in-process through the
`build_client` seam (13.1's idiom), reads the tree back through the scanner's own token,
re-scans for the idempotence proof (DBS-09), and drops the schema and stops the container
in teardown. It does not touch `dev/keycloak`'s Postgres or the shared Elasticsearch
(DD-223).

**Reason.** The rule "each suite proves one real scan against a disposable instance of its
source" (the 12.4 umbrella, DQS-11..16) is this suite's contract, and DD-223 forbids
restarting shared stores mid-suite. A SQLite-only e2e would run the walk but never the wire Postgres
reflection the scanners get hired for (comments, FK detail, schema filtering). There is no
shared dev Postgres to ride: `dev/postgres` left with the example stack (ADR 050), so a
disposable one is also the only honest option. The suite's fixture schema (a dozen tables,
two schemas, a composite FK, a self-FK, comments on both sides) doubles as the parity
fixture a reviewer reads (ADR 052's citation idiom, adapted: the expected tree is written
out in the suite, not read from a live Atlas).

**Alternatives.** The dev Keycloak Postgres as the scan target: it is a shared store, and
seeding a dozen tables into an identity database is precisely the cross-suite interference
DD-223 exists to stop. SQLite over a file: no server round trip, no schemas, no comments —
it proves the walk but not the product. A `testcontainers` spin-up inside pytest: the
workspace's compose-first e2e idiom (12.2, 13.1) keeps the service definitions reviewable
in YAML, and the compose file carries the digest pin.

**Consequences.** The suite costs one container's boot; its healthcheck gates the first
connect, so a cold-start race is a failed healthcheck, not a flaky test. The compose file
joins the dev networks like 13.1's server service, so the scanner reaches Keycloak, the
server, and its Postgres from one `docker compose up`. Teardown drops by schema name
namespaced with the run id (the `zz<run>` idiom of 13.1's topic names).
