# 16.5d One rich card on both screens

- **Status:** in progress
- **Pull request:** #364
- **Records:** ADR 064; DD-614 to DD-617 (here); DV-167; relies on 16.1 (AVS-01..09),
  16.2 (AVR-02/07/08), 16.5a (VSR-03/VSR-07), 16.5b (VDR-03/VDR-06), 7.13 (UIC-14),
  7.21a (DET-17..22, DD-367/DD-368)

The results cards and the details section cards show the same entity differently. The results row is
a bare title and badge; the section card adds the uniform body (chips, the description, the people
rows) that 7.21a built on the Atlas bulk read. The legacy showed one rich card everywhere: its body
led with the entity's breadcrumb trail and carried its text and people (DD-367 refused both for the
uniform body, because the trail had no source). The view family answers the source now: every card
carries its stored `breadcrumb`, `definition` and `classificationNames` (AVS-01/AVS-02). After this
increment both screens render one shared rich card — trail, chips, description and people — and the
details sections resolve their cards through the search door instead of the Atlas bulk read, the way
the legacy sections read App Search.

## Scope

- in `aurelius-atlas-core`: the card's description rule (AVS-03 amended, DD-614) — `definition`
  falls back to `description`, so a card of a type that stores its text under `description` carries
  it;
- in `aurelius-atlas-webapp`: one shared rich card component (VCF-01), the details sections'
  resolve switched to `POST /api/aurelius/v1/search` with the GUID filter (VCF-02, DD-615), and the
  results rows rendered with the shared card (VCF-04).

Not in scope, with the increment that will:

| Not delivered                                                                    | Lands with |
| -------------------------------------------------------------------------------- | ---------- |
| Role labels on the card's people row (DV-167, DD-617)                            | –          |
| A card badge alias (the card shape has no `typeAlias`, DV-167's second clause)   | –          |
| The Governance Quality Rules rows (they keep the uniform body on the bulk shape) | –          |
| The App Search wire retired; `/api/atlas/v2/entity/bulk` left for other callers  | 16.6       |

## Semantics

The door's own rules (AVR) answer every request. The rules below cover the card body's source and
the two screens that render it.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VCF-01 | One shared card component renders a view-family card on both screens: the title (`displayText`), the badge (the type's dictionary name and icon, no alias), the breadcrumb trail of the card (the stored `breadcrumb` plus the card's own crumb — VDR-06's rule, shared; the plain-text crumb is the entity being viewed where one is open, the card's own on a results row, DD-625), the classification chips (`classificationNames`, DD-379's names), the description text as markdown, and a flat people row from the card's derived `m4i_person` relations (names linked, deduped, omitted at none) |
| VCF-02 | A details section resolves its seed through the search door: one request per chunk of 25, `filters.guid` carrying the chunk, `limit` its length, no facets. A guid the answer lacks is a deleted relation (no card, the count keeps it) and a failed chunk drops its cards with the one retrieve alert — DET-18's rules ride the new door unchanged. The section stops calling `GET /api/atlas/v2/entity/bulk` (DD-615 supersedes VDR-03's bulk clause for card bodies)                                                                                                                                 |
| VCF-03 | Every card's description text is the entity's `definition`, else its `description` (AVS-03 amended, DD-614). The read door's `attributes` are unchanged; only the card field's derivation gains the fallback, and the webapp shows that field on the card body                                                                                                                                                                                                                                                                                                                                          |
| VCF-04 | A results row renders the shared card of the answer's card (VSR-07's "no new visible field" is superseded: the row now shows the body and trail the card already answers, with no second request). The count header, facets, paging and the click-to-details routing stay as 16.5a left them                                                                                                                                                                                                                                                                                                            |
| VCF-05 | A section card renders the same shared card as a results row does — same markup, same fields, one component behind both. Loading cards keep the plain ui-card loading row (DET-18); the section's search, sort and paging stay client-side over the resolved cards (DET-20/21/22, DD-368), now matching `displayText`, `qualifiedName` and the description text                                                                                                                                                                                                                                         |
| VCF-06 | The card's people row is one flat list of names without role labels (DV-167): the document's derived person relations name the people but not their roles, and the legacy's per-role document arrays were never filled. The opened entity's People box keeps its labelled rows from the view's `sections` (VDR-03 kept)                                                                                                                                                                                                                                                                                 |
| VCF-07 | The section keyword match, the seed counts, the stats bar, the People box and the person stats read the view's `sections` as 16.5b left them; only the card bodies change source. No other caller of the Atlas bulk read changes, and no Apache Atlas or App Search answer changes (R3, R4)                                                                                                                                                                                                                                                                                                             |

## Aurelius origin

- ADR 064 R2 (one shape family): the card body reads the card everywhere, so the two screens cannot
  diverge again.
- The legacy `models4insight` cards: every card body led with the breadcrumb trail and its text on
  the App Search document (`breadcrumbname`/`breadcrumbguid`, `definition`); the legacy details
  sections resolved their cards from the search engine, not per-entity (DD-365's port).
- 7.13 (UIC-14), 7.21a (DET-17..22, DD-367): the card shell, the uniform body and the sections store
  this increment re-sources and unifies.
- 16.5a/16.5b (VSR, VDR): the two screens and the card shape they already ride.

## Deviations

Against Apache Atlas: none new (R3, R4 — no Atlas answer changes).

Against the demo this page leaves (DV-167): the card body shows the people without their role labels
(the legacy's per-role document fields were never filled) and its badge without an alias (the card
shape carries no `typeAlias`). Both are recorded in [Deviations](../../../../docs/architecture/conversion/deviations.md)
with the note to solve the roles when a source exists.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__view_derivation.py`: the card of an entity whose type
  stores `description` (no `definition`) carries that text; `definition` still wins (VCF-03).
- `libs/python/aurelius-atlas-core/tests/test__view_search.py`: a door card of a description-only
  entity answers its `definition` (VCF-03).
- `apps/aurelius-atlas-webapp/src/app/search/shared/catalogue-card.component.spec.ts`: the trail,
  chips, description markdown, flat people row and its routing emits (VCF-01, VCF-06).
- `apps/aurelius-atlas-webapp/src/app/search/details/sections/related-sections.state.spec.ts`: the
  door request per chunk (GUID filter, limit), the miss and the failure rules on the door answer,
  the client-side match on the card fields (VCF-02, VCF-05).
- `apps/aurelius-atlas-webapp/src/app/search/details/details.component.spec.ts`: the sections
  resolve through the door, the card renders body and trail, the alias clause retires; the People
  box, counts and person stats unchanged (VCF-05, VCF-07).
- `apps/aurelius-atlas-webapp/src/app/search/results/results.component.spec.ts`: a result row
  renders body and trail from the answer's card with no second request (VCF-04).
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts`: green unchanged — the flat row's
  label reuses the dictionary's existing `derivedperson` ("People" / "Personen"), so no key is added.
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp.py`: the details scenario waits for
  the door to answer the seeded cards before it opens the screen (the indexer's beat, CLS-12's
  sibling); the bodies and the section cards ride the door; one results assertion shows a card's
  trail text (VCF-02, VCF-04).
