# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-306. An import maps a clashing GUID to the stored entity instead of renaming it

- **Status:** Proposed
- **Increment:** 6.3b2
- **Date:** 2026-11-02

**Decision.** Before an imported entity is written, each of its GUIDs that is not stored is looked up by the
entity's unique values. When another stored entity holds them, the imported GUID stands for that entity's GUID
in everything the import writes from then on.

**Reason.** Atlas meets the clash as a unique-index violation and renames the stored vertex to the imported GUID,
keeping the old GUID as historical. Its relationships and references follow the vertex, not the GUID. Ours are
stored by GUID in relationships, references, classifications and audits, so a rename would rewrite every
document naming the entity. Mapping the GUID within the import gives the same graph, with the stored GUID.

**Alternatives.** A rename across every index: faithful, but a large write that must not half-fail. Failing the
import: safe, but an import into a catalogue that already holds part of the data would never succeed.

**Consequences.** After such an import the entity keeps its stored GUID, not the exported one (DV-126); an
importer that looks entities up by the exported GUID does not find it.
