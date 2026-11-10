# 12.4 Source readers (umbrella)

- **Status:** in progress (12.4a landed the envelope and the router)
- **Pull request:** –
- **Records:** DD-459 (the seam this plan extends); DV-146 (the retired stream); 12.4a adds
  DD-462..464; the first source adds DD-465 onward

## Scope

The scanner reads one kind of source today: a file on a path the operator configured (12.2, DQS-04).
This track adds readers for more kinds, so a dataset's rows can live outside the scanner's own file
system.

The choice of database stays open on purpose. No customer source is picked yet, and each source is
its own decision (DD-459). This umbrella fixes what never changes: the contract every reader obeys.
Each source lands in its own increment with the answers its own list needs. The track's first step,
the configuration envelope and the router, landed as 12.4a (DQS-17..20). The track can split later,
the way the 7.x track did.

## The contract every reader obeys

These rules bind every source reader in this track. Tests name the ids with
`@pytest.mark.covers(..., rules=[...])` (ADR 056).

| Id     | Rule                                                                                                                                                                                                       |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DQS-11 | The scan reads every dataset through the reader seam (DQS-04). A new reader adds no step to the scan, the rule door, or the score write (DD-459).                                                          |
| DQS-12 | The operator configuration names every source before the scan runs. No reader derives a source from a catalogue attribute, and none discovers one by a walk.                                               |
| DQS-13 | A source that refuses a dataset skips that dataset with a stated reason, and the scan continues (DQS-04). Each source's spec names which failures are refusals, and which fail the run (DQS-01).           |
| DQS-14 | A credential stays a secret. It arrives through the encrypted environment or a mounted file the deployment owns (ADR 008). A map value, a log line, a score entity, and an error message carry none of it. |
| DQS-15 | Every reader cuts its own read at the row budget (DQS-05). A reader whose source cannot cut at its door must stream the rows and stop at the budget.                                                       |
| DQS-16 | A reader's suite proves one real scan against a real instance of that source (ADR 012). The service is the suite's own, namespaced and disposable. Nothing restarts a shared dev service (DD-223).         |

## Candidates

The candidate list is open. The table states what exists today and what a source's spec must answer
before its reader lands.

| Source                  | The read path today                                                                                                                                                                                    | What its spec must answer                                                                                                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SQL database            | polars answers a SQL query as a frame through `read_database_uri`. The route is a ConnectorX or an ADBC driver, and neither is in the workspace today. The driver joins the increment with the reader. | Which database. Which driver. How the map names a table without carrying a password. How the budget cuts the read: at SQL, or over the frame. Which disposable service the suite runs against. |
| Object store (S3 API)   | polars reads a Parquet or CSV object from an S3 API through `storage_options`.                                                                                                                         | Which vendor surface. Which auth: a role the node already holds, or a key. How the map names a bucket, a prefix, and a key.                                                                    |
| Kafka stream            | none. The legacy job read it, and DV-146 retired that shape. A stream has no bounded row count to cut at (DD-460).                                                                                     | Closed for this track. A streaming increment owns it with its own watermark decision.                                                                                                          |
| A named prefix of files | none. The file reader takes one path per dataset.                                                                                                                                                      | Kept closed. DD-459 rejected discovery: a catalogue name must never become a path. An operator-named prefix can reopen it as its own decision.                                                 |

## How a source lands

The configuration envelope is in place: `SOURCES` is a list of sources, each naming its dataset
(by qualified name or guid), its `kind`, and its `config`, and the router sends each dataset to
the reader of its kind, guid first (12.4a, DQS-17..20, DD-462..464). A new source adds its config
schema to the settings' kind table and its reader to the router's table.

1. A deployment names its source. That source picks the track's first reader (DD-459).
2. Write the source's answers into this spec. Add a `DD-NNN` record for each decision
   (DD-465 onward).
3. Implement the reader on the seam. The scan, the rule door, and the score write stay unchanged (DQS-11).
4. Add the driver dependency and the suite's service. The service is namespaced and disposable (DQS-16, DD-223).
5. Run the workspace gates at levels 0 to 2, the way 12.2 did.

??? QUESTION "Which database will Aurelius Atlas support?"

    The first real customer source decides. Each reader is small on top of the seam, so the choice waits for the deployment that needs it (DD-459).

## Java origin

– (net-new). The legacy job read Kafka streams. The batch port retired that shape (DV-146).

## Deviations

None new. The batch posture of DV-146 stands.

## Acceptance

Each source lands with its own rules, its unit pair over its own fake, and one e2e proof against a
real instance (ADR 012). The file reader's pairs stay the floor: a new reader must not break them
(DQS-11).
