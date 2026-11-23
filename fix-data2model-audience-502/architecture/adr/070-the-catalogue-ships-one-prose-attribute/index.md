# 070\. The catalogue ships one prose attribute

- **Status:** Proposed
- **Date:** 2026-11-23
- **Deciders:** Aurelius Enterprise

## Decision

Apache Atlas's `description` is the only prose attribute of the Aurelius data model. The m4i data dictionary keeps no `definition`: the eight types that declare it today drop the attribute, and the text of every Aurelius record moves to `description`. Every Aurelius screen shows one prose field, and one screen shows its text.

An operator who runs a catalogue at the old shape rebuilds it. Aurelius ships sample data, and no production store holds this data, so the change ships as a model change with re-cut samples, the stance [ADR 058](<https://aureliusenterprise.github.io/fix-data2model-audience-502/architecture/adr/058-a-new-catalogue-starts-with-the-m4i-data-dictionary-types/index.md>) and increments 18.6 and 18.7 take for every other m4i change.

## Context

The shipped model gives an m4i record two prose attributes at once. Apache Atlas's base model puts `description` on `Asset`, and every entity type descends from `Asset`. The m4i data dictionary adds its own `definition` to eight types. The Aurelius screens grew around both, and each picked its own order.

That split costs the product in three places. The editor shows an m4i dataset two prose boxes, `Definition` and `Description`, and nothing tells a person which one to write in. The details screen reads `definition` first and falls back to `description` (DET-10), so the box under a record answers a different attribute than the box under its neighbour. The server reads both keys in four more places, the search document, the card line, the search matcher, and the entity vector, each with its own order.

The stored data answers the question already. Of the sample corpus, 181 records hold `definition` and 4 hold `description`, and no record holds both text. The four sit on records that carry no `definition` at all. The m4i dictionary is Aurelius's own model (ADR 058), so its convention is the one to change.

Apache Atlas is the constraint. Its base model ships `description`, its own tools write it, and the catalogue keeps its public contract (ADR 046). The stock dashboards Aurelius serves unchanged read `description`.

## Requirements

- R1: A person editing any shipped type sees one prose field, and a person reading the record sees that same text.
- R2: The Apache Atlas REST contract and the vendored dashboards keep working unchanged, so the shared key stays Apache Atlas's own.
- R3: Aurelius applications that write prose (the database scanner, the Kafka scanner, the server's own readers) name one key.
- R4: A new catalogue reaches the new shape from the shipped model in one start, and its samples import into it.
- R5: A catalogue that still holds the old shape fails loudly instead of answering two keys half-read.

## Alternatives

- **Do nothing.** It fails R1. The dataset editor keeps two prose boxes, and every reader keeps its own fallback order.
- **Retire Apache Atlas's `description` instead.** It fails R2. The stock dashboards, the Apache Atlas tools and the public contract all name that key, and the m4i model is the only one Aurelius owns.
- **Keep both keys and hide one per screen.** It fails R1 and R3. A hidden attribute is still written by whichever screen does not hide it, and the readers still disagree.
- **Migrate an existing store's records from `definition` to `description`.** It fails R4 and R5's simplicity: Aurelius ships no data-migration door, and every prior m4i change (18.6, 18.7) took the rebuild stance for the same reason.

## Tradeoffs

- **Positive:** one prose field in the editor, one attribute behind the details box, one key in every server reader. The four `description`-only records of the sample corpus need no move, and the readers lose their fallback orders.
- **Negative:** the m4i dictionary changes eight type versions, the three sample bundles are re-cut, and both scanners change the key they write. The App Search document keeps its legacy `definition` field name, because the vendored search engine reads it (DV-196).
- **Neutral / follow-ups:** technical ownership (`owner`, `displayName`, `userDescription`) is out of scope and returns with the screens that show it. A store at the old shape is rebuilt by its operator, not migrated.
