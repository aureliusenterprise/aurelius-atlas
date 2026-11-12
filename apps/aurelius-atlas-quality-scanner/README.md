# aurelius-atlas-quality-scanner

The Aurelius Atlas quality scanner: a batch job that scores the data-quality rules stored in
the catalogue and writes the scores back. It is the customer-facing half of data quality
([ADR 051](../../docs/architecture/adr/051-the-conversion-proceeds-in-specified-increments.md),
increment 12.2). The engine that computes each score lives in
[aurelius-atlas-quality](../../libs/python/aurelius-atlas-quality/README.md) (12.1). This app
does the I/O around it: rules in, extracts read, scores stored.

The legacy job was a Flink stream over Kafka and is not ported
([DV-146](../../docs/architecture/conversion/deviations.md)). Aurelius runs a bounded batch:
one process per scan, reading the ACTIVE `m4i_data_quality` rules, evaluating each rule over
its dataset's extract, and storing one `m4i_dq_score` entity per rule and dataset, newest in
place. The webapp's score box and badges (7.25) read the entities this job writes.

The [spec](specs/12-2-quality-scanner/spec.md) states the DQS-01..10 rules. The source list's
envelope — each source names its dataset, its `kind`, and its `config` — is 12.4a (DQS-17..20);
the readers other than `file` are the open
[12.4 track](specs/12-4-source-readers/spec.md).

## Scan

```bash
npx nx scan aurelius-atlas-quality-scanner               # one scan, writes scores
uv run python -m aurelius_atlas_quality_scanner --dry-run   # print candidates, write nothing
uv run python -m aurelius_atlas_quality_scanner --dataset orders.daily  # one dataset
```

Exit 0 means the scan completed. A rule that cannot run is an ERROR score entity, not a failed
run (DQS-08). Exit 1 means the run itself failed: bad configuration, a refused token, or a
refused write (DQS-01).

## Configuration

Every key carries the `AURELIUS_ATLAS_QUALITY_SCANNER_` prefix. The required three:

| Key             | Meaning                                                              |
| --------------- | -------------------------------------------------------------------- |
| `SERVER_URL`    | the Atlas server to scan against (default `https://localhost:21000`) |
| `CLIENT_ID`     | the scanner's realm client, default `aurelius-atlas-quality-scanner` |
| `CLIENT_SECRET` | the secret of that client (DD-458)                                   |

The rest have defaults: `SOURCES` (a JSON array of sources, each naming its dataset by qualified
name or guid, its reader kind, and its config —
`[{"dataset": {"qualifiedName": "/d3"}, "kind": "file", "config": {"path": "/data/d3.parquet"}}`,
DQS-04, DQS-17 and DQS-20 — only `file` is read today), `MAX_ROWS` (the read budget per extract,
DQS-05), `CA_FILE` (the CA that verifies the server and the issuer), `TOKEN_URL`, and the optional
`OTEL_*` block for OTLP export.

## Run in dev

```bash
npx nx scan aurelius-atlas-quality-scanner   # dev Keycloak + server must be up
npx nx test aurelius-atlas-quality-scanner -c ci
npx nx e2e aurelius-atlas-quality-scanner    # the scanner in-process against a real server image
```

The job has no port and no liveness endpoint: it runs to completion and exits, so the image
carries no healthcheck. In production the standalone `atlas-quality-scanner` Helm chart
(`helm/`) runs it as a CronJob on the schedule the deployment names (12.3).
