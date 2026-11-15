# 16.5g The trail shows only with a stored parent

- **Status:** in progress
- **Pull request:** #367
- **Records:** DD-630 (here); VDR-06 amended, VCF-01 amended; relies on 16.5b
  (VDR-06, DD-606), 16.5d (VCF-01/VCF-04/VCF-05, DD-616), 7.20 (DET-12, DD-317),
  16.1 (AVS-02)

A trail earns its place by showing where the entity sits. When an entity has no
stored parent, the trail holds one crumb, and that crumb repeats the name already
printed as the page title or the card title right above it. 16.5b chose that
single crumb on purpose (DD-606). The review asked for the legacy shape back:
the legacy component wrapped its whole trail, the entity's own crumb included,
in a guard on the stored parents (`.scratch/aurelius`,
`search/components/bread-crumbs/bread-crumbs.component.html`), so a parentless
entity drew no trail at all. This increment restores that, in the one rule both
screens share.

## Scope

- the shared trail rule: an entity whose stored breadcrumb is empty gets no
  trail (VDR-11);
- the same rule on both screens it feeds — the details header and every rich
  card on the results rows and in the sections (VCF-04, VCF-05);
- the unchanged neighbours: a filled trail keeps every crumb it has today
  (VDR-11).

Not in scope:

| Not delivered                                                   | Lands with |
| --------------------------------------------------------------- | ---------- |
| The stored breadcrumb itself (the indexer derives it, LAS-04)   | 14.2       |
| The opened entity's People box, chips, description, people rows | –          |
| The breadcrumbs component's own empty guard (UIC-11, unchanged) | –          |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VDR-11 | A trail renders only when the entity has a stored parent (VDR-06 amended): `trailOf` answers the stored breadcrumb, top down, plus the entity's own crumb last, and answers nothing at all when the stored breadcrumb is empty. The legacy component's guard held the same rule over its whole trail, the entity's own crumb included. A filled trail is unchanged in every other way — crumb text and icon fallbacks (VDR-06), the active crumb (DD-606, DD-625), crumb routing (DET-06). Both screens follow the one rule, so a parentless entity shows no trail in its header and none on its card |

## Aurelius origin

- `search/components/bread-crumbs/bread-crumbs.component.html` (legacy, pinned
  commit): `*ngIf="breadcrumbs.length"` wraps the `nav`, and the entity's own
  crumb (`showLast`, fed by the document provider) sits **inside** that `nav`.
  With no stored parents the whole guard fails, so the legacy details header and
  the legacy card showed no trail for a parentless entity.
- The trail's content is unchanged: the App Search document's
  `breadcrumbguid`/`breadcrumbname`/`breadcrumbtype` arrays, read through 16.1's
  door (AVS-02). Nothing about the wire or the document changes.

## Deviations

Against Apache Atlas: none (the trail is m4i demo furniture, not an Atlas
answer).

Against the demo: none new — this change moves the webapp **toward** the demo.
DD-606's one-crumb clause is superseded by DD-630, so the demo's labelled trail
and the Aurelius trail now agree in both directions: filled when a parent
exists, absent when none does.

## Acceptance

- `src/app/search/shared/trail.spec.ts`: `trailOf` answers the stored crumb
  plus the entity's own (VDR-06 kept), and answers the empty list for an entity
  without a stored breadcrumb (VDR-11).
- `src/app/search/details/details.component.spec.ts`: an entity without a
  document renders no trail (VDR-06 amended, VDR-11); the filled trail keeps its
  crumbs, its active crumb, and its routing (DET-12, VDR-06).
- `src/app/search/shared/catalogue-card.component.spec.ts`: a card with no
  stored parent draws no trail, and its title still routes (VDR-11); the filled
  card trail is unchanged (VCF-01).
- `e2e/test__aurelius_atlas_webapp.py`: the parentless seeds' results card
  draws no trail (VDR-11); the seeded mini-graph's details still show
  domain → entity with the entity active (VDR-06, DD-606).
- `libs/angular/aurelius-atlas-ui`: the breadcrumbs component keeps its own
  empty guard (UIC-11), green unchanged — the rule lives in the app's trail, not
  in the lib.
