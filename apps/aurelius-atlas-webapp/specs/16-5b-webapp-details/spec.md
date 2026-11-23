# 16.5b The details screen on the read door

- **Status:** in progress
- **Pull request:** #362
- **Records:** ADR 064; DD-604 to DD-607, DD-834 to DD-837 (here); relies on 16.1 (AVS-01..09),
  16.2 (AVR-10), 16.5a (VSR-03, the `atlas-view.ts` mirror), 7.20 (DET, DD-317/DD-318),
  7.21a (DET-17..22), 7.24 (DET-35/40), 4.4 (PRO-02's propagation)

The second screen switched to the view family (ADR 064). The details screen today assembles its
header, People box, sections and properties from the Atlas entity GET, and its trail renders empty
because nothing fills the seam 7.20 left (DD-317). After this increment it reads one door:
`GET /api/aurelius/v1/entity/guid/{guid}`, in 16.1's view shape — the header, the trail, the
People box, the section seeds and the properties from that one read. What the page shows stays
what 7.20/7.21a/7.24 built; what it reads changes.

## Scope

- in `aurelius-atlas-core`: the read door's own relationship ends (VDR-02) — AVS-04's merge
  clause, which no door has answered until now — and its read of the classifications propagation
  brought (VDR-12, DD-835);
- in `aurelius-atlas-server`: the read route passes them (AVR-10's live view, made complete);
- in `aurelius-atlas-data-access`: `ViewEntityService`, the read door's client, with the
  GUID-keyed cache ADR 064 schedules (its clause that supersedes DD-318's no-cache posture);
- in `aurelius-atlas-webapp`: the details store and screen read the view (VDR-03 to VDR-09, and
  the header's propagated chips of VDR-12), and the breadcrumb seam closes.

Not in scope, with the increment that will:

| Not delivered                                                             | Lands with |
| ------------------------------------------------------------------------- | ---------- |
| The editor on the mutation door, the tag diff, the picker and conflict UX | 16.5c      |
| The card bodies' data on the view family (they keep the Atlas bulk read)  | –          |
| A stale badge or governed mark on the screen (the view carries both)      | –          |
| The App Search wire retired                                               | 16.6       |

## Semantics

The door's own rules (AVR) answer every request; the rules below cover the door's ends and the
screen that reads it.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VDR-01 | The details screen reads its entity through `GET /api/aurelius/v1/entity/guid/{guid}` (AVR-10), one read for header, trail, People box, section seeds and properties (ADR 064 R1). The Atlas entity GET leaves the screen; the section cards keep their bulk `getEntitiesByGuids` (2.3 stays what the card bodies read)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| VDR-02 | The read door answers `sections` with the entity's own relationship ends, as AVS-04 states and no door has answered: the ACTIVE edges of the entity's relationship attributes, keyed by attribute name, each end `{guid, name, typeName, status}`. A read end takes the end's place: a stored derived pair naming the same GUID loses it, a pair's other ends and the pairs of unmated attributes stay (DD-604). Two read attributes can name one entity at the same time, and then both sections answer it (REL-17)                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| VDR-03 | The People box, the person stats' counts and the section seeds read the view's sections by attribute name; the EDT-15 rule stands unchanged (ACTIVE ends carrying a guid, deduped keeping the first). The card bodies render the bulk-read `AtlasEntity` as 7.21a left them                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| VDR-04 | The properties table merges the view's `attributes` with link arrays built from its sections, under the legacy blacklist and drops of DET-11 — the same rows the Atlas GET's merge answered, because the view's attributes hold what the stored entity holds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| VDR-05 | The header's own chips are the view's `classificationNames`, each by its dictionary display name (DET-09's rendering kept) — the entity's own tags only, the split VDR-12 completes; the card bodies' chips are unchanged, as their source is unchanged                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| VDR-06 | The breadcrumb seam (DD-317) is filled: the trail is the view's `breadcrumb` (top down, each crumb's name, or its type, or its guid) plus the opened entity's own crumb, which the breadcrumbs mark active. Icons ride the app's type map, as the badge's do (DET-26). A crumb click routes (DET-06). An entity without a document shows no trail at all: the trail rule asks a stored parent, the legacy guard's shape (amended by 16.5g, VDR-11, DD-630)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| VDR-07 | A read served from the cache (DD-605) paints without a request: a guid opened again in the session answers from memory, the editor's save tick evicts and re-reads (DD-327 kept), a page reload clears it, and the store holds its last 50 views                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| VDR-08 | A 404 answers the empty state with no alert (DET-13, ALR-05's 4xx silence); every other failure alerts with the retrieve line, as DD-318 left it. A `stale` answer renders as any other answer (its mark is not shown)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| VDR-09 | The layout dispatch (DET-15's typedef walk), the title, badge, description box, stats bar, anchors and every visible string stay as 7.20/7.21a/7.24 built them; no new visible field; no i18n key added or removed                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| VDR-10 | No other screen's calls change — the editor keeps its Atlas read until 16.5c — and no Apache Atlas or App Search answer changes (R3, R4)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| VDR-12 | The screen also shows the classifications propagation brought, marked as such (DV-197, DD-834 as amended by DD-836): a door reads them beside the entity and answers `propagatedClassifications`, one entry per name with the entities it came from (DD-835). Every door that reads them fills the field, view and card alike (DD-836), so the header of an entity and the result line of that same entity mark the same tags. The marked chip's dropdown names those sources, and each source row shows the source's type icon and name above the path it sits on in place of its type name (DD-836, as amended by DD-837): the row's name, with its icon, is the control that routes to the source's details, and each crumb of the path routes to its own entity. A source the store lost leaves the entry with none, and the chip still shows. The editor's diff and the mutation door's refusal stay as VDR-05 left them: the entity's own names never move (AVW-08) |

## Aurelius origin

- ADR 064 R1 (one read), R2 (one shape family) and its follow-up clause for the GUID cache;
  AVS-04's merge clause this increment finally answers; AVR-10's live view.
- 7.20 (DET-07..13, DD-317's seam, DD-318's no-cache posture), 7.21a (DET-17..22's sections),
  7.24 (DET-35/40's boxes and person stats): the screen this increment re-sources.
- 16.5a (VSR-03): the `atlas-view.ts` mirror this screen joins.

## Deviations

Against Apache Atlas (DV-197, superseding DV-166): the details header's own chips show the
classifications the entity owns, and the propagated ones ride the same row marked, each marked chip
naming the entities its tag came from. The legacy header drew them in a row of their own (DD-834);
the editor's box never lets a propagated tag be edited (DD-326), and the mutation door protects it
from a save's diff (AVW-08) — the tag belongs to its source.
Against the wire this page leaves (intentional, its retirement road): the Atlas entity GET's
`relationshipAttributes` becomes the view's `sections` (VDR-02), its `classifications` become
`classificationNames` (VDR-05), and the trail's missing source becomes the document's stored
breadcrumb (VDR-06).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__view_derivation.py`: the ends of an entity with edges,
  ACTIVE only, keyed by attribute, none for an entity without them, and one end under two
  attributes answered by both (VDR-02); the grouped propagated names and `read_propagations`
  over a two-hop chain, including a name whose source is gone (VDR-12, DD-835).
- `libs/python/aurelius-atlas-model/tests/test__views.py`: the view's extra fields and
  `ClassificationSource`'s shape; the card carries `propagatedClassifications`, and a
  `RelationEntity` answers a `breadcrumb` only when its document has parents (VDR-12, DD-836).
- `apps/aurelius-atlas-server/tests/test__view_family.py`: the door answers its ends and the
  pair's dedupe; an entity without edges answers as before (VDR-02); the door answers a
  propagated tag with the entity it came from, in the view and in the card it serves (VDR-12,
  DD-836); the existing AVR-10 pins stay green.
- `libs/angular/aurelius-atlas-data-access/src/lib/aurelius/view-entity.service.spec.ts`: the
  door's URL, the cache's hit, the eviction and the cap (VDR-01, VDR-07).
- `apps/aurelius-atlas-webapp/src/app/search/details/details.component.spec.ts`: the door read
  for a seeded view; header, trail, People box, sections seed and properties from the view (VDR-01
  to VDR-06); the marked chip, its source rows with their icon and one-line clickable path, the
  name routing to the source and a crumb routing to its crumb (VDR-12, DD-836, DD-837); the 404 and
  failure paths (VDR-08).
- `apps/aurelius-atlas-webapp/src/app/search/shared/catalogue-card.component.spec.ts`: the card
  marks a propagated tag the search door brought, names its source with its icon and one-line
  path, routes the source's name without opening the card too, and routes a crumb of its path
  (VDR-12, DD-836, DD-837).
- `libs/angular/aurelius-atlas-ui/src/lib/classification-chip/classification-chip.component.spec.ts`:
  the marker's trigger is a keyboard-focusable button, so the sources are reachable (VDR-12).
- `apps/aurelius-atlas-webapp/src/app/search/details/sections/**` specs: seeds and counts from
  the view's sections, the card bodies unchanged (VDR-03).
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts`: green with no key added or
  removed.
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp.py`: the details scenarios ride the
  door; one new scenario opens a parented entity and shows the filled trail (VDR-06); one opens a
  tagged entity's downstream end and shows the marked chip, its source row, and the routing, and
  finds the same mark on that entity's card in the results list (VDR-12, DD-836).
