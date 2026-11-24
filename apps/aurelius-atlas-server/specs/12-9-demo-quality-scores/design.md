# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design
log apply: an accepted entry is never edited except its status line, and a changed
decision is a new entry that supersedes the old one.

## Entries

### DD-858. The demo scores ship as baked score entities, not as a scan

- **Status:** Proposed
- **Increment:** 12.9
- **Date:** 2026-11-24
- **Supersedes:** none; follows DD-456 (Proposed, 12.2, the score entity and its
  unique key) and DD-635/DD-638 (Proposed, 12.7b/12.7d, the sample corpus edited
  as data)

**Decision.** `sample_data.zip` gains 42 `m4i_dq_score` entities, one per row of
the frozen legacy quality fixture
(`legacy-app-search-atlas-dev-quality.json`). Each copies the scanner's record
shape (`records.py`): `scoreKey` `{datasetGuid}/{ruleGuid}`, `qualifiedName`
`dq-score/{scoreKey}`, the rule's `dimension`, the row's `dqscore`, `verdict:
PASS`, and the field's dataset as `datasetGuid`. Every other entry of the zip is
copied byte for byte. `atlas-export-order.json` gains the 42 GUIDs after the 657
entity GUIDs it already lists. The `m4i_dq_score` type definition is not added to
the zip's `atlas-typesdef.json`: the server loads it from `m4i_models/0011` at
start (ADR 058), like every other m4i type. `only_gov_quality.zip` and
`small.zip` are untouched.

**Reason.** The roll-up half of the feature is already ported and proven. The
`QualityIndexer` (14.5, ASQ-04/ASQ-05) derives results from stored scores and
adds them up per field, data attribute and breadcrumb, and the frozen oracle
already carries the rolled-up numbers on 81 documents. The only missing piece is
score data in the demo store. Baking the entities is the smallest change that
fills it, and it keeps the increment data-only, like the 12.7b/e/g corpus edits
(DD-635, DD-639, DD-844).

The 42 values are not invented. The fixture is the legacy quality engine's own
recording of the same corpus, and the existing gate
`test__the_sample_s_scores_roll_up_as_atlas_dev_s_but_the_inactive_rule_s`
(DV-185, DV-195) already proves that scores with exactly these rule GUIDs and
these numbers, keyed to `deriveddatasetguid[0]` of each field, roll up to the
oracle's numbers on all 654 documents. Baking turns that synthesized proof into a
stored one. The audit of the 42 rows joins the corpus on every side: 42 distinct
rules (one of them the corpus's inactive rule, which keeps proving DD-532 on the
demo store), 25 fields, 2 datasets, and every field's one `datasets` end equals
the oracle's `deriveddatasetguid[0]`.

A scan is the wrong instrument for the demo data. The scanner (12.2, 12.3) reads
a real extract of a source; the demo store has no extract behind its 22 datasets,
so a run scores nothing or invents a fake table per dataset. The legacy scores
came from the legacy scanner over the legacy extracts, and the recording in the
fixture is what survives of it.

The entities ride the export order because `ZipSource` imports exactly what
`atlas-export-order.json` lists. A score holds no relationship, so its order
position is free, and appending keeps the 657 existing lines byte-identical.
Appending is also what makes the dev store converge: the import reconciles over
a running store, and the scoreKey upsert (DD-456, EWR-05/EWR-06) means a repeated
demo re-import updates the same 42 entities in place.

**Alternatives considered.**

Synthesize the scores at server start for the demo realm (refused: a hidden
writer of store data that no export, audit or import path explains, and it forks
"the demo corpus" from "what the demo store holds"). Run the quality scanner on
the dev stack and fake source extracts (refused: needs 22 fake extracts and a
running Kafka/schedule path for demo cosmetics, and the numbers would be a scan
of invented data, further from the oracle than the fixture's own values). Ship a
second, scores-only bundle and make the demo tenant import two bundles (refused:
the tenant seeding command takes one sample, TAD-13, and the split serves no
other tenant). Add the scores to every bundle (refused: `only_gov_quality.zip`
ships governance rules, which are a different type with no `m4i_data_quality`
rule to score, and `small.zip` is a 12-entity smoke catalogue).

**Consequences.** The demo store's 42 scores reproduce the oracle exactly (14.1's
reference set): the same 81 documents gain non-zero totals, and the field/dataset
pairing the gate chose becomes stored fact. The 7.25c screens light up from real
data, and 7.25d's results-card flip finds scores ready to render. Four gates
move, all named in the spec: the fixtures gate counts 45 entities without a
document (3 sources + 42 scores), the indexer gate grows its no-document type
set the same way, the roll-up gate reads the shipped scores instead of
synthesizing 42 (its `score-{index}` fixtures go away), and the trace markers
name the shipped path. The engine and governance gates hold at 654 documents:
LAS-01/DD-500 keeps a score out of App Search, so nothing else in 14.x sees the
new entities.

### DD-859. The baked scores carry only the attributes the read path consumes

- **Status:** Proposed
- **Increment:** 12.9
- **Date:** 2026-11-24
- **Supersedes:** none; follows DD-858 (Proposed, 12.9, the baked scores)

**Decision.** Each baked record fills `verdict`, `score`, `ruleGuid`,
`datasetGuid` and `dimension` from the fixture row, and fixes `runId` to
`demo-sample-1` and `runAtMs` to the export's own timestamp base. It leaves
`checkKind`, `passed`, `rowsChecked`, `rowsFailed` and `errorMessage` unset. The
fixture row carries none of those five.

**Reason.** The type makes all but `scoreKey` optional, so a partial record is a
valid score entity. The read path consumes exactly the five filled attributes:
`_scored` reads `verdict`, `score` and `ruleGuid` (ASQ-02, DD-532), the result
builder reads the rule's dimension, and `dimension` on the score is the scanner's
own copy of the rule's (DQS-07). `checkKind` and the row counts exist to explain
a scan to an operator; the demo's numbers come from the legacy recording, which
never measured rows, so filling them means inventing facts. DV-206 records the
shrink. A scanner that later scores the demo store for real updates the same
entity by its key (DD-456) and writes the full record, so nothing blocks the
honest path.

**Alternatives considered.**

Invent row counts and a check kind (refused: invented facts on the one surface a
user reads as measurement, and none of it is read back). Fill `passed` from the
verdict (refused on its own: `passed` is the scanner's input to the verdict, not
a second copy of it, and the roll-up ignores it; it can ride a later real scan).
Drop `dimension` (refused: DQS-07's record carries it, and leaving it out makes
the demo entities a shape no scanner writes, which future gates would have to
special-case).

**Consequences.** The demo scores are visibly partial to anyone who opens a score
entity (`runId` names them). DV-206 states the boundary, so a parity check of a
live scan against demo data compares the five shared attributes and ignores the
five empty ones.
