# 7.27 The rules editor

- **Status:** in progress
- **Pull request:** — (this increment's PR)
- **Records:** adds EDT-25..32, DET-38, and DD-477..483 (here), and DV-148 to
  [deviations](../../../../docs/architecture/conversion/deviations.md) in the implementation
  PR; relies on EDT-01..12/DD-322..337 (the drawer), EDT-13..17/DD-338..341 (the relationship
  picker), DET-35/36/DD-444 (the field's rules box), APC/DD-140 (data-access HTTP),
  DD-324/DD-330 (the write gate and the create route), QRE-01..04/DD-475/476 (12.5, the
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
  save validates through 12.5's validate endpoint before the entity POST (DD-477, DD-478).
- the **create and edit doors**, unchanged from the drawer's own (EDT-30's shape): the generic
  create `+` with `Data Quality` selectable in its type picker is the create door, and a rule's
  details page opens the same drawer to edit through the pencil, as every DET type does. A rule
  is an entity like any other, and it enters the editor the same way.
- the rule form's **human vocabulary** (EDT-31, DD-480): the kind picker labels each kind with
  its localized human name, picking one reveals the kind's one-line description above the
  dimension, and the dimension shows its localized name. The engine's names stay the stored
  values.
- the **threshold slider** (EDT-32, DD-481): the threshold control is a range slider beside a
  percentage field: the slider spans the served 0..1 bounds, the field shows the current threshold
  as a percentage with a % sign (an untouched field shows the default 100), a typed percentage
  outside the bounds stores the nearer bound, and editing either moves both.
- the **rule's own details layout** (DET-38, DD-482): the `m4i_data_quality` layout row gives a
  rule page a Fields box seeded from the rule's `fields` end, its stat and nav entry with it,
  like every other layout's relationship boxes.
- the `QualityRuleService` client in `aurelius-atlas-data-access` for the two 12.5 routes (the
  `SearchByMeaningService` shape, `/api/aurelius/` beside Atlas's).

Explicitly not delivered here, with the increment that will:

| Not delivered                                 | Lands with        | Why                                                               |
| --------------------------------------------- | ----------------- | ----------------------------------------------------------------- |
| A dry run of a rule over a dataset's rows     | a later increment | Needs 12.4's source readers and a server-side evaluation surface  |
| Deleting a rule                               | 7.9               | The delete flow is 7.9's, for every type                          |
| Editing `m4i_gov_data_quality` rules          | later             | The validate-entity backend is still the mock (DV-67)             |
| Scores on the form (the rule's current score) | 7.25              | The scores surface is 7.25's (DD-369)                             |
| A box-scoped create `+` on the rules box      | not planned       | The generic create door is the door; a rule is an entity (DD-483) |

## Semantics

TS tests name the ids in the test name (the 7.21a convention). The vocabulary and the validate
contract are 12.5's (QRE-01/02) and 12.1's (DQ-01/07), cited here, never restated as a TS table.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDT-25 | The drawer renders the quality form in place of the generic attribute form when its type is `m4i_data_quality` and the rule is a vocabulary one (EDT-29's seam): create mode always, edit mode when the entity names a `dqcheckkind`. The form is a kind Select over 12.5's `kinds` (each labelled by its EDT-31 human name, the rows ordered by that label), the kind's dimension shown as read-only text (EDT-31's name), and one control per required and optional parameter of the chosen kind, in the order the resource lists them. Before the create mode's first pick the form shows the kind Select over the shared fields only. Kinds load once per drawer (the service caches); while they load the form shows the drawer's loading line. |
| EDT-26 | A parameter control rides its stored attribute (patch `001-data_quality_vocabulary`): `column`→`dqcolumn`, `pattern`→`dqpattern`, `values`→`dqvalues` (chips), `columns`/`otherColumn`/`type`→ their `dq` names, `min`/`max`/`maxAgeHours`→ number, `minColumns`→ whole number. The editor writes no `dq` attribute the chosen kind does not name; a kind switch clears the parameters of the old kind (the same clear EDT-04's type switch does). The `type` control is a Select over the resource's `castableTypes`.                                                                                                                                                                                                                               |
| EDT-27 | The quality form carries the shared fields (name, description as EDT-03/EDT-11 has them), the `active` checkbox (the stored `active`, seeded from the entity, default checked on create), and the `threshold` control (EDT-32's slider-and-percent pair, 0..1 stored, empty means the engine's default 1.0 and shows 100). The form keeps the rule's other stored attributes out of the save body: quality-mode saves send name, description, `active`, `threshold`, the kind's `dq` parameters, and `dqcheckkind`.                                                                                                                                                                                                                                  |
| EDT-28 | The quality-mode Save calls 12.5's validate with the draft's stored-rule shape first (DD-476). `{valid: true}` continues with the EDT-06 save unchanged (the POST, the classifications diff, the landing on details). `{valid: false}` renders the `reason` as the drawer's error line (EDT-07's notification place) and does not POST; a later edit clears the line. A validate call that fails on transport or a non-2xx answers the same line with the generic "could not check" text — a rule never saves unchecked.                                                                                                                                                                                                                             |
| EDT-29 | The quality form seeds from the entity like EDT-02 does: an existing rule opens with its kind, its parameters under the controls EDT-26 names, its `active` and `threshold`. A legacy rule (no `dqcheckkind`, the DQ-07 pair) opens in the generic form: the quality form offers only kinds, and the pair map is the engine's (DD-479). Its Save rides EDT-23's governance banner and EWR as before, unchecked — a legacy rule stays readable by the scanner through DQ-07, and its re-authoring into the vocabulary is a human choice into the kind form, not a forced rewrite. The `expression` attribute of such a rule passes through the save untouched (EDT-27's body rule applies to quality-mode saves only).                                |
| EDT-30 | `QualityRuleService.kinds()` answers the kinds resource and `validateRule(attributes)` the validate answer (QRE-01/02's shapes), through `API_BASE_URL` and the bearer interceptor (APC). The service is the only caller of the two routes; the drawer never fetches them itself. The kinds answer is cached in the service after its first success (EDT-25's "once").                                                                                                                                                                                                                                                                                                                                                                               |
| EDT-31 | The kind picker labels each kind with its localized human name (the catalogue's, the raw engine name never shown), and picking one shows the kind's localized one-line description as read-only text between the kind and the dimension; the dimension shows its localized name too. The stored value and the validate body keep the engine's names, and a kind the catalogue does not name falls back to its raw name with no description line. The human names and descriptions are webapp copy in both catalogues, not vocabulary served by the server (DD-480).                                                                                                                                                                                  |
| EDT-32 | The threshold is a range slider beside a percentage field, side by side (DD-481): the slider spans the served `thresholdMin`/`thresholdMax` at step 0.05, the field shows the current threshold as a percentage with a % sign (the stored value stays the engine's 0..1 ratio), and an untouched or cleared field shows the engine's default as 100. A typed percentage outside the served bounds stores the nearer bound, and the field shows that bound once it is left. Both hold one value, editing either moves the other, and the pair keeps the form's between-field rhythm like every other field.                                                                                                                                           |
| DET-38 | The `m4i_data_quality` layout row (DD-482) gives a rule's details page a Fields card section seeded from its `fields` relationship end (`#related-fields`, the same seed idiom as every DET-17 box), with its stats-bar count and side-nav entry after the description and before the properties. The rule page keeps the default description box and properties accordion.                                                                                                                                                                                                                                                                                                                                                                          |

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
- `apps/atlas/proxy.conf.json` and the legacy create door — kept as it is: the generic create
  `+` and its type picker, with `Data Quality` as one of the selectable types (review call on
  this PR, DD-483).

## Deviations

Against Apache Atlas: none, Atlas has no rule editor. Against the Aurelius product, added to
[deviations](../../../../docs/architecture/conversion/deviations.md) in the implementation PR:

- **DV-148**: the legacy rule editor is a hand-written form per quality type whose fields store
  free text (`ruleType`, a typed dimension, an `expression`). Aurelius Atlas renders the rule
  form from the engine's vocabulary served by the server (DD-475): a kind picker, the chosen
  kind's parameters only, the dimension read-only from the kind, and no expression field
  (DV-146). The legacy's dictionary keys for the shared fields (`search.components.editor.govQuality.*`)
  carry over where a field survives.

## Acceptance

Unit (Vitest, co-located, `-c ci`):

| Proves                     | File                                                                                    |
| -------------------------- | --------------------------------------------------------------------------------------- |
| EDT-25..27, EDT-29, 31, 32 | `src/app/search/editor/quality-fields.spec.ts`                                          |
| EDT-28, EDT-29             | `src/app/search/editor/entity-editor.component.spec.ts` (quality-mode cases)            |
| EDT-30                     | `libs/angular/aurelius-atlas-data-access/src/lib/aurelius/quality-rule.service.spec.ts` |
| DET-38                     | `src/app/search/details/sections/section-config.spec.ts` (the rule layout row)          |

E2E (Playwright, the served stack, namespaced seed and self-clean per DD-223 and 9.6; the
`authenticated` fixture; the m4i purge list the DET tests share):

| Proves                                                                                                                                                                                                                                                                                                                                                     | File                                               |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| EDT-25..28, EDT-30, EDT-31, EDT-32, DET-38 — create a rule through the generic door (Data Quality in the picker, the human kind name and description, slider and number), pick the field in the picker, see it as a row of the field's box, edit it (threshold, deactivate), see the rule page's Fields box, and re-read it from the store through the API | `e2e/test__aurelius_atlas_webapp_quality_rules.py` |

The e2e seeds its field and dataset with the `_seed_m4i_mini_graph` helper the DET tests share
(name-unique, self-purged), never the sample corpus. A blocked save (EDT-28's `valid: false`)
is covered in unit tests only: driving it through the UI needs a rule shape the endpoint rejects
while the drawer still accepts, which the form itself makes near-unreachable — the unit pair
covers both answers of the contract.
