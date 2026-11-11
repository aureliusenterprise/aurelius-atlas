# 7.27 The rules editor

- **Status:** in progress
- **Pull request:** — (this increment's PR)
- **Records:** adds EDT-25..30, DET-37, and DD-475..477 (here), and DV-148 to
  [deviations](../../../../docs/architecture/conversion/deviations.md) in the implementation
  PR; relies on EDT-01..12/DD-322..337 (the drawer), EDT-13..17/DD-338..341 (the relationship
  picker), DET-35/36/DD-444 (the field's rules box), APC/DD-140 (data-access HTTP),
  DD-324/DD-330 (the write gate and the create route), QRE-01..04/DD-473/474 (12.5, the
  endpoints this rides), UIC-36..39 (7.24's dumb quality components, untouched here), and
  ADR 053/056.

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01 to WBP-07
this slice inherits and its Acceptance repeats.

## Scope

The legacy editor dispatched `m4i_data_quality` to a type-specific form with free-text fields
(`editors-by-type.ts`, `gov-quality/gov-quality-editor.component.*`): a `ruleType`, a typed
dimension, and a `expression` the engine ran. Aurelius Atlas stores a rule as a check kind from
the closed vocabulary and its `dq`-prefixed parameters (DQ-01, DV-146), and its generic drawer
(7.7a) draws that type as raw attributes: nothing stops a user from storing a kind the engine
rejects, which the scanner then marks ERROR (DQS-08) — a rule that silently never runs.

Delivered here:

- the drawer's **quality mode** (EDT-25..29): when the editor's type is `m4i_data_quality`, the
  form is the vocabulary, not the attribute list. A kind picker fed by 12.5's kinds resource
  drives parameter controls for that kind only, the dimension shows as the kind's own, and the
  save validates through 12.5's validate endpoint before the entity POST (DD-475, DD-476).
- the **create and edit doors** (EDT-30, DET-37): a `+` in the field page's Data Quality Rules
  box header (DET-35's box), gated like the pencil (`canWriteEntities`), opening the existing
  create route with the type fixed to `m4i_data_quality` and the open field prefilled in the
  rule's `fields` picker; a rule row of that box opens the drawer to edit it, as every DET
  section row already does.
- the `QualityRuleService` client in `aurelius-atlas-data-access` for the two 12.5 routes (the
  `SearchByMeaningService` shape, `/api/aurelius/` beside Atlas's).

Explicitly not delivered here, with the increment that will:

| Not delivered                                                | Lands with        | Why                                                                |
| ------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------ |
| A dry run of a rule over a dataset's rows                    | a later increment | Needs 12.4's source readers and a server-side evaluation surface   |
| Deleting a rule                                              | 7.9               | The delete flow is 7.9's, for every type                           |
| Editing `m4i_gov_data_quality` rules                         | later             | The validate-entity backend is still the mock (DV-67)              |
| Scores on the form (the rule's current score)                | 7.25              | The scores surface is 7.25's (DD-369)                              |
| A type picker preseeded on `m4i_data_quality` from elsewhere | stands as it is   | The `+` of the rules box is the door; EDT-04's picker is unchanged |

## Semantics

TS tests name the ids in the test name (the 7.21a convention). The vocabulary and the validate
contract are 12.5's (QRE-01/02) and 12.1's (DQ-01/07), cited here, never restated as a TS table.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDT-25 | The drawer renders the quality form in place of the generic attribute form when its type is `m4i_data_quality` and the rule is a vocabulary one (EDT-29's seam): create mode always, edit mode when the entity names a `dqcheckkind`. The form is a kind Select over 12.5's `kinds` (each labelled by its name, ordered as the answer orders them), the kind's dimension shown as read-only text, and one control per required and optional parameter of the chosen kind, in the order the resource lists them. Before the create mode's first pick the form shows the kind Select over the shared fields only. Kinds load once per drawer (the service caches); while they load the form shows the drawer's loading line. |
| EDT-26 | A parameter control rides its stored attribute (patch `001-data_quality_vocabulary`): `column`→`dqcolumn`, `pattern`→`dqpattern`, `values`→`dqvalues` (chips), `columns`/`otherColumn`/`type`→ their `dq` names, `min`/`max`/`maxAgeHours`→ number, `minColumns`→ whole number. The editor writes no `dq` attribute the chosen kind does not name; a kind switch clears the parameters of the old kind (the same clear EDT-04's type switch does). The `type` control is a Select over the resource's `castableTypes`.                                                                                                                                                                                                     |
| EDT-27 | The quality form carries the shared fields (name, description as EDT-03/EDT-11 has them), the `active` checkbox (the stored `active`, seeded from the entity, default checked on create), and the `threshold` number input (0..1, empty means the engine's default 1.0). The form keeps the rule's other stored attributes out of the save body: quality-mode saves send name, description, `active`, `threshold`, the kind's `dq` parameters, and `dqcheckkind`.                                                                                                                                                                                                                                                          |
| EDT-28 | The quality-mode Save calls 12.5's validate with the draft's stored-rule shape first (DD-474). `{valid: true}` continues with the EDT-06 save unchanged (the POST, the classifications diff, the landing on details). `{valid: false}` renders the `reason` as the drawer's error line (EDT-07's notification place) and does not POST; a later edit clears the line. A validate call that fails on transport or a non-2xx answers the same line with the generic "could not check" text — a rule never saves unchecked.                                                                                                                                                                                                   |
| EDT-29 | The quality form seeds from the entity like EDT-02 does: an existing rule opens with its kind, its parameters under the controls EDT-26 names, its `active` and `threshold`. A legacy rule (no `dqcheckkind`, the DQ-07 pair) opens in the generic form: the quality form offers only kinds, and the pair map is the engine's (DD-477). Its Save rides EDT-23's governance banner and EWR as before, unchecked — a legacy rule stays readable by the scanner through DQ-07, and its re-authoring into the vocabulary is a human choice into the kind form, not a forced rewrite. The `expression` attribute of such a rule passes through the save untouched (EDT-27's body rule applies to quality-mode saves only).      |
| EDT-30 | `QualityRuleService.kinds()` answers the kinds resource and `validateRule(attributes)` the validate answer (QRE-01/02's shapes), through `API_BASE_URL` and the bearer interceptor (APC). The service is the only caller of the two routes; the drawer never fetches them itself. The kinds answer is cached in the service after its first success (EDT-25's "once").                                                                                                                                                                                                                                                                                                                                                     |
| DET-37 | The `related-rules` box header (DET-35) gains a `+` when `canWriteEntities` is true (EDT-08's gate, the same posture as the pencil). It opens the drawer at `create` with the type fixed to `m4i_data_quality` (DD-330's route, no type picker round), and seeds the `fields` relationship picker with the open field (EDT-13's pick shape). A user without `atlas-write` sees no `+`. The box's rows, search, sort, and paging (DET-17..22) are unchanged.                                                                                                                                                                                                                                                                |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
cited by path:

- `apps/atlas/src/app/search/components/editor/editors-by-type.ts` — the dispatch EDT-25
  replaces: `m4i_data_quality` (and `m4i_gov_data_quality`) to one hand-written component.
  Aurelius Atlas keys the mode off the same type name, in the one drawer.
- `apps/atlas/src/app/search/components/editor/gov-quality/gov-quality-editor.component.{ts,html}` —
  the fields the quality form replaces: its `name`, required `expression`, typed-dimension and
  free `ruleType` inputs, and its U+2019 quotation-mark warnings (kept: EDT-28's engine accepts
  the name, and the legacy's name warning rides the catalogue keys, DV-148). The `expression`
  control is gone with DV-146's closed vocabulary.
- `apps/atlas/proxy.conf.json` and the legacy create door (the drawer opened over a type pick) —
  what DET-37's `+` replaces with the box-scoped door.

## Deviations

Against Apache Atlas: none, Atlas has no rule editor. Against the Aurelius product, added to
[deviations](../../../../docs/architecture/conversion/deviations.md) in the implementation PR:

- **DV-148**: the legacy rule editor is a hand-written form per quality type whose fields store
  free text (`ruleType`, a typed dimension, an `expression`). Aurelius Atlas renders the rule
  form from the engine's vocabulary served by the server (DD-473): a kind picker, the chosen
  kind's parameters only, the dimension read-only from the kind, and no expression field
  (DV-146). The legacy's dictionary keys for the shared fields (`search.components.editor.govQuality.*`)
  carry over where a field survives.

## Acceptance

Unit (Vitest, co-located, `-c ci`):

| Proves             | File                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------ |
| EDT-25..27, EDT-29 | `src/app/search/editor/quality-fields.spec.ts`                                             |
| EDT-28, EDT-29     | `src/app/search/editor/entity-editor.component.spec.ts` (quality-mode cases)               |
| EDT-30             | `libs/angular/aurelius-atlas-data-access/src/lib/aurelius/quality-rule.service.spec.ts`    |
| DET-37             | `src/app/search/details/sections/section-config.spec.ts` + the box header component's spec |

E2E (Playwright, the served stack, namespaced seed and self-clean per DD-223 and 9.6; the
`authenticated` fixture; the m4i purge list the DET tests share):

| Proves                                                                                                                                                                                                                            | File                                               |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| EDT-25..28, EDT-30, DET-37 — create a rule from a field's box (the `+`, kind `COLUMN_NOT_NULL_RATIO`, column `total`), see it as a row of the box, edit it (threshold, deactivate), and re-read it from the store through the API | `e2e/test__aurelius_atlas_webapp_quality_rules.py` |

The e2e seeds its field and dataset with the `_seed_m4i_mini_graph` helper the DET tests share
(name-unique, self-purged), never the sample corpus. A blocked save (EDT-28's `valid: false`)
is covered in unit tests only: driving it through the UI needs a rule shape the endpoint rejects
while the drawer still accepts, which the form itself makes near-unreachable — the unit pair
covers both answers of the contract.
