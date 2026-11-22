# 18.7 The field's optional flag becomes a checkbox

- **Status:** in review
- **Pull request:** #454
- **Records:** DD-830 (here), DV-195. Relies on
  [ADR 058](../../docs/architecture/adr/058-a-new-catalogue-starts-with-the-m4i-data-dictionary-types.md),
  increment 1.4 (TDS, the typedef store), increment 1.5 (MDL, the loader), increment 7.33 (EDT-33, the editor
  labels), increment 12.7d (DV-173, the retired field-flag rules), increment 18.3 (PME-13, the rules the model
  can answer), and increment 18.6 (ACA, DD-829, the rebuild stance).

## Scope

`m4i_field` carries two flags whose names read as yes-or-no questions: `hasContent` and `optionalField`. The
data dictionary declares both as optional strings, and no rule and no record gives either one a meaning. All
264 fields of `sample_data.zip` and the one of `small.zip` hold null for both. Increment 12.7d retired the two
governance rules over them, because no field ever answered either flag (DV-173, DD-638). That increment refused
the boolean flip on one ground: a stored attribute cannot change its data type, so a flipped model reaches a
new catalogue and not an existing one.

This increment lifts that refusal the same way increment 18.6 did. The m4i dictionary is Aurelius's own model,
and the store that holds it is a development catalogue with no production data (DV-194, DD-829). A catalogue at
the old shape is rebuilt, and the flip lands.

In scope:

1. `m4i_field` drops its `hasContent` attribute definition and gives `optionalField` the type `boolean`. The
   type goes to type version `1.2` (FFB-01). The editor already answers a checkbox for a `boolean` attribute
   (EDT-03), so the flag becomes a toggle with no editor change.
2. The three sample bundles carry the new type definition, and their field records lose the `hasContent` key.
   Every `optionalField` value stays null (FFB-02).
3. The corpus keeps no rule whose expression names `hasContent`, so `m4i_field--hasContent` leaves both rule
   bundles and each bundle's export order (FFB-03, PME-13). The bundle ships 65 governance rules.
4. A catalogue that holds the string keeps the string. The load reports the model file as failed and imports
   fail whole. A new catalogue reaches the boolean shape in one load (FFB-04).
5. The editor's attribute label map and both locale catalogues retire the `hasContent` editor key. The bare
   legacy dictionary entry stays (FFB-05).

Out of scope:

- Migrating a catalogue that holds `optionalField` as a string. No door changes a stored attribute's type, and
  FFB-04 names what happens instead.
- `m4i_field--optionalField`. It stays retired and inactive as 12.7d left it, and its `completeness`
  expression still names an attribute the model declares.
- A third flag. The type's other attributes stay as they are.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FFB-01 | The `m4i_field` entity definition declares no `hasContent` attribute, declares `optionalField` with type name `boolean` and cardinality `SINGLE`, and holds type version `1.2`. The registry answers no attribute of the dropped name for the type.                                 |
| FFB-02 | Each bundle under `data/atlas-sample/` declares `m4i_field` at version `1.2` with the boolean flag and without `hasContent`, and no entity of that type names `hasContent` in `attributes` or in `relationshipAttributes`. Every `optionalField` value is null.                     |
| FFB-03 | No bundle ships a governance rule whose expression names `hasContent`. `sample_data.zip` and `only_gov_quality.zip` each ship 65 rule records, and neither export order names the dropped rule's GUID.                                                                              |
| FFB-04 | A store that holds `optionalField` as a string does not take the boolean. The load reports the model file as failed and keeps every stored attribute and version, and an import of a retyped attribute fails whole. A new catalogue reaches the boolean in one load.                |
| FFB-05 | The editor's attribute label map holds `optionalField` and no `hasContent` entry, and both locale catalogues hold no `search.components.editor.attribute.hasContent` key. The bare legacy dictionary entry `hasContent` stays, and SHL-08 compares the two catalogues with the map. |

## Aurelius origin

None. The m4i data dictionary is Aurelius's own model, versioned with the server (ADR 058). The `boolean` type
is Apache Atlas's own built-in, and the editor's checkbox for it is 7.12's shape (EDT-03).

## Deviations

None from Apache Atlas. `m4i_field` is not an Atlas type. The data decision is DV-195: dropping the rule leaves
`sample_data.zip` with 65 rules and the App Search index with 654 documents, and every verdict of every rule
that reads stays as increment 12.7d left it, because the dropped rule was already retired and judged nothing.

## Acceptance

- Unit: `libs/python/aurelius-atlas-core/tests/test__m4i_models.py` (FFB-01: the dictionary declares the
  boolean flag and no dropped attribute at version `1.2`; FFB-02: every bundle declares that type and no field
  record names the dropped key; FFB-03: every rule of every bundle names an attribute the model declares, and
  each rule bundle ships 65 rules), `libs/python/aurelius-atlas-core/tests/test__model_loader.py` (FFB-04: a
  model file that retypes a stored attribute fails whole and a new catalogue takes the boolean).
- Webapp: `apps/aurelius-atlas-webapp/src/app/search/editor/attribute-labels.spec.ts` (FFB-05: the map answers
  a checkbox label for the flag and no entry for the dropped attribute),
  `apps/aurelius-atlas-webapp/src/app/search/editor/form-fields.spec.ts` (EDT-03: a `boolean` attribute answers
  a checkbox field, and a missing value starts unchecked), `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts`
  (SHL-08: the two catalogues and the two fixtures still agree exactly).
- Run: `uv run pytest libs/python/aurelius-atlas-core/tests/test__m4i_models.py
libs/python/aurelius-atlas-core/tests/test__model_loader.py`,
  `npx nx test aurelius-atlas-webapp -c ci`.
- Data: each bundle's `atlas-typesdef.json`, its field entries and its rule entries change with the model,
  which `test__m4i_models.py` compares (FFB-02, FFB-03).
- Gates: the 14.6 App Search gates re-baseline to the new corpus. The engine answers 654 documents and the
  indexer writes 654 (one retired rule entity fewer). The governance gate reads 28 of 65 rules and answers
  1,785 verdicts, 1,765 met and 20 missed, because the dropped rule judged nothing (DV-195). The legacy
  fixture gate stands: its 684 oracle documents are the frozen recording, and the dropped rule joins the 30
  GUIDs the comparisons skip.
