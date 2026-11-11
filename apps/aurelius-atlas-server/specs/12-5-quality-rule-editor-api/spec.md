# 12.5 The rule vocabulary endpoint

- **Status:** in progress
- **Pull request:** — (this increment's PR)
- **Records:** adds QRE-01..05 and DD-473/474 (here); relies on DQ-01..03/DQ-07 (12.1, the
  vocabulary and its parser), DD-440 (the `/api/aurelius/v1` precedent), ADR 046 (Atlas's own
  API stands), AUZ (6.2, the signed-in posture of the Aurelius endpoints), and ADR 051.

## Scope

The webapp will let a user author a quality rule (7.27). The browser needs the rule vocabulary
that today lives only in Python: the ten check kinds, their dimensions, and their parameters
(12.1's `aurelius_atlas_quality.rule`). It also needs to know, before it saves, whether the rule
it built is one the scanner can read (DQS-08 marks an unreadable rule ERROR).

Delivered here:

- `GET /api/aurelius/v1/quality/kinds`: the engine's closed vocabulary as a resource, answered
  from `KINDS` at request time (DD-473).
- `POST /api/aurelius/v1/quality/rules/validate`: a stored-rule shape checked through the
  engine's own parser (QRE-02, DD-474). It reads no data and touches no store.
- in `apps/aurelius-atlas-server`: the router, the dependency on `aurelius-atlas-quality`, and
  the app wiring, following the 11.4 pattern (`routes/search_by_meaning.py`).

Explicitly not delivered here, with the increment that will:

| Not delivered                                             | Lands with        | Why                                                             |
| --------------------------------------------------------- | ----------------- | --------------------------------------------------------------- |
| The webapp's rule form and its save flow                  | 7.27              | The browser slice rides these two endpoints                     |
| A dry run: a rule evaluated over a dataset's real rows    | a later increment | It needs the 12.4 source readers and a server-side evaluation   |
| Any rule write surface                                    | stands as it is   | A rule saves through entity write REST (EWR) with `atlas-write` |
| Governance-quality rule verdicts (`m4i_gov_data_quality`) | later             | DV-67 stands: validate-entity is still the mock                 |

## Semantics

Python tests name the ids, the `@pytest.mark.covers(..., rules=["QRE-NN"])` convention (ADR 056).
The vocabulary content itself is 12.1's contract (DQ-01/DQ-02), cited here, not restated per
kind.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| QRE-01 | `GET /api/aurelius/v1/quality/kinds` answers 200 with the vocabulary the engine holds: `kinds`, one entry per check kind sorted by name, each `{name, dimension, required, optional, reason}` with the parameter lists as the `KINDS` map holds them. It also answers `castableTypes` (the names a `COLUMN_TYPE_CASTABLE` rule may name) and `thresholdMin` and `thresholdMax`. Nothing is hardcoded in the route besides the render (DD-473). |
| QRE-02 | `POST /api/aurelius/v1/quality/rules/validate` takes the stored-rule attribute shape of DQ-07: a JSON object holding the `dq`-prefixed attributes of patch `001-data_quality_vocabulary` (or a legacy `dataqualitytype`/`dataqualityoperator` pair), the `name`, and the `threshold`. A rule the vocabulary can read answers 200 `{valid: true, kind, dimension}` with the kind and dimension the engine parsed.                               |
| QRE-03 | A rule the vocabulary cannot read answers 200 `{valid: false, reason}` with the engine's own `QualityRuleError` text (an unknown kind, a missing or unknown parameter, a threshold outside the ratio). An unreadable rule is the product of the validation, not a rejected request (DD-474). A body that is not a JSON object answers 400 in Atlas's error shape. Validation reads no entity and no dataset.                                   |
| QRE-04 | Both endpoints require a signed-in user, as quick search does. They answer the same for every user: the vocabulary is the engine's, not the store's, and validation holds no entity. No new privilege enters the authorizer, and no write changes (EWR and `atlas-write` still gate the rule itself).                                                                                                                                          |
| QRE-05 | Apache Atlas's own endpoints answer as before (ADR 046). The new router rides the app's include list beside `SEARCH_BY_MEANING`, and the server gains its dependency on `aurelius-atlas-quality` (its `pyproject.toml` and the `implicitDependencies` in `project.json`).                                                                                                                                                                      |

## Aurelius origin

None of Apache Atlas, which has no rule engine (12.1). The legacy product's editor kept the
vocabulary in the browser as form fields with no API at all
(`apps/atlas/src/app/search/components/editor/gov-quality/**`). These endpoints exist so the new
editor reads one source of truth, the engine (DD-473).

## Deviations

Against Apache Atlas: none, the endpoints add a product surface Atlas does not have, under
`/api/aurelius/` like 11.4's searches (DD-440). Against the Aurelius product: none, and no new
`DV` entry. DV-146 already carries the closed-vocabulary decision.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_quality.py`: QRE-01..05 on the
  in-process app with the fake store, the 11.4 test file's fixture pattern. The QRE-01 test
  compares the answer against the imported `KINDS` map, and the QRE-02/03 tests pair each
  answer with a rule the engine parses or raises on.
  `uv run pytest apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_quality.py`.
- No e2e here by choice: the routes hold no store call, and 7.27's webapp e2e drives them
  through the served origin against the real server, so an e2e at this level would only re-prove
  the unit matrix.
