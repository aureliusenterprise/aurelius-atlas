# 16.5f Role-labelled people on the rich cards

- **Status:** in progress
- **Pull request:** #366
- **Records:** DD-626 to DD-629 (here); DV-167 amended, DV-170 new; relies on 14.2
  (ASD-01..05), 16.1 (AVS-01/02, LAS-05), 16.5d (VCF-01..07), 16.5e (VCF-08..14)

This page is the `aurelius-atlas-core` part of increment 16.5f; its rule table is the
increment's shared set. The other part is with [`aurelius-atlas-webapp`][part-0].

The demo's card bodies name each person with their responsibility: "Data Owner(s): …",
"Data Steward(s): …", "Domain Lead(s): …". A card's people come from its stored search
document, and that document names the people without roles: the legacy document had
per-role GUID fields (`deriveddataownerguid`, `deriveddatastewardguid`,
`deriveddomainleadguid`), and the legacy pipeline never filled them — all 684 records of
the `tests/fixtures/legacy-app-search-atlas-dev.json` fixture hold `null`. This increment
fills those fields, and carries their ends on the card to the webapp.

## Scope

- the three per-role relation fields on the App Search document, filled by the indexer
  from the entity's relationship attributes (ASD-06);
- the source hash's derivation version, which makes every pre-16.5f document stale once
  so the round re-derives and fills it (ASD-07);
- the read door answering those ends in `card.relations` under their attribute names
  (AVS-10).

Not in scope:

| Not delivered                                                                                                     | Lands with |
| ----------------------------------------------------------------------------------------------------------------- | ---------- |
| The per-role fields as query fields (the legacy engine read them as constants, so queries over them never worked) | – (16.6)   |
| The card rows themselves (VCF-15..17, the webapp part)                                                            | [part-0]   |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASD-06 | Each mapped entity's document carries `deriveddomainleadguid`, `deriveddataownerguid` and `deriveddatastewardguid`: the GUIDs of the ACTIVE ends of the entity's `domainLead`, `businessOwner` and `steward` relationship attributes, each with its name at the same position in `deriveddomainlead`, `deriveddataowner` and `deriveddatasteward` (the LAS-05 pair shape), deduped first-wins. An entity whose type has no such attribute carries empty lists. The three fields map as the other relation fields do (ASD-02 extended). The legacy named only the GUID fields; the name lists are ours, because the door answers a card's people from the document alone (DD-627) |
| ASD-07 | The source hash includes the derivation version (ASD-03 amended). The indexer's round writes every document whose hash is not the entity's current one, so bumping the version makes each document stale once and the round re-derives it (ASD-04's set, unchanged). Version 1 is the hash as written until 16.5f; 16.5f writes version 2 documents carrying ASD-06's fields (DD-628)                                                                                                                                                                                                                                                                                            |
| AVS-10 | The read door answers `card.relations` with the role ends too: the `domainLead`, `businessOwner` and `steward` lists of the document, each as its own `EntityRelation` keyed by the attribute name, after the type-keyed relations (AVS-02's shape). An end the store no longer has keeps the document's stored name, as the other relation pairs do (AVS-02, ASU-03)                                                                                                                                                                                                                                                                                                            |

## Aurelius origin

- Apache Atlas 2.4.0 has no role concept: the three attributes and the demo's rows are
  m4i/Aurelius data-dictionary features. The origin for the fields is the Aurelius legacy
  (`atlas-dev` document mapping and `search/components/people/people.component.html`),
  recorded under DV-167.
- Our type registry already answers the role ends: `read_ends` keys them by attribute name
  for the view door (VDR-02, DD-604), and the indexer's `first_parent` uses the same
  membership test (LAS-04). ASD-06 reuses that mechanism, not a new walk (DD-626).

## Deviations

Against Apache Atlas: none (the roles are m4i data-dictionary concepts).

Against the demo: DV-167 amended — the roles ride the stored document, filled at index
time, where the demo resolved them through an entity read per card. See the ledger row.

## Acceptance

- `tests/test__app_search_document.py`: the three fields with their pairs, deduped and in
  order, empty for a roleless type (ASD-06); the version in the hash and the one-time
  staleness (ASD-07).
- `tests/test__app_search_indexer.py`: a seeded entity with owner, steward and
  domain-lead edges gets the filled fields; the round re-derives a version-1 document
  once and fills it (ASD-06, ASD-07).
- `tests/test__view_search.py`: `card_of` answers the three role relations after the
  type-keyed ones (AVS-10).

Run with `nx test aurelius-atlas-core -c ci`.

[part-0]: ../../../../apps/aurelius-atlas-webapp/specs/16-5f-card-people-roles/spec.md
