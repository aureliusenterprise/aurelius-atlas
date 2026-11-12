# aurelius-atlas-db-scanner

The Aurelius Atlas relational database scanner: a batch job that reflects one
live database and registers what it finds — the schemas, their tables, their
columns, and their foreign keys — in the catalogue. It is the relational cut of
the scanning track
([ADR 051](../../docs/architecture/adr/051-the-conversion-proceeds-in-specified-increments.md),
increment 13.3). The legacy platform registered such schemas only through its
registered hooks or a CSV import. This job looks at the live database itself and
registers what is there
([DV-150](../../docs/architecture/conversion/deviations.md)).

One scan connects to the database, lists the schemas that are not the dialect's
own system schemas, reflects each admitted table through SQLAlchemy, and hangs
the result under a System and one Collection per schema. Each table becomes a
Dataset whose columns are its Fields, with the dialect's own type names and the
database's own comments. Each foreign-key column pair becomes a Process, so the
catalogue can show which table refers to which. The job writes the whole tree in
one bulk request as its own service identity. A re-scan updates the same
entities in place.

The [spec](specs/13-3-relational-database-scanner/spec.md) states the DBS-01..12
rules. The Helm chart and the schedule land with the planned 13.4.

## Scan

```bash
npx nx scan aurelius-atlas-db-scanner                # one scan, writes the tree
uv run python -m aurelius_atlas_db_scanner --dry-run # print the tree, write nothing
uv run python -m aurelius_atlas_db_scanner --schema sales --table orders
```

Exit 0 means the scan completed. A table whose reflection fails is a dataset
with no fields and a notice, not a failed run (DBS-05). Exit 1 means the run
itself failed: bad configuration, a refused token, a database that answers no
connect within the timeout, or a refused write (DBS-02).

The scan names no database product (DBS-01). It reflects through SQLAlchemy, so
a deployment adds a driver and gains its dialect with no code change. The image
ships the Postgres driver (`psycopg`); SQLite works from the standard library,
which is what the offline tests and a `--dry-run` against a local file use.

## Configuration

Every key carries the `AURELIUS_ATLAS_DB_SCANNER_` prefix and has a
command-line flag (`--system-name`, `--schemas`, …): the flag beats the
environment, and `--help` lists them all. The secret keys have no advertised
flag — they are environment settings, so a secret never lands in a shell
history or a process listing (DD-472). The DSN is a secret for the same reason:
it carries the database credentials in one string (DD-506). The required keys:

| Key             | Meaning                                                                                   |
| --------------- | ----------------------------------------------------------------------------------------- |
| `DSN`           | the database URL to scan (DBS-10) — one database per run (DD-503), no advertised flag     |
| `SYSTEM_NAME`   | the catalogue label for the platform the database belongs to (DBS-03) — no default        |
| `CLIENT_SECRET` | the secret of the scanner's realm client (DD-458's pattern, DBS-10) — without it, no scan |

The rest have defaults: `SERVER_URL` (the Atlas server to write to, default
`https://localhost:21000`), `TOKEN_URL`, `CLIENT_ID` (default
`aurelius-atlas-db-scanner`), `SCHEMA_NAME` (the Collection name for a dialect's
nameless default schema, default `default`, DBS-04), `SCHEMAS` and `TABLES`
(comma-separated lists of case-insensitive name patterns, `*` standing for any
run of characters, default `*`, DBS-04/DBS-05), `CONNECT_TIMEOUT_SECONDS` (how
long the door waits for a silent database, default 10, DBS-02), `CA_FILE` (the
CA that verifies the server and the issuer), `LOG_LEVEL`, and the optional
`OTEL_*` block for OTLP export (DD-196).

The run-level knobs are the repeatable flags (DBS-11): `--dry-run` reads
everything and writes nothing, printing one line per entity it would store, and
`--schema`/`--table` narrow one run to named patterns without touching the
configured `SCHEMAS`/`TABLES`.

## Run in dev

```bash
npx nx scan aurelius-atlas-db-scanner   # dev Keycloak and the dev server must be up
npx nx test aurelius-atlas-db-scanner -c ci
npx nx e2e aurelius-atlas-db-scanner    # the scanner in-process against a real server image and its own Postgres
```

The e2e stack starts its own disposable Postgres beside the server (DD-507). In
dev, point the DSN at any database you own:

```bash
AURELIUS_ATLAS_DB_SCANNER_DSN='postgresql+psycopg://atlas:secret@localhost:5432/warehouse' \
npx nx scan aurelius-atlas-db-scanner --dry-run
```

The job has no port and no liveness endpoint: it runs to completion and exits,
so the image carries no healthcheck. In production a scheduler starts it (the
Helm CronJob lands with 13.4).
