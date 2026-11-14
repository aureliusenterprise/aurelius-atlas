# 16.5c The editor on the mutation door

- **Status:** in progress
- **Pull request:** #363
- **Records:** ADR 064; DD-608 to DD-613 (here); relies on 16.1 (AVS-01..09),
  16.2 (AVR-10, AVR-13), 16.3 (AVW-01..12, DD-589..594), 16.5b (VDR-01..10,
  DD-605's cache and evict), 7.7a-7.7c and 7.9 (EDT-01..28), 12.5 (EDT-25..28),
  12.7 (EDT-23/24's banner)

The third screen switched to the view family (ADR 064). The editor today reads
its entity through the Atlas entity GET, builds its form from a dump of every
typedef, seeds its tag box by filtering the answer's classifications on the
client, and saves by POSTing the entity and then adding and deleting each tag
beside it (DD-326, DD-340). After this increment it shares the read door with the
details screen, builds its form from one type slice, and saves through the
mutation door in one request. What the drawer shows and how it behaves stays what
7.7 and 7.9 built. What it reads and how it writes change.

## Scope

- in `aurelius-atlas-core` and `aurelius-atlas-server`: the mutation door's two
  answers (the saved view and the conflict's stored view) carry `sections` as the
  read door answers them (VDR-02's ends, the one batched read DD-604 introduced),
  which completes AVW-07's "as 16.2's read door answers it";
- in `aurelius-atlas-data-access`: the mutation door's client (one POST, its 409
  answers passed whole) and the form-slice clients (the for-type chain, the
  classification and enum slices, the entity headers for the create picker);
- in `aurelius-atlas-webapp`: the editor store and drawer read the view, save
  through the door, and re-edit on a conflict (VDE-01 to VDE-12).

Not in scope, with the increment that will:

| Not delivered                                                        | Lands with |
| -------------------------------------------------------------------- | ---------- |
| The delete through the door (the editor keeps its Atlas DELETE path) | –          |
| Labels editing (the editor never had it; the door takes the set)     | –          |
| The Atlas entity GET and POST retired for every other screen         | 16.6       |
| A stale badge or governed mark on the drawer (the view carries both) | –          |

## Semantics

The door's own rules (AVW) answer every write, and the read door's rules (AVR,
VDR) answer the open. The rules below cover the drawer that reads and writes
them.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| VDE-01 | The editor reads its entity through `GET /api/aurelius/v1/entity/guid/{guid}` (AVR-10), in the drawer's own read (DD-322 kept). The Atlas entity GET (EDT-02) leaves the editor. The form, the tag box, and the pickers seed from that view, and the GUID cache (DD-605) serves the open (VDR-07)                                                                                                                                                                                                                                                                                                            |
| VDE-02 | The form fields, the relationship pickers, the enum options, and the type lineage build from `GET /api/aurelius/v1/types/for-type/{name}` (AVW-11): the named type and its supertype chain, each typedef whole. The tag box's applicable classifications come from the classification defs (`GET /api/atlas/v2/types/typedefs?type=CLASSIFICATION`), kept by the chain's lineage (EDT-05's rule). The create picker lists the entity typedef headers (`?type=ENTITY`, TYR-08), labelled by the dictionary display name of the name (EDT-04, DD-379 kept). The whole-typedefs dump (EDT-04) leaves the editor |
| VDE-03 | The tag box starts at the view's `classificationNames` — the entity's own tags, the answer already leaving propagated ones out (VDR-05, AVW-08), so the client's DD-326 filter retires. A save sends the box's full desired set as `classifications`. The door diffs it to add and remove calls and protects a propagated tag (AVW-08). The editor's POST-add plus one DELETE per removed tag (DD-326) retires                                                                                                                                                                                               |
| VDE-04 | The pickers seed from the view's `sections` (VDR-02's ends) under the EDT-15 rule kept (the ACTIVE ends that carry a guid, deduped keeping the first). A save sends, for each picker the form rendered, its full desired end list as a `sections` entry, each end its guid (AVW-09). The door removes an end a dropped entry no longer names (AVW-05). The `relationshipAttributes` merge of DD-340 retires for the door. A `meanings` picker sends its term GUIDs through the door's `meanings` key, not a `sections` entry, because a term assignment rides 5.2c's bookkeeping and not a plain edge        |
| VDE-05 | A save is one `POST /api/aurelius/v1/entity` (AVW-01, AVW-05). An update names the `updateTime` of the view it edited (AVW-04). A create names no guid and carries the qualified name the editor generated (DD-592); the answer's view carries the server's GUID (AVW-06). The temporary numeric GUID seed and the `guidAssignments` remap (DD-325) retire                                                                                                                                                                                                                                                   |
| VDE-06 | The mutation door's answers carry `sections` the way the read door does (VDR-02): the saved view and the conflict's stored view pass the entity's own ends (DD-604's batched read), so AVW-07's "the live view as 16.2's read door answers it" is true in full, and a re-edit has the entity's real ends and term assignments, not the document's stale pairs (DD-610)                                                                                                                                                                                                                                       |
| VDE-07 | A conflict (a 409 `ENTITY_VERSION_CONFLICT` beside the stored view, AVW-04, DD-591) re-edits from that view: the base the save merges onto becomes the answer's `view`, every control, tag and end the person left untouched answers the stored value, every one they changed keeps their value, one line says the entity changed since it opened, and a second Save rides the stored `updateTime`. There is no alert and no error page (DD-591's reload-and-reedit path)                                                                                                                                    |
| VDE-08 | A create whose qualified name a stored entity already holds answers a 409 `ENTITY_NAME_TAKEN` (AVW-06): one new line says the qualified name is already held, the drawer stays open, and the edits are kept (EDT-08's shape). No navigation runs                                                                                                                                                                                                                                                                                                                                                             |
| VDE-09 | Any other failed save (a refusal, a validation answer, a 403) answers one alert as EDT-08 left it (the existing save-failure line), the drawer open, and the edits kept. No navigation runs                                                                                                                                                                                                                                                                                                                                                                                                                  |
| VDE-10 | A save's success is the answer's live view (AVW-07, VDE-06): `stale` false and the new `updateTime`. The editor evicts the saved guid from the read cache (DD-605, VDR-07), fires the saved tick (DD-327 kept; the details screen re-reads as 16.5b left it), and lands on the entity's details (EDT-06 kept). The commit foot fills its outcome line from the tick (LR-005 kept)                                                                                                                                                                                                                            |
| VDE-11 | The delete (EDT-19) keeps its Atlas `DELETE .../guid/{guid}` path, because the door does not delete (16.3's scope). The quality branch keeps its vocabulary (DD-491) and validates its draft (EDT-28) before the door save. The governance banner (EDT-23/24, DD-446/DD-498) keeps its `AtlasEntity`-shaped draft through the aux validate API, seeded from the view plus the live field values and picks                                                                                                                                                                                                    |
| VDE-12 | The visible fields, strings, layout, and drawer of 7.7 and 7.9 stay as built. The new strings are the conflict line (VDE-07) and the name-taken line (VDE-08), each added to the bridge catalogue (both files). No other screen's calls change, and no Apache Atlas or App Search answer changes (AVW-12, R3, R4)                                                                                                                                                                                                                                                                                            |

## Aurelius origin

- ADR 064 (one shape, three doors): the mutation door this screen is built for,
  and its contract AVW-01..12 with DD-589..594.
- 16.5b (VDR-01..10, DD-605): the read door and its GUID cache the editor now
  shares, and VDR-05's own-tags chips the tag box matches.
- 7.7a-7.7c and 7.9 (EDT-01..28), 12.5 (EDT-25..28), 12.7 (EDT-23/24): the editor
  this increment re-sources.
- DD-325, DD-326, DD-340, DD-592, DD-593: the client mechanics this increment
  retires or replaces.

## Deviations

Against Apache Atlas: none new (AVW-12). The door's optimistic conflict (AVW-04)
replaces the silent last-write-wins the Atlas POST effectively is, and that is
recorded in 16.3's records (DD-591), not as a new deviation here.

Against the wire this editor leaves (intentional, its retirement road): the Atlas
entity GET becomes the read door's view (VDE-01). The whole-typedefs dump becomes
the for-type chain plus the classification and enum slices and the entity headers
(VDE-02). The entity POST and the tag POST-and-DELETE sequence become one door
POST (VDE-03, VDE-05). The `relationshipAttributes` merge of DD-340 becomes the
door's `sections` diff (VDE-04). The temporary GUID seed and the `guidAssignments`
remap of DD-325 retire on the real GUID the answer names (VDE-05, DD-592).

## Acceptance

- `apps/aurelius-atlas-server/tests/test__view_mutation.py`: the saved answer and
  the conflict's stored view carry the entity's read ends in `sections` (VDE-06),
  the term assignments among them under `meanings`; a create whose relationship
  attribute the type makes mandatory lands its edge through the body's own
  relationship attributes, and one without it stays refused (DD-613).
- `libs/angular/aurelius-atlas-data-access/src/lib/aurelius/view-entity.service.spec.ts`
  and the new `view-save.service.spec.ts`, `view-types.service.spec.ts`: the save
  client posts the door body and passes a conflict's `view` through whole, and the
  slice clients ask their routes (VDE-02, VDE-05..07). Each test names its rule
  id.
- `apps/aurelius-atlas-webapp/src/app/search/editor/editor-state.spec.ts`: the
  read through `ViewEntityService`, the save as one POST (edit and create), the
  conflict re-edit, the name-taken alert, a refusal alert, and the success tick
  and navigation (VDE-01, VDE-05..09).
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts`:
  the fields built from the for-type slice, the tag box seeded from
  `classificationNames`, the pickers seeded from `sections`, the meanings picker
  on the `meanings` key, and the governance draft (VDE-02..04, VDE-10).
- `apps/aurelius-atlas-webapp/src/app/search/editor/view-as-entity.spec.ts`:
  the entity folded from the answer (the `sections` rows among them) and the
  door body built from the rendered fields and pickers, plus the conflict
  re-seed helpers (VDE-04, VDE-07).
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp.py`: edits a seeded
  entity, creates an entity, tags an entity, links and unlinks a relationship,
  shows the governance banner, and hides the editor affordances from a reader.
  The two new scenarios cover a conflict (edit the same entity twice and re-edit
  from the stored view) and a name-taken create. Each scenario carries exactly one
  level marker. Run with `nx e2e aurelius-atlas-webapp` and `nx e2e
aurelius-atlas-server`.
