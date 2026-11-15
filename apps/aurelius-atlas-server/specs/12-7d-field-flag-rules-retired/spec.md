# 12.7d The two field-flag rules retire

- **Status:** in review
- **Pull request:** #373
- **Records:** adds DD-638 (here) and DV-173; amends nothing on the wire. Relies on
  VEV-03 (12.2, a rule is ACTIVE unless its `active` attribute is false), ASG-03
  (14.6, an inactive rule reads nothing), and DD-635 (12.7b, the retirement as data).

## Scope

Two rules of the sample corpus nag on every field: `m4i_field--hasContent`
(`e5d37d4f-b93f-4a9e-afa6-f7a1fef9656c`) and `m4i_field--optionalField`
(`a74870f5-4ed4-4622-838c-157b8671bd71`), each a `completeness` rule over its
attribute. Not one of the corpus's 264 fields answers either flag, so the editor
drawer, the details box and the rule pages carry two warning lines per field for
two optional flags the metamodel itself declares optional.

The ask behind this increment was a toggle: both flags read as booleans, so the
text boxes should be checkboxes. That is blocked upstream, and the block is not
ours to lift (DD-638):

- An attribute of a stored type definition **cannot change its data type**.
  A definition update that retypes one is refused (`_check_updated_attribute`,
  TDS-08 — the same rule Apache Atlas 2.4.0 has); an import that carries a
  retyped attribute fails whole with `INVALID_IMPORT_ATTRIBUTE_TYPE_CHANGED`;
  even the `UPDATE_ATTRIBUTE` typedef patch runs through the same check.
- So a flipped dictionary model would reach only new stores: an existing store
  keeps `string` when the file's version does not change, and fails the whole
  `0010-m4i_data_dictionary_model.json` file at every start when it does
  (MDL-02 skips a failed file). Toggles on fresh installs and text boxes
  everywhere else, forever, is worse than no toggle.

What the screen actually needs is the warning, not the box: both rules retire.

## Semantics

No new rule id and no code change. VEV-03 and ASG-03 already take a rule with
`active: false` out of the verdicts, the editor, the rule pages and the 14.6
read set — the 12.7b retirement precedent (DD-635), applied to two records:

- `data/atlas-sample/sample_data.zip` — both rule records carry `active: false`
- `data/atlas-sample/only_gov_quality.zip` — the same two records, the same edit

The two attributes stay in the metamodel as optional strings: still visible,
still editable, just no longer demanded. A later increment can retype them if
Atlas ever grows a legal retype.

## Aurelius origin

None. The two rules travel the corpus, and the retirement reuses the machinery
12.7b built for the two presence rules.

## Deviations from Java Atlas

[DV-173](../../../../docs/architecture/conversion/deviations.md): the frozen
`atlas-dev` oracle's verdict documents never carried these two rules — its read
set judged 27 rules and neither of them is among them. Retiring them moves
Aurelius closer to the oracle: 528 verdict documents (264 fields × 2) leave
Aurelius's index, and the parity set is untouched — 1,612 kept, 29 pair moves,
16 missing-guid.

## Acceptance

- The three 14.6 gates, on the re-baselined truth:
    - `test__app_search_governance.py`: 43 of 95 rules read (two joined the two
      retired presence rules as inactive); 2,030 verdicts, 1,767 met and 263
      missed; the 1,612 legacy documents of a read rule keep their verdicts, the
      29 pair moves and the 16 missing-guid hold (LAS-13, DV-160, DV-171,
      DV-172, DV-173);
    - `test__legacy_app_search_fixtures.py`: unchanged — 324 description
      differences, 199 disagreements, 5 name differences;
    - `test__app_search_indexer.py`: unchanged.
- Both bundles: only the two rule records changed, every other entry
  byte-identical to before the edit.
