# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-462. One `SOURCES` entry is a `{kind, config}` object, and the bare path is not accepted

- **Status:** Proposed
- **Increment:** 12.4a
- **Date:** 2026-11-10

**Decision.** Each entry of the `SOURCES` map is a JSON object with a `kind` string and a
`config` object (DQS-17). The file kind's `config` holds one key, `path`, and a file entry whose
`path` is missing or not a string is a settings error. An entry that is not such an object — the
old bare path string, a wrong type, a missing key — fails the settings and the job exits 1
(DQS-19). The settings accept a `kind` no reader answers yet: that is a skip at scan time, not a
settings error (DQS-18).

**Reason.** The umbrella's rule DQS-12 says the operator configuration names every source. A bare
path names only a path: the kind is implicit, and a second kind has nowhere to live without a
second map or a guess. One envelope shape, checked at the settings door, fails a misconfigured
scan before the job signs in or reads a row — the same door DQS-01 already answers with exit 1.
Refusing the old shape, rather than accepting both, keeps one way to say a source: an accepted
bare path would keep two shapes alive forever, and every reader's spec would answer questions
twice.

**Alternatives.** Accept both shapes, reading a bare string as kind `file`: 12.2 shipped no
deployment yet — the CronJob chart lands in 12.3 (DD-459), and the dev `.env` map is empty — so
there is nothing to migrate, and the cheaper moment to break the shape is now. Name the kind in a
sibling map (`SOURCE_KINDS`): two maps for one fact, and they can disagree per dataset. Put the
whole reader choice in the CLI flag: a flag cannot name one source per dataset.

**Consequences.** The README, `.env` comment, and every test that builds the map ride the new
shape. The settings error text names the new shape, so an old map fails with the reason a reader
understands. A later kind adds its `config` schema to the settings' kind table and its reader to
the router's kind table (DD-463). The envelope itself never changes again.

### DD-463. A router picks the reader per dataset, and the seam and the scan stay untouched

- **Status:** Proposed
- **Increment:** 12.4a
- **Date:** 2026-11-10

**Decision.** A `SourceRouter` answers the `DatasetReader` seam (DQS-04) for the whole map: it
sends each dataset to the reader registered for its entry's `kind` (DQS-18), and a `kind` with no
registered reader is a skip with the reason `kind not available`, counted like any other skip. The
CLI builds the router from the settings map and hands it to the scan as it hands the file reader
today (12.2). The file reader itself keeps its constructor and its behaviour (DQS-19): the router
builds it over the path map of the `file` entries. `run_scan`, the rule door, and the score write
change no line (DQS-11).

**Reason.** DQS-11 says a new reader adds no step to the scan. The scan already reads through a
one-method seam, so the only place a kind can be answered is the object that owns the map. The
router is that object, and the unknown-`kind` skip keeps the umbrella's refusal rule (DQS-13): a
job that carries a configuration for a reader it does not have still scans everything else and
says the reason out loud. Registering a kind's config schema (settings) and its reader (router) in
two small tables is the whole contract a later increment adds to.

**Alternatives.** Change the seam to take a `Source` object per read: the scan passes the source
it looked up, which moves the kind choice into the scan — DQS-11's exact prohibition — and forces
the file reader's five unit pairs to rewrite for no behaviour change. Choose the reader inside
`FileReader`: a reader named for one format must not answer for others. Have the scan hold a list
of readers and ask each in turn: a dataset then answers twice (skip reason of a reader that was
never its source), and the map's single authority (DQS-12) is lost.

**Consequences.** The e2e builds the router instead of the file reader, so the five 12.2 proofs
exercise the real wiring (DQS-19's floor). A dataset un-named in the map keeps the reason
`no source configured`, and a `file` dataset whose path is gone keeps `no readable file` — the
reasons the 12.2 pairs assert. The CLI's reader line is the one wiring change. A future increment
adds a kind to the two tables and nothing else.

### DD-464. A source names its dataset inside the entry, by qualified name or by guid

- **Status:** Proposed
- **Increment:** 12.4a
- **Date:** 2026-11-10

**Decision.** `SOURCES` is a JSON array of source objects (DQS-17). Each source carries its
catalogue dataset inside the entry, as `dataset`: one object with `qualifiedName` or `guid`,
exactly one of the two (DQS-20). The router answers a guid source for the dataset whose guid
matches, and a name source for the dataset whose qualified name matches. When the same dataset
has a guid source and a name source, the guid source answers — the stable identity wins. Two
sources naming the same dataset (the same guid, or the same name) is a settings error, because
the router would then hold two answers for one dataset. The seam's `skip_reason` grows the guid
beside the qualified name, so a guid source can answer why it skipped.

**Reason.** With the dataset as the map key, only a qualified name can name a dataset, and a
name is a label the catalogue's owner controls: a rename or a move of a table changes it, and
every `SOURCES` map then points at nothing while the scan reports the rows as missing. The guid
is the identity the catalogue never reissues, so a source keyed by guid survives a rename. The
dataset also belongs inside the entry: a map key can disagree with the entry it keys (a map of
`"/d3"` whose config is another table's), and an array of self-contained sources removes the
disagreement by construction.

**Alternatives.** Keep the map and allow a guid as a key too: the key then carries two kinds of
identity with no marker which is which, and the disagreement between key and entry stays
possible. Add a third map for guid sources: two sources of truth for one fact, DQS-12's shape to
avoid. Make `dataset` accept a list of names and guids in one entry: one source then answers for
two datasets with two lifecycles, and a skip reason cannot say which one failed.

**Consequences.** The envelope's JSON shape changes while 12.4a is still unshipped, so nothing
migrates. The settings error text names the array shape. A dataset with both source kinds is
answered by the guid source, and a scan notice says the skip reason of the source that answered.
`FileReader` keeps its name-keyed map — the router builds it from the name of each file source
and calls it with that name — so the reader's unit pairs stand (DQS-19). The seam's
`skip_reason` gains the guid argument, and the scan already holds both on the dataset ref.
