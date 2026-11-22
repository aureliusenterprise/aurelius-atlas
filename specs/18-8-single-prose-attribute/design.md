# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-832. The dictionary drops `definition` and the corpus moves its text

- **Status:** Proposed
- **Increment:** 18.8
- **Date:** 2026-11-23
- **Relates to:** SPA-01 to SPA-07, ADR 070, ADR 058 (the m4i model ships with
  the server), ACA-04 (the store hands back a stored attribute the model lacks),
  DD-829 (18.6, the rebuild stance), DD-830 (18.7, the same stance for a retype),
  MDL-02 (the loader), PME-13 (12.7a, a rule names a declared attribute),
  DV-180 (MMS-07, the twelve creatable types), DV-194.

**Decision.** The eight m4i types that declare `definition` drop the attribute
definition and each goes to the next type version. Every `definition` text in
the three sample bundles moves to `description`, and the three governance rules
that ran `completeness('definition')` run `completeness('description')`. A new
catalogue reaches the shape in one load. A catalogue that already holds the
attribute keeps it, because the store's update path appends back every attribute
a stored type holds and the model lacks (ACA-04), and the load succeeds.

**Reason.** Two prose attributes on one record cost the product three visible
wrongs. The dataset editor shows two prose boxes and nothing says which to
write. The details box reads `definition` then falls back to `description`
(DET-10, DD-320), so two neighbours show text from different attributes. Four
server readers pick their own order.

The corpus already picked a key. Of the m4i records, 181 hold `definition` and 4
hold `description`, and no record holds both texts, so the move carries no
collision. The four `description` records are `m4i_dataset` and
`m4i_generic_process` records that declare no `definition` at all, so they move
as themselves and not by merge. The Apache Atlas base model owns `description`
and its own dashboards read it, so the surviving key is the one Atlas's screens
already agree on. The m4i dictionary is Aurelius's own model (ADR 058), so the
dictionary is the thing to change, not Apache Atlas.

The three hidden attributes (`owner`, `displayName`, `userDescription`) stay in
the model. `Asset` is Apache Atlas's own model and the catalogue keeps its
contract (ADR 046, DV-181), so the increment hides them in the editor (EDT-37)
and leaves the type and the read paths alone.

A removal does not fail a warm store the way 18.7's retype did. DD-830 refused a
stale store because TDS-08 refuses an attribute that changes type and MDL-02
then fails the whole file. A removal is the opposite: ACA-04 (`_keeping_registered`
in `typedef_store.py`) hands back every attribute a stored type holds and the
update lacks, so a warm store's `m4i_dataset` keeps its `definition` and the
model file loads. That is not a bug to fight and it is not a migration to build.
The product ships and tests a new store (the wiped-volume stance of DV-194), so
SPA-03 names both outcomes: a new store is the new shape, an old store keeps the
old attribute, and neither is broken.

**Alternatives.**

- **Keep both keys and hide one on each screen.** It keeps all three wrongs: the
  hidden attribute is still written by the screen that does not hide it, and the
  readers still disagree on order.
- **Retire Apache Atlas's `description` instead.** It cannot. Atlas's own
  dashboards, the REST contract (ADR 046) and every client name `description`,
  and the m4i dictionary is the only model Aurelius owns.
- **Add a `description`-only view and leave the model.** It fails SPA-01: the
  editor builds fields from the type (EDT-03), so `definition` keeps a box until
  the model drops it.
- **Migrate a stored catalogue from `definition` to `description`.** The port has
  no door that rewrites stored attributes, and every prior m4i change took the
  rebuild stance (DV-194). It would also have to decide a winner for a record
  that held both, and none does.

**Consequences.** Eight type versions move, the three bundles are re-cut, and
both scanners change the key they write. The editor now shows exactly one prose
field, `Description`, on every shipped type, because `description` is inherited
from `Asset` and the create picker's twelve all carry it (DV-180). The three
`completeness` rules flip to `description` and answer met on the same records,
because those records' texts move with them, so the 1,785 verdict total holds.
`DERIVATION_VERSION` moves to 4 (DD-833), so every App Search document
re-derives from the moved attribute. A warm store keeps `definition` and its
`completeness('definition')` rules judge an attribute the shipped model no
longer names, which is the honest cost of shipping a model change without a
migration: it is visible only to a store that should have been rebuilt.

### DD-833. The document and the card keep their `definition` field names

- **Status:** Proposed
- **Increment:** 18.8
- **Date:** 2026-11-23
- **Relates to:** SPA-05, ASD-02 (14.2), AVS-01 (16.1), AVR-04 (16.2), VCF-03
  (16.5d), DD-502 (the App Search index shape), DD-580 (the hand-mirrored card),
  DD-614 (the card's one description field), DD-484 (the frozen recording).

**Decision.** The App Search document's `definition` field and the view card's
`definition` field keep their names. Their value now comes from the entity's
`description` attribute. `DERIVATION_VERSION` goes to 4, so a document stored
against the old attribute re-derives. The view's raw `attributes` still carry
every attribute under its own name.

**Reason.** Both names are contracts that Aurelius does not own end to end. The
document's `definition` is one of the fields `atlas-dev`'s vendored engine reads
by name (ASD-02, DD-502), and the frozen `atlas-dev` recording of increment 14.4
is Apache Atlas's own output (DD-484). Renaming it makes Aurelius's index
disagree with the oracle the parity series compares against. The card's
`definition` is the 16.x family's wire field, hand-mirrored into the Angular
`Card` model (DD-580) and read by the card, the section filter and the lineage
panel. Renaming it churns the whole card family for a field label.

A field name on a wire shape is not a claim about the store attribute behind it.
DD-614 already made the card's `definition` the entity's prose with a fallback.
This increment narrows that fallback to one source and leaves the field's name
alone. The reader-facing change is the editor and the details box, which do read
the attribute name (EDT-03, DET-10) and do change.

**Alternatives.**

- **Rename both fields to `description`.** It reaches into the vendored engine's
  index mapping and the hand-mirrored card family for a name that only internal
  readers see. The parity fixtures name the document field, and DD-484 forbids
  editing them.
- **Drop the card field and make readers use `attributes`.** It breaks AVS-01 and
  every card caller for no user-visible gain. The card is the cheap read path
  that avoids walking `attributes` per entity (DD-581).

**Consequences.** `DERIVATION_VERSION = 4` re-derives all 654 documents on the
first boot after the change, the same path increment 16.5f's role names rode. The
card field's docstring loses its fallback sentence. The webapp's `Card.definition`
readers (VCF-03, the section filter) are unchanged, because the name they read
did not change. A reader who wants the raw attribute reads it from the view's
`attributes`, which now holds only `description` for prose on a shipped type.
