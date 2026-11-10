# 12.4a The source envelope

- **Status:** in review
- **Pull request:** –
- **Records:** DD-462, DD-463, DD-464 (this increment's `design.md`); the umbrella contract is 12.4 (DQS-11..16)

## Scope

The `SOURCES` setting names each dataset's extract path as a flat JSON map (12.2, DQS-04). This
increment replaces that map with a JSON array of source objects. Each source carries its dataset —
by qualified name or guid — inside the entry, next to the `kind` and `config` it names. The file
reader keeps working unchanged, and no new reader lands here. The router between kinds is the one
new piece.

The step makes the umbrella's rules true in code before any second source arrives (DQS-11,
DQS-12). A later increment adds one reader and answers its own questions (12.4, "How a source
lands"). The database choice stays open.

## What lands

The job accepts the new shape, and only the new shape. `SOURCES` is a JSON array, and a source is
one object:

```json
[
    {
        "config": { "path": "/data/d3.parquet" },
        "dataset": { "qualifiedName": "/d3" },
        "kind": "file"
    }
]
```

- `dataset` names the catalogue dataset the rows belong to: its `qualifiedName`, or its `guid`
  when the name can change (DQS-20). Exactly one of the two, always.
- `kind` names the reader. The only kind in this cut is `file`, and its `config` holds one key,
  `path`.
- A dataset no source names is skipped, as before (DQS-04, DD-459).
- The scan reaches every dataset through the same reader seam (DQS-11). The seam names both
  identities on `read` already; its `skip_reason` grows the guid with it (DQS-20).

## Rules

Tests name each id with `@pytest.mark.covers(..., rules=[...])` (ADR 056).

| Id     | Rule                                                                                                                                                                                                                                                                                           |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DQS-17 | `SOURCES` is a JSON array of source objects, each with a `dataset`, a `kind` string, and a `config` object. Any other shape — a bare path, a map, a wrong type, a missing key — is a configuration error, and the job exits 1 (DQS-01). Two sources naming the same dataset is the same error. |
| DQS-18 | The router sends a dataset to the reader of its source's `kind`. A kind the job does not have is a skip with the reason `kind not available`, counted like any other skip (DQS-04) — the run continues.                                                                                        |
| DQS-19 | The file reader reads `config.path` exactly as 12.2 reads the mapped path: the same formats, the same skip reasons, the same row budget (DQS-04, DQS-05). The old shape (a bare path string) is not accepted.                                                                                  |
| DQS-20 | A `dataset` names the dataset by `qualifiedName` or by `guid`, exactly one. The router answers a guid source for the dataset with that guid, and a name source for the dataset with that name. A guid source answers its dataset before a name source of the same dataset does.                |

## Explicitly not delivered

| What                                             | Where | Why                                                                      |
| ------------------------------------------------ | ----- | ------------------------------------------------------------------------ |
| A second reader (SQL, object store)              | 12.4  | The database choice stays open; each source is its own decision (DD-459) |
| A `kind` per entry that changes the file reader  | –     | DQS-19 keeps the file reader's pairs as the floor                        |
| Any change to the scan, the rule door, the write | –     | DQS-11: the seam hides the new piece, and those steps stay unchanged     |

## Test map

| Rule   | Unit proof                                                                                         |
| ------ | -------------------------------------------------------------------------------------------------- |
| DQS-17 | The settings parse the array; each bad shape, and a dataset named twice, raise the settings error. |
| DQS-18 | The router reads a `file` dataset and skips an unknown `kind` with its reason.                     |
| DQS-19 | The file reader reads through the router and keeps its reasons and its budget.                     |
| DQS-20 | A guid source answers by guid, a name source by name, and the guid source answers first.           |

## Java origin

– (net-new). The legacy job had no file source map.

## Acceptance

The e2e suite (12.2) points its source list at the router through the new shape. The five e2e
proofs stay green. The file reader's unit pairs stay green (DQS-19's floor).
