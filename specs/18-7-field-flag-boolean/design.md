# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-830. The optional flag is a boolean and the content flag goes

- **Status:** Proposed
- **Increment:** 18.7
- **Date:** 2026-11-22
- **Supersedes:** DD-638 (Proposed, 12.7d, the two field-flag rules retire instead of becoming toggles).
- **Relates to:** FFB-01 to FFB-05, ADR 058 (the m4i model), TDS-08 (the update check), MDL-02 (the loader),
  PME-13 (the rules the model can answer), DD-829 (the rebuild stance), DV-173 (the retired rules), DV-195.

**Decision.** `m4i_field` drops its `hasContent` attribute definition and gives `optionalField` the type name
`boolean`, and the type goes to type version `1.2`. The editor answers a checkbox for the flag with no code
change, because a `boolean` attribute already renders one (EDT-03). The corpus keeps no rule over the dropped
attribute, so the record `m4i_field--hasContent` (`e5d37d4f-b93f-4a9e-afa6-f7a1fef9656c`) leaves both rule
bundles and both export orders. The three sample bundles carry the new type and their field records lose the
dropped key. A catalogue that holds the string is rebuilt, not migrated: it keeps the string, reports the model
file as failed, and fails an import that carries the retyped attribute.

**Reason.** The two flags are columns of a source spreadsheet that arrived without a defined meaning. The
dictionary describes `hasContent` as "Content Structure for a Field", which restates the name, and
`optionalField` as "Optional field for additional value", which names no fact. Both are optional strings, and
across the 265 fields of the corpus not one holds a value for either. Increment 12.7d already retired the two
rules over them for that reason (DV-173). What is left is two text boxes that ask yes-or-no questions in a type
a reader edits.

DD-638 refused the boolean flip on one ground, and the ground is still true: the update check refuses an
attribute that changes its type (`_check_updated_attribute` in
`libs/python/aurelius-atlas-core/aurelius_atlas_core/typedef_store.py`, TDS-08), an import fails whole with
`INVALID_IMPORT_ATTRIBUTE_TYPE_CHANGED`, and the loader skips the whole model file when either fires (MDL-02).
DD-638 read that as a permanent split: toggles on new stores, text boxes on every old one.

Increment 18.6 removed that split six days later, for a different attribute of the same model. It proved that
the bootstrap update path hands an update back every attribute it lacks (`_keeping_registered`, ACA-04), so no
model change shrinks a stored type, and it chose a rebuild over a migration, because the m4i store is a
development catalogue with no production data to carry (DV-194). A rebuild answers the retype exactly as well
as it answers a removal: a new catalogue takes the boolean in one load, and an old one keeps the string until
an operator rebuilds it. The choice is now the same choice 18.6 made, and this record takes it.

**Alternatives.**

- **Keep both as strings and stay retired.** The reader still types into two text boxes to answer two
  yes-or-no questions, and the flag stays a free-text field that no rule and no client reads as a fact.
- **Add a boolean twin attribute and hide the two text boxes.** This was DD-638's second alternative, and it
  still works on a warm store. It is refused for the reason 18.6 gives: the dictionary is Aurelius's own, so a
  second attribute for the same fact buys only the ability to leave the old string in place forever, which the
  Atlas type system cannot undo. The dev catalogue is rebuilt anyway.
- **Keep `hasContent` and flip only `optionalField`.** Smaller, and it avoids FFB-03's rule removal and the
  App Search re-baseline. Refused because the request named both flags, and the kept column is the one with no
  meaning at all.
- **Migrate the stored type in place.** It needs a door that changes a stored attribute's type, which the port
  does not have and Atlas has for no attribute at all. It would break TDS-08 parity for a model only Aurelius
  defines.

**Consequences.** `m4i_field` loses an attribute it never used, and its flag answers true or false. The editor
gives it a checkbox, and a field that never had the flag reads as unchecked, because `BooleanType` answers null
as valid and the editor seeds a missing boolean as `false`. The corpus drops to 65 governance rules, and the
App Search index drops to 654 documents, one retired rule entity fewer. No verdict moves: the dropped rule was
already inactive under DV-173, so it judged nothing (DV-195). The webapp retires one editor key, and the bare
legacy dictionary entry stays, because SHL-08 compares the catalogues with each other and the vendored legacy
dictionary supplies the bare entry (DV-181). A stale store is the honest cost, and FFB-04 pins it in a test so
a reader of a warm catalogue learns the truth from the suite: the whole `0010-m4i_data_dictionary_model.json`
file fails there, so no m4i type in it updates, and the catalogue keeps every string until it is rebuilt.

### DD-831. The dropped rule joins the GUID set the parity gates skip

- **Status:** Proposed
- **Increment:** 18.7
- **Date:** 2026-11-22
- **Relates to:** FFB-03, PME-13, DD-754, DV-185, DV-195.

**Decision.** `m4i_field--hasContent` joins `DROPPED_RULES`, the GUID set the three 14.6 App Search gates
remove from the frozen `atlas-dev` recording before they compare. The set holds 30 GUIDs. The recording keeps
its document for the rule, and no gate compares it.

**Reason.** PME-13 makes the corpus carry only rules whose expressions the model can answer, so the rule cannot
stay once `hasContent` does. The frozen oracle is Apache Atlas's own output and never changes, so its document
for a rule the corpus no longer holds must leave the comparisons. DD-754 built exactly that door for the 29
rules increment 18.3 deleted, and every gate already routes through the set. The set's meaning stays one thing:
a rule the corpus no longer ships.

**Alternatives.**

- **Leave the rule in the corpus.** PME-13 fails: a `completeness('hasContent')` rule over an attribute the
  model no longer declares is false on every field forever, which is the dead-rule class PME-13 exists to
  remove.
- **Edit the frozen recording.** The fixtures are Apache Atlas 2.4.0's own output and are the ground the whole
  parity series reads (DD-484). Editing one makes every later comparison untrustworthy.
- **Delete the oracle's document from the count instead of skipping it.** The gates count the recording's
  684 documents and prove Aurelius writes one per entity. Dropping a document from the frozen file breaks the
  count that proves the index shape.

**Consequences.** The count in the set's comment reads 30, and increment 18.7 is named there beside 18.3, so a
reader learns why two different increments emptied the corpus. DV-185 stays as increment 18.3 wrote it, and
DV-195 carries the new number, because an entry in the ledger records what its increment decided.
