# 16.5f Role-labelled people on the rich cards

- **Status:** in progress
- **Pull request:** #366
- **Records:** DD-626 to DD-628 (with the core part); DV-167 amended; relies on 16.5d
  (VCF-01..07, DD-616/617), 16.5e (VCF-08..14), 7.21a (DET-23), 16.1 (AVS-02)

This page is the `aurelius-atlas-webapp` part of increment 16.5f; its rule table is the
increment's shared set. The other part is with [`aurelius-atlas-core`][part-0], which
fills the document fields and answers the door.

The demo's card bodies name each person with their responsibility: "Data Owner(s): …",
"Data Steward(s): …", "Domain Lead(s): …". 16.5d shipped the cards with one flat "People"
row instead (VCF-06, DV-167), because a card's people came from the stored document
without roles. 16.5f's core part now answers the roles on the card; this part renders the
labelled rows.

## Scope

- the shared rich card's people, one labelled row per role the card has people for, in
  the legacy order (VCF-15);
- the flat row as the fallback for a document without role data yet (VCF-16);
- the unchanged neighbours: the opened entity's People box, the People facet, the counts
  (VCF-17).

Not in scope:

| Not delivered                                                             | Lands with |
| ------------------------------------------------------------------------- | ---------- |
| The document fields and the door answer (ASD-06/07, AVS-10)               | [part-0]   |
| The opened entity's People box (DET-23 already renders its labelled rows) | –          |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VCF-15 | The shared rich card names its people in one labelled row per role it has (VCF-06 amended): Domain Lead(s) (`domainLead`), Data Owner(s) (`businessOwner`), Data Steward(s) (`steward`), in that order — the legacy card's order (DET-23's rows, `shared/people.ts`'s ends and labels). Each row dedupes by guid first-wins and links each name, emitting `cardClicked(guid)`. A role with no people draws no row, and a card with none draws no people block |
| VCF-16 | A card whose document has person names but no role ends (derived before 16.5f, still awaiting its round, ASD-07) keeps today's flat "People" row (VCF-06 as written). The row is the fallback, never an extra: when role ends answer, the flat row is gone (DD-628)                                                                                                                                                                                           |
| VCF-17 | Nothing else changes: the opened entity's People box keeps its rows from the view's sections (VDR-03, DET-23), the sections' People facet keeps counting the `m4i_person` relations (VCF-09 — the role keys are different attributes and add no rows), and the stats bar and counts are untouched                                                                                                                                                             |

## Aurelius origin

- The legacy card body (`search/components/people/people.component.html`): three blocks in
  the order Domain Lead(s), Data Owner(s), Data Steward(s), each with the persons icon,
  the dictionary label (`search.components.people.*` keys, held in both catalogues), and
  deduped name links. `shared/people.ts` already holds those ends and labels for the
  opened entity's box (DET-23); VCF-15 reuses them.
- The demo resolved a card's roles through an entity read per card; our card reads them
  from the door's `card.relations` now that the core part answers them (DV-167 amended).

## Deviations

Against Apache Atlas: none (the roles are m4i data-dictionary concepts).

Against the demo: DV-167 amended — the card's rows now match the demo's. The remaining
difference is the round delay: a freshly written edge shows on a card only after the
indexer re-derives its document, not on the first read.

## Acceptance

- `src/app/search/shared/catalogue-card.component.spec.ts`: the labelled rows in order
  with their emits, dedup, the no-row rules (VCF-15), the flat fallback (VCF-16), the
  People-box and facet non-effects stay green (VCF-17).
- `e2e/test__aurelius_atlas_webapp.py`: the seeded entity's card on its domain's page
  shows "Data Owner(s)" and "Data Steward(s)" rows (VCF-15) on the shared dev store,
  namespaced seeds, self-cleaned.
- `src/app/search/details/sections/related-sections.state.spec.ts`: the People facet
  counts unchanged with role keys present (VCF-17).

[part-0]: ../../../../libs/python/aurelius-atlas-core/specs/16-5f-card-people-roles/spec.md
