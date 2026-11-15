# 12.7a The verdicts, scoped to the draft's type

- **Status:** in review
- **Pull request:** #370
- **Records:** adds VEV-07, VEV-08 (here) and DD-631..634 (here); amends VEV-01, VEV-02,
  VEV-03 (12.7, here) and EDT-24 (7.24, one-way description alias). Relies on LAS-13 and
  ASG-04 (the rule→type join and the relationship reading of 14.6), and on DET-42 (the
  details box, which already asks the store for the type's own rules).

## Scope

12.7 connected the editor banner to the catalogue's governance rules. It ran every ACTIVE
rule in the catalogue over every draft. That is wrong wherever a store holds rules for more
than one type, and the dev store does: the m4i sample corpus carries 95 rules over ten
types. A rule for `m4i_system` says "This entity is missing a kibanaSpace", and the banner
painted that line under the Name control of a dataset, because the rule measured a `name`
and the dataset's control is named `name`. The product already owns the join: LAS-13 and
ASG-02 state that a rule is for the type its qualified name names before the first `--`,
the server's 14.6 verdict engine scopes every rule by it, and the details box (DET-42)
searches only the opened type's rules. Only the editor path skipped it.

Two smaller misses ride the same symptom. A rule over a relationship attribute (`fields`,
`owner`) could never see a value, because the draft carries its picks under
`relationshipAttributes` and the app read only `attributes`, so the line under that picker
was always a warning. And the banner's description alias ran both ways in code, where the
spec states one direction.

Delivered here:

| Module                                    | Holds                                                        |
| ----------------------------------------- | ------------------------------------------------------------ |
| `aurelius_atlas_validate_entity.models`   | the draft grows `typeName` and `relationshipAttributes`      |
| `aurelius_atlas_validate_entity.verdicts` | the type join on the rule's qualified name, the draft record |
| `aurelius_atlas_validate_entity/routes`   | the draft model passes whole to the engine                   |
| `aurelius-atlas-webapp` editor            | the description alias becomes one-way (EDT-24 amended)       |

Explicitly not delivered, with the increment that will:

| Not delivered                                                  | Lands with                 | Why                                                                                                                                                                                                           |
| -------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A rule→type attribute on the rule type                         | none                       | LAS-13's qualified-name prefix is the product's join, kept                                                                                                                                                    |
| Server-side verdicts written when an entity saves              | 12.8 (planned)             | Unchanged                                                                                                                                                                                                     |
| The same empty-relationship reading for stored entities (14.6) | a parity-checked follow-up | ASG-04's `[]`-present reading is frozen by DD-536's 1,612-verdict parity corpus; the draft path (this increment) is where the editor and details box answer, so the honest reading ships there first (DD-634) |

## Semantics

Python tests name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056). The
reference is the Aurelius source (ADR 052), as in 12.7.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VEV-07 | A governance rule is for the entity type its `qualifiedName` names before the first `--` (LAS-13): `m4i_dataset--name` is for `m4i_dataset`. The draft is judged by the rules of its own `typeName`, and by no others. A rule whose qualified name holds no such prefix is for no type and answers nothing at all: no verdict, no unread entry. A draft with no `typeName` is judged by nothing. The rule search asks `qualifiedName` beside its attributes (VEV-03 amended).                                                                                                                                                                                                     |
| VEV-08 | The draft's `relationshipAttributes` ride the record the check reads, as 14.6's ASG-04 reads them for a stored entity: a JSON list of entries holds content by its length and a single entry object holds content. An empty relationship — `[]`, a wrapped `{"raw": []}`, or a `null` (a cleared or untouched picker) — carries no value at all: a presence rule over it misses, never a false warning (DD-634). A value stored in the webapp's `{"raw": x}` wrapper reads as `x` (DV-132's door), for attributes and relationship values alike (VEV-01 amended: the draft's `attributes`, `typeName` and `relationshipAttributes` are read, the rest of the body stays ignored). |

VEV-02 as amended: one ACTIVE rule of the draft's type answers one verdict, and the
`unreadRules` of a call hold only the unread rules of the draft's type (VEV-03 amended).
The cache of VEV-05 still holds the one whole read, and the type filter runs per call on
it. EDT-24 as amended: the drawer shows a verdict under the control the verdict's attribute
names, and a `definition` verdict names the `description` control one way (the legacy's
alias direction, DD-633). A `description` verdict names only its own control.

## Aurelius origin

- `libs/m4i-flink-tasks/m4i_flink_tasks/operations/get_rules/get_rules.py` — the job judged
  each entity by the rules of its type (LAS-13's join, restated by ASG-02).
- `libs/m4i-data-management/.../core/quality/rules/...` and 14.6's ASG-04/DD-536 — the
  relationship reading this port applies to the draft.
- `apps/atlas/src/app/search/components/editor/services/editor-gov-quality-search.service.ts`
  — the legacy editor's search, scoped like the details box's.
- `apps/atlas/src/app/search/components/editor/components/gov-quality-display/` — the card
  key `definition` displayed under the Description control, one way (the alias direction
  DD-633 restores).

## Deviations

None new. This increment narrows the gap 12.7 left open; DV-153's meaning stands (the
answer is Aurelius's own shape), and no wire shape changes: a draft already carried
`typeName` and `relationshipAttributes` before this increment, and the answer keeps its
verdict fields.

## Acceptance

Unit (`uv run pytest apps/aurelius-atlas-validate-entity/tests`), on the fake catalogue:

| Proves    | File                                                              |
| --------- | ----------------------------------------------------------------- |
| VEV-07    | `tests/test__verdicts.py` (the join, the foreign silence, unread) |
| VEV-07/08 | `tests/test__aurelius_atlas_validate_entity_app.py` (the route)   |
| VEV-08    | `tests/test__verdicts.py` (the record the check reads)            |

Scenarios: `scenarios/validation/verdicts.scenario.yaml` grows — the corpus rules gain
their qualified names, one stage answers a draft whose picks land the `fields` verdict
(VEV-08), a foreign type's rule answers nothing (VEV-07), and the sample corpus's own
`completeness('childDataset')` record answers its refusal line for a picker holding
nothing and its compliant line only once a child is picked (VEV-08, DD-634).

Webapp unit: `entity-editor.component.spec.ts` (the one-way alias, a line under a
relationship picker). Run `nx test aurelius-atlas-webapp -c ci`.

E2E: this app's suite seeds a foreign type's rule and asserts its silence (VEV-07),
lands a relationship rule with the draft's picks (VEV-08), and seeds a presence rule
over a relationship to prove an empty picker answers its refusal line live (VEV-08,
DD-634). The webapp suite seeds its
banner rules under `DataSet--` and asserts a foreign type's line is nowhere in the drawer.
Level 1 + 2.
