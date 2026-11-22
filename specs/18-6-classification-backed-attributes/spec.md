# 18.6 The data attribute type carries its tags only as classifications

- **Status:** in review
- **Pull request:** #453
- **Records:** DD-829 (here), DV-194. Relies on
  [ADR 058](../../docs/architecture/adr/058-a-new-catalogue-starts-with-the-m4i-data-dictionary-types.md),
  increment 1.5 (MDL, the loader), increment 1.4 (TDS, the typedef store), increment 18.1 (MMS, the
  bootstrap scope), increment 3.3a (CLS, direct classifications), and increment 7.33 (EDT-33, the editor labels).

## Scope

The m4i data attribute type states three of its facts twice. It declares `hasPII`, `isKeyData` and
`riskClassification` as string attributes, and the same model declares the five classifications `PII`,
`key_data`, `high_risk`, `medium_risk` and `low_risk`, each of which applies to the data attribute type.

The sample corpus uses only one of the two spellings. Across the 157 data attributes of `sample_data.zip`, all
157 hold the three attributes, and 136 hold at least one of the five classifications. Each attribute value
maps onto a classification without a single exception, and 16 attributes already hold the `PII`
classification. The attributes add nothing a classification cannot say, so this increment removes them from
the type and keeps the classifications as the only spelling of a tag.

In scope:

1. The `m4i_data_attribute` entity definition drops the three attribute definitions and goes to type version
   `1.2` (ACA-01). The five classification definitions stay as they are, and each still applies to the data
   attribute type.
2. The three sample bundles carry the new type definition, and the entity records lose the three attribute
   keys. Classifications of every record stay untouched (ACA-02, ACA-03).
3. The editor's attribute label map and both locale catalogues retire the three editor keys (ACA-05). The
   vendored legacy dictionary keys and the details page's legacy property blacklist stay (DD-829).
4. A catalogue at the old shape is rebuilt, not migrated. The port has no door that removes a stored attribute
   (DD-829).

Out of scope:

- Migrating a store that holds the three attributes. No increment removes stored attributes, and ACA-04 names
  what happens instead.
- New classifications. The five the model already declares carry every value of the three attributes, and the
  mapping table of DD-829 proves it.
- The `PII` classifications that the corpus already holds on 16 data attributes. They stay exactly as written.
- Changing the details page's property blacklist. That list ports Apache Atlas's own hidden-property set
  (DET-11) and names the three strings as legacy property names, not as m4i attributes of this type.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ACA-01 | The `m4i_data_attribute` entity definition declares no `hasPII`, `isKeyData` or `riskClassification` attribute, and holds type version `1.2`. The five classification definitions of the model all still apply to the type, and the registry answers no attribute of that name for it.                                                                                                 |
| ACA-02 | Each bundle under `data/atlas-sample/` declares the data attribute type at version `1.2` without the three attributes, and no entity of that type names one in `attributes` or in `relationshipAttributes`. `small.zip` and `sample_data.zip` declare the type exactly as the model does, and `only_gov_quality.zip` states it with its reduced attribute field set (MDD-02).          |
| ACA-03 | Every classification a bundle attaches to a data attribute is one of the five the model declares, and the model applies it to the data attribute type. A bundle holds at least one classified data attribute, so the corpus still says something about risk and key data.                                                                                                              |
| ACA-04 | A model file that drops an attribute a store already holds does not remove it. The store answers the update with no failed file, takes the new type version, and keeps every stored attribute, because an update receives back every attribute it lacks (DD-829). A new catalogue reaches the trimmed shape in one load.                                                               |
| ACA-05 | The editor's attribute label map names neither of the three attributes, and both locale catalogues hold no `search.components.editor.attribute.` entry for one. The bare legacy dictionary entries `isKeyData` and `riskClassification` stay, because the vendored Area0 dictionary supplies them (DV-181), and the completeness gate SHL-08 compares the two catalogues with the map. |

## Java origin

Nothing in Apache Atlas 2.4.0. The m4i data dictionary is Aurelius's own model, versioned with the server
(ADR 058). Classifications are the Atlas mechanism the type already uses, and increment 3.3a ports them (CLS).

## Deviations

None from Apache Atlas. The data decision is DV-194: the corpus keeps its classification tags and loses the
three attribute keys, so 21 data attributes of `sample_data.zip` carry no tag at all. Those records held
`hasPII` null, `isKeyData` blank and `riskClassification` blank, which mapped to no classification, and the
increment invents none. `small.zip` holds one untagged data attribute the same way.

## Acceptance

- Unit: `libs/python/aurelius-atlas-core/tests/test__m4i_models.py` (ACA-01: the dictionary declares no
  attribute of the three and holds version `1.2` while all five classifications apply to the type; ACA-02: every
  bundle declares the trimmed type and no entity of the type names one of the keys; ACA-03: every
  classification on a data attribute is one the model applies to the type, and at least one exists),
  `libs/python/aurelius-atlas-core/tests/test__model_loader.py` (ACA-04: a model file that drops a stored
  attribute keeps it and moves only the version, and a new catalogue reaches the trimmed shape).
- Webapp: `apps/aurelius-atlas-webapp/src/app/search/editor/attribute-labels.spec.ts` (ACA-05: the map and the
  fixture hold no entry for a retired attribute, and every label the map carries names a catalogue key),
  `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts` (SHL-08: the two catalogues and the two
  fixtures still agree exactly after the three entries go).
- Run: `uv run pytest libs/python/aurelius-atlas-core/tests/test__m4i_models.py
libs/python/aurelius-atlas-core/tests/test__model_loader.py`,
  `npx nx test aurelius-atlas-webapp -c ci`.
- Data: each bundle's `atlas-typesdef.json` and its data attribute entries change with the model, which
  `test__m4i_models.py` compares (ACA-02). The `14.6` governance gates do not move, because no rule expression
  names any of the three attributes.
