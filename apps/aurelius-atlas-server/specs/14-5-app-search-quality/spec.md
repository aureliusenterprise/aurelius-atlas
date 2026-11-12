# 14.5 The App Search API: `/data_quality` and the score roll-up

- **Status:** in progress
- **Pull request:** — (this increment's PR)
- **Records:** DD-528 to DD-532 (here), DV-159; relies on ADR 060, 14.1 (LAS-11, LAS-12), 14.2 (ASD-01),
  14.3 (ASU-06), 14.4 (ASE-01 to ASE-11) and 12.2 (the `m4i_dq_score` entities, DQS-06 to DQS-08)

## Scope

The original webapp reads data quality twice. A field's details page lists the field's quality results from
the `atlas-dev-quality` engine, which its reverse proxy reaches at `<base>/data_quality`. Every search page, card
and details page reads the score fields of `atlas-dev`, which 14.4 answers as 0. This increment fills both from
the score entities the quality scanner writes (12.2). In `aurelius-atlas-core`:

- the quality result of each score entity, and the score totals of each entity document, derived again in each
  round from the stored scores, rules and documents (`app_search_quality.py`);
- the engines as their documents and fields, `atlas-dev`'s score fields read from the totals and
  `atlas-dev-quality` from the results (`app_search_engine.py`);
- the listing of the scores and of the documents holding a result or totals (`entity_documents.py`).

In `aurelius-atlas-server`, `POST /api/as/v1/engines/atlas-dev-quality/search` and `.../search.json`
(`routes/app_search.py`), and the quality round in the App Search worker (`app_search.py`).

Not delivered, with the increment that will:

| Not delivered                                                                    | Lands with |
| -------------------------------------------------------------------------------- | ---------- |
| The `atlas-dev-gov-quality` engine (`/gov_quality`)                              | 14.6       |
| A deployment's route from the original webapp's `data_quality` to this endpoint  | none       |
| A score of a field on its own: the scanner scores a rule over a dataset (DQS-06) | none       |

The second row is the operator's, as 14.4's `elastic`; the server's README shows the route.

## Semantics

A score is an active `m4i_dq_score` entity with the verdict `PASS` or `FAIL`, a `score` and a `ruleGuid`: the
newest score of a rule over a dataset (DQS-06). ERROR findings and the datasets' `overall` summaries are not
scores here (DD-532). A rule is active when its entity is and its `active` attribute is not `false` (DQS-02).
A rule's fields in a dataset are the active `m4i_field` entities at the other end of the rule's active
relationships whose App Search document lists the dataset among its `deriveddatasetguid`, in the order the rule
lists its relationships.

The results of `atlas-dev-quality` (LAS-11, DD-528, DV-159):

| Field                             | Value                                                                                 |
| --------------------------------- | ------------------------------------------------------------------------------------- |
| `id`                              | the score entity's GUID                                                               |
| `guid`, `qualityguid`             | the rule's GUID                                                                       |
| `qualityqualifiedname`            | the rule's `qualifiedName`                                                            |
| `name`                            | the rule's `name`, else its `qualifiedName`                                           |
| `expression`                      | the rule's `expression`, else empty                                                   |
| `dataqualityruledescription`      | the rule's `ruleDescription`, else empty                                              |
| `dataqualityruledimension`        | the rule's `qualityDimension`, else empty                                             |
| `businessruleid`                  | the rule's `id` when a number, else 0                                                 |
| `fieldguid`, `fieldqualifiedname` | the GUIDs and qualified names of the rule's fields in the score's dataset             |
| `datadomainname`                  | the first data domain in the breadcrumbs of those fields' data attributes, else empty |
| `dqscore`                         | the score's `score`                                                                   |

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASQ-01 | `POST /api/as/v1/engines/atlas-dev-quality/search` and `.../search.json` answer as `atlas-dev`'s do (ASE-01, ASE-02): the user needs `ENTITY_READ`. `atlas-dev-gov-quality` answers 404 until 14.6                                                                                                                                                                        |
| ASQ-02 | `atlas-dev-quality` holds one result per score of an active rule with at least one field in the score's dataset, with the fields of the table above                                                                                                                                                                                                                       |
| ASQ-03 | `atlas-dev-quality` answers its requests as `atlas-dev` does (ASE-04 to ASE-11), over its own fields, with `meta.engine.name` and `_meta.engine` its name. Its text fields are those of the table but `dqscore` and `businessruleid`, which are numbers                                                                                                                   |
| ASQ-04 | On `atlas-dev`, LAS-12's totals hold, read from the results: a field's own totals add, per dimension (the result's `dataqualityruledimension` lowercased), each result naming it: its `dqscore` to the sum, 1 to the count, and the rule's GUID once to `qualityguid_<d>`. A result of another dimension adds to no total                                                 |
| ASQ-05 | A data attribute's own totals are the sums of those of the fields whose document lists it among its `deriveddataattributeguid`. Each field and data attribute adds its own sums and counts to every entity of its breadcrumb. `dqscoresum_overall` and `dqscorecnt_overall` add up the five dimensions; each `dqscore_*` is its sum over its count, 0 when the count is 0 |
| ASQ-06 | A document without a result in its totals answers 0 in each score field and `[]` in each `qualityguid_*`, and filters, facets and sorts on a score field take it as 0 (DD-530)                                                                                                                                                                                            |
| ASQ-07 | Each round of the App Search worker, after the documents, derives the results and totals again from the stored scores, rules and documents, writes each that changed and takes away each no longer held (DD-529). A write that meets a change in between waits for the next round                                                                                         |
| ASQ-08 | No answer of Apache Atlas's API changes                                                                                                                                                                                                                                                                                                                                   |

## Aurelius origin

From `aureliusenterprise/aurelius` at commit b057389:

- `backend/m4i-atlas-post-install/scripts/propagate_quality.py`: the roll-up, from the results to the fields,
  their data attributes and the breadcrumbs (ASQ-04, ASQ-05).
- `libs/atlas/api/src/lib/elastic/engines/data-quality-search.service.ts`: the result's fields the webapp reads
  (ASQ-02).
- `apps/atlas/src/app/search/details/field/data-quality-cards/data-quality-cards.component.ts`: the field page's
  request: a filter on `fieldguid`, a facet on `dataqualityruledimension`, sorts by `name`,
  `dataqualityruledimension` and `dqscore` (ASQ-03).
- `k8s/charts/reverse-proxy/conf.d/search-api.yaml`: `<base>/data_quality` reaching `atlas-dev-quality` (ASQ-01).

## Deviations

None against Apache Atlas (ASQ-08). Against the legacy engine,
[DV-159](../../../../docs/architecture/conversion/deviations.md): a result per score of a rule over a dataset,
under the score's GUID, listing the rule's fields in that dataset, where `atlas-dev-quality` held one per rule
under its qualified name with one field; and `name`, `businessruleid` and `datadomainname` from the rule and the
documents, where the legacy values came from a source the catalogue no longer holds (DD-485).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__app_search_quality.py`, on the fake client:
    - a result's fields from its score, rule, fields and their documents; no result for an ERROR, a summary, a
      deleted score, an inactive or deleted rule, or a dataset none of the rule's fields is in (ASQ-02);
    - the totals of a field, its data attribute and their breadcrumbs; the overall; another dimension (ASQ-04,
      ASQ-05);
    - a second round writes nothing; a changed score, a taken away score and a moved field show after a round
      (ASQ-07);
    - the sample catalogue imported and indexed, with a score for each of the legacy results: all 23 score
      fields and the rule GUIDs of all 684 `atlas-dev` documents as the legacy ones, but for the one inactive
      rule's result, which the 10 documents it reached hold no more (LAS-12, DD-532).
- `libs/python/aurelius-atlas-core/tests/test__app_search_engine.py`: the quality engine's fields, a field page's
  request, and the score fields of `atlas-dev` read, filtered, faceted and sorted with and without totals
  (ASQ-02, ASQ-03, ASQ-06).
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_app_search_engine.py`: both paths of the quality
  engine, the governance engine's 404 (ASQ-01); `test__aurelius_atlas_server_app_search.py`: a worker round runs
  the quality round after the documents (ASQ-07).
- `libs/python/aurelius-atlas-core/e2e/test__app_search_quality_e2e.py`, on the dev Elasticsearch: a rule
  over a field written by the writer, its score, both rounds, the field page's request and a domain's totals sorted
  (ASQ-02 to ASQ-05).
