# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-829. The data attribute states each tag once, as a classification

- **Status:** Proposed
- **Increment:** 18.6
- **Date:** 2026-11-22
- **Relates to:** ACA-01 to ACA-05, ADR 058 (the m4i model), MDL-02 (the loader), TDS-08 (attribute removal),
  CLS-01 (direct classifications), DET-11 (the legacy property blacklist), DV-194.

**Decision.** The `m4i_data_attribute` entity definition drops its `hasPII`, `isKeyData` and
`riskClassification` attribute definitions and goes to type version `1.2`. The five classification definitions
`PII`, `key_data`, `high_risk`, `medium_risk` and `low_risk` stay unchanged, and each still names the data
attribute type in `entityTypes`. The three sample bundles carry the new type definition, and their data
attribute records lose the three keys while every classification stays byte-identical. The editor's label map
and both locale catalogues retire the three prefixed keys. A catalogue that already holds the three attributes
is rebuilt, not migrated.

**Reason.** The classifications already carry every value the attributes spell. The corpus proves it, with no
exception across its 157 data attributes:

| `isKeyData` | `riskClassification` | Classifications the record holds | Records |
| ----------- | -------------------- | -------------------------------- | ------- |
| No          | Low                  | `low_risk`                       | 45      |
| Yes         | Low                  | `key_data`, `low_risk`           | 44      |
| Internal    | Low                  | `low_risk`                       | 31      |
| blank       | blank                | none                             | 21      |
| Yes         | Medium               | `PII`, `key_data`, `medium_risk` | 13      |
| Yes         | High                 | `PII`, `high_risk`, `key_data`   | 2       |
| No          | Medium               | `PII`, `medium_risk`             | 1       |

`hasPII` is null on all 157 records, and 16 of them hold the `PII` classification the attribute never set. So
the mapping is: `riskClassification` picks exactly one of the three risk classifications, `isKeyData` equal to
`Yes` adds `key_data`, and `PII` arrives on its own terms. A duplicate spelling costs three fields in the
editor, three labels in two catalogues, and a second answer to "is this personal data" that no rule reads. No
governance rule expression in the corpus names any of the three attributes, so no frozen gate moves, and all
three are `isIndexable: false`, so no search document holds them.

The store gives no third choice about a catalogue at the old shape. The bootstrap update path builds each
update through `types_to_update`, and that helper appends every attribute the stored definition holds and the
new definition lacks (`_keeping_registered`, in `libs/python/aurelius-atlas-core/aurelius_atlas_core/typedef_store.py`,
which ports Atlas's `updateTypeAttributes`). The removal is therefore gone before the deletion check of TDS-08
runs, so the load reports no failure, takes version `1.2`, and answers all three attributes (ACA-04). The
sanctioned removal door is MDL-11's legacy reference-attribute patch, which reaches relationship ends only.
That is Atlas's own behaviour, so the port keeps it and the increment rebuilds the dev store instead.

**Alternatives.**

- **Keep the attributes and stop writing them.** The type still offers three editor fields, and a reader still
  gets two answers to one question. The duplication the request asked to remove stays in the metamodel.
- **Migrate a store in place.** It needs a door that removes a stored attribute, which the port does not have
  and which Atlas has for relationship ends only (MDL-11). Adding one would break TDS-08 parity for a data
  dictionary only Aurelius defines.
- **Derive classifications from the attributes at load.** A load-time rewrite of 136 records hides the tag in
  one place and invents a rule no Atlas path has. The corpus already holds the classifications, so the rewrite
  would move nothing.
- **Remove the legacy dictionary keys and the details blacklist too.** Both name the strings for other reasons.
  The dictionary keys `isKeyData` and `riskClassification` come from the vendored Area0 catalogue (DV-181), and
  the details page's list ports Apache Atlas's own hidden-property set verbatim (DET-11). Neither reads the m4i
  type.

**Consequences.** ACA-04 states the silent keep as the port's answer, so a reader of a stale store learns the
truth from a test rather than from a surprise. The dev store and any other catalogue at `1.1` keeps the three
attributes until it is rebuilt, which the bootstrap does on a new index (MMS). The 21 blank records of
`sample_data.zip` and the one of `small.zip` end untagged, and DV-194 records that choice.
