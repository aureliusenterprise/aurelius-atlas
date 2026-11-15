# 16.1 The view shape: the card and the view

- **Status:** in progress
- **Pull request:** [#357](https://github.com/aureliusenterprise/aurelius-atlas/pull/357)
- **Records:** ADR 064; DD-580 to DD-583 (here); relies on 14.2 (LAS-01..06, DD-498..501),
  14.5/14.6 (LAS-11..13, the score fields and the verdicts) and 11.3 (VEC-01..11)

## Scope

The one shape family ADR 064 gives the webapp. In `libs/python/aurelius-atlas-model`, a new
`views.py`:

- the **card**: what a result line, a chip and a badge need;
- the **view**: one entity as a screen needs it, the card extended with its own values, its
  related sections, and its quality detail;
- the derivation that fills both from what the store already holds: the entity's own fields and
  its derived App Search document of 14.2, with no new store reads beyond the entity document.

In `aurelius-atlas-core`, the derivation as one shared function the read doors, the write doors
and the search door (16.2, 16.3) all call.

Not delivered, with the increment that will:

| Not delivered                                                                                 | Lands with                           |
| --------------------------------------------------------------------------------------------- | ------------------------------------ |
| The per-rule governance verdicts (the box of 7.29 keeps its 12.7 live join until it switches) | the increment that switches that box |
| The endpoints that answer the shape                                                           | 16.2, 16.3                           |
| The webapp screens reading it                                                                 | 16.5                                 |
| The App Search wire's retirement                                                              | 16.6                                 |
| The facet request and answer models (the search door's, not the card's)                       | 16.2                                 |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AVS-01 | A card holds: `guid`, `typeName`, `superTypeNames`, `name`, `qualifiedName`, `displayText`, `definition`, `status`, `createTime`, `updateTime`, `createdBy`, `updatedBy`, `classificationNames`, `labels`, a breadcrumb of `{guid, name, typeName}` crumbs top-down, one `quality` entry per dimension and overall (score, count, total, rule GUIDs), and `governed`: whether the entity has governance verdicts (DD-535's document mark) |
| AVS-02 | The card's derived fields come from the stored App Search document: the breadcrumb arrays become crumbs in their stored order, and each `derived<field>` pair becomes a `relations` entry `{attribute, entities: [{guid, name}]}` in 14.2's RELATION_FIELDS order. An entity without a stored document has an empty breadcrumb, relations and quality, and `governed` absent                                                              |
| AVS-03 | `displayText` is the name, or the qualified name when there is no name                                                                                                                                                                                                                                                                                                                                                                    |
| AVS-04 | A view is a card plus: `attributes` (the entity's own attribute values as stored), `businessMetadata`, and `sections`: one list keyed by attribute, merging the entity's own relationship ends (`{guid, name, typeName, status}` as 2.3 reads them) with the stored `relations` pairs (`{guid, name}`; `typeName` and `status` absent where only a pair exists), each end once                                                            |
| AVS-05 | Both models serialize like every Atlas model: camelCase aliases and no null keys (`AtlasModel.to_json`)                                                                                                                                                                                                                                                                                                                                   |
| AVS-06 | A card or view states its freshness: `stale` is the stored document's stale flag (ASU-01), and `updateTime` is the entity's. The shape carries no other freshness claim                                                                                                                                                                                                                                                                   |
| AVS-07 | The models live in `aurelius_atlas_model.views`, so the server, the Python client and the hand-mirrored Angular models share one definition of the fields                                                                                                                                                                                                                                                                                 |
| AVS-08 | The derivation of one entity's view reads the entity document only. It computes nothing a worker computes (no parent walk, no relation join): those live in the stored document                                                                                                                                                                                                                                                           |
| AVS-09 | No answer of Apache Atlas's API and no App Search answer changes                                                                                                                                                                                                                                                                                                                                                                          |

## Aurelius origin

- ADR 064: the one-shape decision and its three doors.
- `apps/aurelius-atlas-webapp` today: the card covers what a results card and a detail chip
  render (7.4a, 7.21a); the view covers what `getEntityByGuid` plus the typedef walk plus the
  bulk resolves plus the gov-quality join assemble (7.20, 7.21a, 7.29).
- 14.2's `StoredAppSearch` and 14.5's totals: the source fields, with the legacy engine names
  renamed to the view's camelCase names.

## Deviations

None against Apache Atlas (AVS-09). The shape is an Aurelius-native surface; the Atlas wire is
untouched. The relation-name pairs carry the 14.2 rule that a deleted end keeps its GUID and
loses its name (ASU-02): the view shows the name as none, and the read door of 16.2 decides
which ends it answers.

## Acceptance

- `libs/python/aurelius-atlas-model/tests/test__views.py`: the field sets (AVS-01, AVS-04,
  AVS-05), the card's projection of a view (AVS-04), the displayText default and the freshness
  fields (AVS-03, AVS-06), and the models' module (AVS-07).
- `libs/python/aurelius-atlas-core/tests/test__view_derivation.py`: the shared derivation —
  a stored document's crumbs, pairs and business metadata; no document; the displayText
  fallback; the quality entries; the stale mark; the section merge; the attached names
  (AVS-01..04, AVS-06, AVS-08) — and every indexed document of the sample catalogue derived
  from its own document alone (AVS-02, AVS-08).
- AVS-09, like ASE-12 before it: the existing suites are its proof — nothing here is imported
  by an Atlas or App Search answer.
- Trace: every other rule id is named by a test with `@pytest.mark.covers(..., rules=[...])`
  (ADR 056).
