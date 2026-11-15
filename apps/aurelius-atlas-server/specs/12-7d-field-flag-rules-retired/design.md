# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design
log apply: an accepted entry is never edited except its status line, and a changed
decision is a new entry that supersedes the old one.

## Entries

### DD-638. The two field-flag rules retire instead of becoming toggles

- **Status:** Proposed
- **Increment:** 12.7d
- **Date:** 2026-11-15
- **Supersedes:** none; follows DD-635 (Proposed, 12.7b, the retirement as data)

**Decision.** `m4i_field--hasContent` (`e5d37d4f-b93f-4a9e-afa6-f7a1fef9656c`)
and `m4i_field--optionalField` (`a74870f5-4ed4-4622-838c-157b8671bd71`) carry
`active: false` in both shipped bundles. The two attributes of `m4i_field` stay
as they are: optional, typed `string`, editable as text. No code changes; the
retirement rides VEV-03 and ASG-03 exactly as DD-635's did.

**Reason.** Both rules nag on every field of the corpus — none of its 264
fields answers either flag, and the metamodel declares both optional — while
the user's real complaint is the two warning lines in the editor drawer. The
requested fix (both flags as booleans, so the editor's existing checkbox
renders them) is blocked by Atlas's own rule: a stored attribute cannot change
its data type. `_check_updated_attribute` refuses a retyping definition update
(TDS-08), the import merge fails whole with
`INVALID_IMPORT_ATTRIBUTE_TYPE_CHANGED`, and the `UPDATE_ATTRIBUTE` patch
routes through the same check. A flipped model therefore cannot reach an
existing store: unchanged version means the update is skipped and the store
keeps `string`; a bumped version means the dictionary model file fails at every
start (MDL-02 skips the whole failed file). Shipping toggles for fresh installs
and text boxes for every existing one is the split this project's parity rules
call a false product. Retiring the two rules answers the complaint with the
machinery already reviewed in 12.7b.

**Alternatives considered.**

Flip the two attributeDefs anyway (refused: it cannot land on an existing
store — see Reason; and where it would land, a checkbox always writes
`false`/`true`, so a kept `completeness` rule passes the first time anyone
saves the field — the false-verdict class 12.7a/12.7b exist to remove).
Boolean twin attributes (`hasContentFlag`, `optionalFieldFlag`) as new
defs, retiring the nags and hiding the two dead text boxes (refused as too
big for the complaint: an editor field-exclusion rule, new labels through
the catalogue, and two dead `string` attributes in the def forever — Atlas
cannot delete one; open it as its own increment if the flags ever earn it).
Keep the nags (refused: two honest-but-useless warnings per field is what
started this).

**Consequences.** 528 verdict documents (264 fields × 2 rules) leave Aurelius's
index; the 14.6 read set drops 45 → 43 and the verdict balance reads 1,767 met
/ 263 missed. The parity set is untouched — the frozen oracle's read set of 27
rules never carried either rule (DV-173 names the damage), so every legacy
verdict still answers as it did. The field drawer loses two warning lines and
keeps two text boxes. A retype of either attribute needs a legal path Atlas
does not have; if it ever grows one, the flip rides it and the rules return by
`active: true`.
