# 12.9 The demo corpus ships per-field quality scores

- **Status:** in review
- **Pull request:** #461
- **Records:** adds DD-858, DD-859 and DV-206; amends nothing on the wire.
  Relies on DQS-06/DQS-07 (12.2, the score entity and its key), ASQ-02/ASQ-04/
  ASQ-05/ASQ-07 (14.5, the results and the roll-up), LAS-01 (14.1, `m4i_dq_score`
  has no document, DD-500), and DET-56/DET-58/DET-59/DET-60 (7.25c, the score
  surfaces).

## Scope

The demo catalogue shows no data quality scores. The details pages, the stats
bar and the score sorts are built (7.25c) and the worker rolls scores up the
hierarchy (14.5, ASQ-04/ASQ-05), but every screen answers `Unavailable`. The
sample corpus ships 50 data quality rules and no `m4i_dq_score` entity, so there
is nothing to roll up. The legacy deployment measured one score per rule and
dataset, and an averaging job carried those field scores up to the data
attribute, dataset, collection, system and domain. Aurelius has both halves. It
has no scores to feed them.

This increment ships the scores the legacy deployment measured. The frozen
legacy quality engine holds 42 result rows, one per rule, over 25 fields of two
datasets (the fixture `legacy-app-search-atlas-dev-quality.json`, 14.1). The
corpus already holds the 42 rules, the 25 fields and both datasets. This
increment bakes one `m4i_dq_score` entity per row into `sample_data.zip`, keyed
as 12.2 keys one, with the row's score. No code changes: 14.5's quality round
derives each score's result, and ASQ-04/ASQ-05 add those results up per field
and every entity of their breadcrumb. The numbers on screen then reproduce the
frozen legacy documents (14.1's oracle) on the demo store.

Delivered here:

| Module                                      | Holds                                               |
| ------------------------------------------- | --------------------------------------------------- |
| `data/atlas-sample/sample_data.zip`         | the 42 `m4i_dq_score` records, and the export order |
| `tests/test__legacy_app_search_fixtures.py` | the without-a-document count, 3 sources + 42 scores |
| `tests/test__app_search_quality.py`         | the roll-up gate reads the shipped scores           |
| `tests/test__app_search_indexer.py`         | the no-document gate counts the shipped scores      |
| `tests/test__view_search.py`                | the door's entity counts gain the 42 scores         |

Explicitly not delivered, with the increment that will:

| Not delivered                                    | Lands with       | Why                                                                                                         |
| ------------------------------------------------ | ---------------- | ----------------------------------------------------------------------------------------------------------- |
| Scores on the results cards                      | 7.25d (approved) | the mount site of the card block is 7.25d's flip of DET-61; the scores land ready for it                    |
| Scores in `only_gov_quality.zip` and `small.zip` | none             | those bundles ship governance rules or a mini catalogue; neither carries a `m4i_data_quality` rule to score |
| A scan over the demo store                       | none             | the scanner runs on a schedule (12.3) and reads a source; the demo store has no extract to measure          |

## Semantics

No new rule id. The shipped records are ordinary score entities of the type the
scanner writes, and the behaviour they reach is stated where it already lives:

- Each record is one score entity of `m4i_dq_score` with a `scoreKey` of
  `{datasetGuid}/{ruleGuid}` and a `qualifiedName` of
  `dq-score/{scoreKey}`, the scanner's own shape (DQS-06, DQS-07, DD-456).
- Each record carries `verdict: PASS` and the legacy row's `score`, so
  `_scored` reads it (ASQ-02, DD-532). The one row of the inactive rule keeps
  its score and stays without a result, because its rule answers nothing
  (DD-532). It stays in the corpus for that reason.
- The score's `datasetGuid` is the dataset of the row's field (its one
  `datasets` end). This is the dataset the frozen oracle names for the field
  (`deriveddatasetguid`), and it is what makes ASQ-02's "at least one field in
  the score's dataset" hold.
- The score's `dimension` is the rule's `qualityDimension`. ASQ-04 reads the
  dimension off the result and the result off the rule, so the field is the
  source of truth and the copy on the score is the scanner's (DQS-07).
- The score entities get no App Search document (LAS-01, DD-500), so the
  document count of 14.x stays as it is. Their results reach the fields, their
  data attributes and every breadcrumb entity (ASQ-04, ASQ-05), which the 7.25c
  screens read (DET-56, DET-58, DET-59, DET-60).

## Aurelius origin

- `libs/python/aurelius-atlas-core/tests/fixtures/legacy-app-search-atlas-dev-quality.json`
  — the 42 result rows of the frozen legacy quality engine, one per rule, each
  naming its rule, field, dimension and score. This is the source of every value
  baked here. The rows' `dqscore` is the legacy scan's own number.
- `libs/python/aurelius-atlas-core/tests/fixtures/legacy-app-search-atlas-dev.json`
  — the frozen legacy documents: the rolled-up `dqscore_*` fields of 81 of the
  sample's documents (25 fields, 40 data attributes, datasets, collections,
  systems, data entities, domains) that this increment lets the new app
  reproduce.
- `apps/aurelius-atlas-quality-scanner/aurelius_atlas_quality_scanner/records.py`
  — `score_key` and `score_entity`: the key, the qualified name and the
  attribute set the shipped records copy.
- `libs/python/aurelius-atlas-core/aurelius_atlas_core/app_search_quality.py`
  — `QualityIndexer`: the roll-up that needs no change.

## Deviations

DV-206 records the one deliberate difference from the scanner's live output: the
shipped records carry a fixed `runId` and `runAtMs`, and only the five attributes
the roll-up and the 7.25c screens read carry the legacy row's values
(`verdict`, `score`, `ruleGuid`, `datasetGuid`, `dimension`). A real scan also
fills `checkKind`, `passed`, `rowsChecked` and `rowsFailed`. Those four feed
nothing on the read path (ASQ-02 reads the verdict, score and rule; ASQ-04 reads
the result), so the demo records leave them out rather than invent row counts
the corpus never measured. DV-206 also records the closer-to-oracle move: the
demo store now carries the scores the frozen oracle was made from.

## Acceptance

- `uv run pytest libs/python/aurelius-atlas-core/tests/test__app_search_quality.py`
  (ASQ-04, ASQ-05, DD-532): the roll-up gate stops synthesizing scores and reads
  the 42 shipped ones. The comparison over all 23 score fields of the 654
  oracle documents, the `len(totals) == 654` and the inactive rule's
  `reached (10, 12)` all still hold (DV-185, DV-195). The gate now proves the
  shipped records reproduce the oracle, not only that the indexer does.
- `uv run pytest libs/python/aurelius-atlas-core/tests/test__legacy_app_search_fixtures.py`
  (LAS-01): the set of corpus entities without a document grows from the 3
  `m4i_source` entities to 45, the same 3 plus the 42 `m4i_dq_score` entities.
  The fixture gate's other counts do not move (the document set is unchanged).
- `uv run pytest libs/python/aurelius-atlas-core/tests/test__app_search_indexer.py`
  (LAS-01, ASD-04): the gate that names the entities without a document grows
  its set from `m4i_source` to `m4i_source` and `m4i_dq_score`. The written
  count stays 654 (DD-500).
- `uv run pytest libs/python/aurelius-atlas-core/tests/test__view_search.py`
  (AVR-11): the door's unfiltered total grows from 657 to 699, the shipped
  scores counted by their type beside the three sources. The 14.4 engine's
  count stays 654.
- `uv run pytest libs/python/aurelius-atlas-core/tests/test__app_search_engine.py`
  and `test__app_search_governance.py` (14.x): unchanged. The score entities
  hold no document and no governance verdict.
- `nx e2e aurelius-atlas-webapp` (DET-56, DET-58, DET-61): the 7.25c quality
  scenario is unchanged. Its stack seeds its score source by hand and starts
  from an empty store, so it never reads the shipped corpus (7.25c's note).
- By hand, on the dev stack: re-import `sample_data.zip` over the running store
  with the writer token (`POST /api/atlas/admin/import`), let the worker's rounds
  drain, and open the field `f86b18e1-7a20-4ba1-a616-09bac4b96a3b`
  (`FUNC_ORGANIZATION`). Its Data Quality box lists the accuracy rule at 89% and
  its stats bar's Data Quality stat reads the percent, not `Unavailable`. Its
  data attributes and the dataset above them carry rolled-up totals, and the ES
  documents of the 81 oracle documents carry a non-zero `quality_totals`.
