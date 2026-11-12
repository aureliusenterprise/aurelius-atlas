# 12.2 The quality scanner

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** adds DQS-01..10 and DD-455..460 (here); relies on DQ-01..08 and DD-450..454
  (12.1, [spec](../../../../libs/python/aurelius-atlas-quality/specs/12-1-quality-engine/spec.md)),
  DD-454/DV-146 (the unread legacy rule is an ERROR, not a guess), DD-369 (nothing measured renders
  nothing), AUT-02/AUT-10 and 10.9 (service identities and per-service credentials), DD-362 (the m4i
  models load at boot), and ADR 051/052/056.

## Scope

The engine (12.1) scores rules over a frame but has no I/O: it reads no data and writes no scores.
This increment builds the batch job that does both: `apps/aurelius-atlas-quality-scanner`, a CLI
that runs to completion and exits. One scan reads the ACTIVE `m4i_data_quality` rules from the
catalogue, finds each rule's datasets through its `fields` end, reads each dataset's extract from a
configured file source, evaluates the rules with `aurelius-atlas-quality`, and writes the scores
back as `m4i_dq_score` entities — newest per rule, in place. A rule the vocabulary cannot read, or
a rule whose column the extract lacks, is recorded with the ERROR verdict (DD-454) and the run
continues.

The job is the customer-facing half of data quality: it runs on a schedule in a customer
environment (the deployment chart is the next increment), and 7.25 reads the score entities it
writes to light the webapp's score box, pies, and badges.

Delivered here:

| Module         | Holds                                                               |
| -------------- | ------------------------------------------------------------------- |
| `settings.py`  | the app configuration under `AURELIUS_ATLAS_QUALITY_SCANNER_`       |
| `sources.py`   | the dataset reader seam, and the file reader for the first cut      |
| `catalogue.py` | the catalogue door: rules and their dataset bindings in, scores out |
| `records.py`   | a score document or an ERROR finding to the entity to store         |
| `scan.py`      | one scan: the five steps, the per-rule and per-dataset outcomes     |
| `__main__.py`  | the CLI: settings, the Keycloak token, telemetry, the exit code     |

Also delivered: the `m4i_dq_score` entity type (DD-455, in the m4i models `aurelius-atlas-core`
loads at boot), the dev realm's `aurelius-atlas-quality-scanner` service-account client (DD-458),
and the e2e proof against the dev stack.

Explicitly not delivered, with the increment that will:

| Not delivered                                                  | Lands with     | Why                                                                               |
| -------------------------------------------------------------- | -------------- | --------------------------------------------------------------------------------- |
| The Helm chart, the CronJob schedule, the server audience join | 12.3           | The chart track owns deployment (10.x's split); the app first                     |
| Customer source readers (JDBC, object store)                   | 12.4           | The reader seam is here (DQS-04); each source is its own decision and secret      |
| The score REST surface and the webapp's score box              | 7.25           | The server and webapp read what the scanner stores                                |
| Score history (one row per run)                                | a later record | Latest-per-rule is the product (DD-456); history needs its own retention decision |
| Incremental scanning (only new rows)                           | a later record | Every scan re-reads its extracts; the budget bounds them (DQS-05)                 |

## Semantics

Python tests name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056). The score entity
and the source map are this increment's own contract; the rule shapes and the engine's verdicts are
12.1's (DQ-01..08) and are cited, not restated.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DQS-01 | A scan runs as one process: it reads the rules, scans, writes, and exits. Exit 0 is a completed scan — rule-level ERROR findings are data, not failures. Exit 1 is a run-level failure: an unreachable catalogue, a refused token, a refused write.                                                                                                                                                                                       |
| DQS-02 | The rules to scan are the `m4i_data_quality` entities of the catalogue whose `active` attribute is not the boolean false (a missing or text `active` is active, as the stored corpus holds both shapes). The list arrives by the basic search of the type, paged by marker to the end.                                                                                                                                                    |
| DQS-03 | A rule's datasets are the datasets reached through the rule's `fields` end and each field's own `datasets` end (DD-457), deduplicated and in first-seen order. A rule that reaches no dataset is skipped with a count; a dataset no rule reached is never read.                                                                                                                                                                           |
| DQS-04 | A dataset's rows come from the reader seam: `read(qualified_name, guid)` answers a polars frame. The first cut is the file reader, configured by the `sources` map from the dataset's qualified name to a path; the format follows the extension (`.parquet`, `.csv`, `.ndjson`, `.json`), and no other extension is read. A dataset with no entry, or no readable file, is skipped with a count and the frame is never guessed (DD-459). |
| DQS-05 | The reader returns at most `max_rows` rows (default 1,000,000); an extract with more is cut at the budget and the run says so. The budget is a memory bound, not a sampling choice.                                                                                                                                                                                                                                                       |
| DQS-06 | The run writes the engine's documents (DQ-08) as `m4i_dq_score` entities, all in one bulk write per scan. Each entity's `scoreKey` is `{datasetGuid}/{ruleGuid}` — `{datasetGuid}/overall` for the summary document — and the write updates the entity with that key in place (DD-456): the store holds the newest scan per rule and dataset, never two.                                                                                  |
| DQS-07 | Each score entity carries the document's attributes (`ruleGuid`, `datasetGuid`, `runId`, `runAtMs`, `dimension`, `checkKind`, `score`, `passed`, `rowsChecked`, `rowsFailed`, and the summary's `dimensions` map), plus the `verdict` `PASS` or `FAIL` from the engine's `passed`, and a `qualifiedName` under the key.                                                                                                                   |
| DQS-08 | A rule the vocabulary cannot read (`QualityRuleError`, the DD-454 case) or a rule whose check cannot run over the frame (`polars.exceptions.ColumnNotFoundError`) is stored as one ERROR entity per dataset: the same key and ids, `verdict=ERROR`, `errorMessage` naming the cause, and no score. The scan continues with the other rules and datasets (DQS-01).                                                                         |
| DQS-09 | `--dry-run` runs the whole scan and writes nothing; it prints one line per stored entity candidate and per skip. `--dataset` (repeatable) limits the scan to the named datasets' qualified names; rules that reach none of them are never evaluated.                                                                                                                                                                                      |
| DQS-10 | The job authenticates to the catalogue as its own service identity: client credentials of the `aurelius-atlas-quality-scanner` confidential client (DD-458), whose token the server accepts for read and write. All catalogue traffic goes through `aurelius-atlas-server-client` — the job never touches the store directly, so auth and audits behave like any client's.                                                                |

## Ported from

none (the legacy Flink `dqscore_*` job, not ported). Where the legacy ran a streaming job over
Kafka with Flink-evaluated rule expressions, Aurelius runs a bounded batch over configured extracts
with the closed vocabulary (DV-146). The Java classes column stays none by that origin.

## Acceptance

| Ids       | Proven by                                                                                                       |
| --------- | --------------------------------------------------------------------------------------------------------------- |
| DQS-01    | `tests/test__scan.py` (exit values), `tests/test__run_fake.py`                                                  |
| DQS-02    | `tests/test__catalogue.py` (paging, the active filter, the raw wrapper, the stamped foreign parameters, DD-461) |
| DQS-03    | `tests/test__catalogue.py` (binding through fields, dedup, the skip)                                            |
| DQS-04    | `tests/test__sources.py` (each format, the unknown skip, no entry)                                              |
| DQS-05    | `tests/test__sources.py` (the cut and its notice)                                                               |
| DQS-06    | `tests/test__records.py`, `tests/test__scan.py` (keys, one bulk write)                                          |
| DQS-07    | `tests/test__records.py` (each attribute, the summary map, the verdict)                                         |
| DQS-08    | `tests/test__scan.py` (the ERROR entity — no score, on the written entity; the run continues)                   |
| DQS-09    | `tests/test__scan.py` (dry-run writes nothing, the dataset filter)                                              |
| DQS-10    | `e2e/` against the dev stack (the scanner's own token reads, writes, and the score entity reads back)           |
| DQ-01..08 | unchanged: the engine's own suite (12.1)                                                                        |
