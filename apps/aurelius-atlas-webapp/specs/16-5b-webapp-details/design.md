# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an
accepted entry is never edited except its status line, and a changed decision is a new entry that
supersedes the old one.

## DD-604. The read door answers its entity's own relationship ends

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-14

**Decision.** `GET /entity/guid/{guid}` passes `ends` to `view_of`: the entity's ACTIVE edges,
read through the registry's relationship attributes and the graph helpers the 2.3 read uses, and
answered under the attribute name each edge belongs to, as `{guid, name, typeName, status}` —
AVS-04's merge clause, which no door has answered until now. The read is the entity document plus
one batched read of its ends: the store answers every end GUID of the entity in one `get_many`,
and a SINGLE-cardinality attribute's one object is listed like any other end. A stored derived
pair naming a read end loses its place to it; the pairs of unmated attributes stay. The dedupe
applies to the stored pairs only: two read attributes can name one entity at the same time — the
process that both feeds and produces a dataset (REL-17) — and each of them answers it, so one box
of the screen never empties another.

**Reason.** The screen's People box, person stats and section seeds key by relationship attribute
(`dataEntity`, `domainLead`), which only the entity's own edges know; the stored document's pairs
key by the end's type field and carry no attribute name. AVS-04 already names this source and
`view_of` already takes the parameter — the door never passed it. A batched ends read is not the
walk ADR 064 R1 rejects: one entity, its own attributes, one round.

**Alternatives.**

- The client keeps the Atlas GET beside the view: two reads for one screen, and the shape family
  splits again (fails R1, R2).
- The screen derives ends from `relations` pairs: pairs have no attribute name and no status, so
  the People box and stats could not key or filter (fails VDR-03).
- Recompute the derived document live: the rejected join of ADR 060, per open.

**Consequences.** The door's answer grows one batched read per open; the 2.3 read's helpers
(`relationship_type_name`, `edges_for_label`) are its shared machinery, so edge semantics cannot
drift. DELETED edges answer nothing, as the screen's EDT-15 rule already drops them — the client
rule stays and never fires. 16.5c's save answer can pass the same ends for the written entity.

## DD-605. The GUID cache lives in the door's client, not the page's store

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-14

**Decision.** The GUID-keyed view cache ADR 064 schedules lives in `ViewEntityService`
(`aurelius-atlas-data-access`, root-provided): the last 50 views by guid, an in-memory map that a
page reload clears. `view(guid)` answers a cached view synchronously and asks the door otherwise;
`evict(guid)` drops one entry. `DetailsState` (page-scoped) evicts on the editor's save tick
before re-reading (DD-327 kept), and the crumb and property links ride the same cached read. The
supersede of DD-318's "no cache" is ADR 064's own follow-up clause; DD-318's fetch states (the
guid guard, the loading line, the alert paths) stand untouched in the store.

**Reason.** Crumb and property links walk a chain a click at a time and a save's re-read asks for
the guid just opened: without a cache each step re-reads what the last answered. The cache must
outlive one screen to serve the walk, so it cannot live in a page-scoped store; and it must not
know the webapp's event types, so the eviction is the store's call, not the service's subscription.

**Alternatives.**

- The page store caches: dies with the screen, buys nothing for the walk.
- `shareReplay` on the request: keyed by nothing, or by the wrong key — the guid needs a real map.
- A TTL: the freshness rule (R7) says live-at-read; a saved entity is the only stale risk and the
  tick already covers it, so time adds a knob and no correctness.

**Consequences.** DD-318's posture is superseded for this screen's read only, by name; the Atlas
GETs and the bulk card read keep DD-318's rule. A saved entity opened in a second tab can show
its pre-save view until reload — accepted, session memory, marked in the service.

## DD-606. The trail fills DD-317's seam from the view, opened entity last

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-14

**Decision.** `DetailsBreadcrumbState` (DD-317's seam) stays and the screen fills it: on every
view arrival, `setTrail` with the view's `breadcrumb` (stored order, top down — each crumb's
name, or its type, or its guid) plus the opened entity's own crumb last, which the breadcrumbs
mark active through `activeGuid` (7.13's contract). Icons ride the app's type map, as the header
badge's do (DET-26); a type the map never saw gets no icon. The screen's binding and crumb
routing (DET-06) do not change — the seam's contract holds as written. An entity without a
document shows its own crumb alone; no entity shows nothing.

**Reason.** The seam was drawn for exactly this fill (DD-317's consequence: "a later increment
fills it from an endpoint's answer"), and the view now carries the trail the indexer stored
(LAS-04). The legacy trail ended with the opened entity itself — the `activeGuid` input's
contract — so the entity's crumb belongs to the trail, not to the component.

**Alternatives.**

- Drop the store, derive crumbs in the component: one seam deleted, DET-12's spec pair rewritten
  for no behaviour change.
- Leave the entity crumb to the component: the trail of a parentless entity renders empty under
  the component's guard, and a page shows no name above its own title.

**Consequences.** DET-12's "renders empty" pins flip to filled trails; the direct-visit case now
shows a trail too (the document carries it without any walk). The `breadcrumbtype` of an
unmapped crumb renders the raw name, as DET-26's badge does.

## DD-607. The chips answer the entity's own classifications

- **Status:** Superseded by DD-834
- **Increment:** 16.5b
- **Date:** 2026-11-14

**Decision.** The header's chips are the view's `classificationNames` (DD-090's stored field),
each by its dictionary display name — DET-09's rendering kept. Propagated tags stop showing: the
field holds the classifications the entity owns, and AVS's rule leaves the propagated names to
their source. The deviation is DV-166 in the ledger, in this increment's PR. The card bodies'
chips keep the bulk-read `classifications` and show propagation as today — their source is the
Atlas read, unchanged until 16.5c moves the card bodies.

**Reason.** The view answers one field set for every consumer (R2), and the read door's shape is
16.1's, fixed. The editor's box never let a propagated tag be edited (DD-326) and the mutation
door protects it from a save's diff (AVW-08): the tag is not the entity's to manage, and showing
it in the header promised control the screen never had. The detail GET's full classification
bodies were only ever read for their `typeName`.

**Alternatives.**

- The door answers propagated names too: a new field or a widened one, for a screen that cannot
  act on them — and the card and the trail would disagree with the editor.
- The screen keeps the Atlas GET for its chips: a second read per open for one chip row (fails R1).

**Consequences.** A field inheriting `PII` from its entity shows the chip on the entity's page
only, not on the field's; DV-166 says so. The unit pins that read `classifications` re-key to
`classificationNames`; the e2e chip scenario (EDT-05, a tag added to the entity itself) is
unaffected.

## DD-732. The Properties table reads the entity's own relationship attributes

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-20

**Decision.** `viewProperties` builds a link row only from a section whose ends carry a type or a
state. Those are the door's read ends, which AVS-04 answers as the entity's own relationship
attributes. A stored derived pair answers `{guid, name}` with neither, and earns no row.

**Reason.** A stored pair rides the card's derived search fields and is keyed by the end's type
name (AVS-02, LAS-05, LAS-06). DET-11 merges the entity's attributes with its relationship
attributes, and a type name is never one, so such a pair drew a row the Atlas GET never answered.
An m4i dataset whose field joins a data entity showed a row labelled `m4i_data_entity`, and the
Properties stat read one too many (DET-24, DET-32). The row hid before 90c4cf2 (#392) made a write
derive before it answered, because a just-seeded entity then had no document when the screen read.
Every relationship attribute the dictionary declares already sits on DET-11's blacklist, so a type
name is the only kind of key this guard can drop. The card's boxes read the pairs by attribute name
and keep every end they drew before (DET-17..DET-22, VCF-16).

**Alternatives.**

- The door drops the type-keyed pairs from `sections`: it also takes them from the card's boxes,
  which AVS-02 and VDR-02 pin, so it needs both rules amended.
- The table blacklists the nine `RELATION_FIELDS` names: it silences today's dictionary, and a new
  derived type name leaks again.
- The e2e expectation moves to `properties 1`: the row is visible on every such dataset, so it is a
  defect, not a test artefact.

**Consequences.** The Properties row count drops by one for an m4i dataset whose field joins a data
entity, which is what DET-11 and DET-32 ask for (DV-177's scenario returns to `properties 0`). The
editor's draft keeps the pairs under their type name (DD-608): the store ignores a key the type does
not declare, so a save cannot write one. A unit pin covers a derived pair on its own and beside a
read end naming the same GUID.

## DD-834. The header marks the propagated tags and names where they came from

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-23

**Decision.** The header's chip row carries both kinds, and the mark tells them apart (VDR-12):
the entity's own names ride plain chips (VDR-05), and each name propagation brought rides the
same row on the ui-lib chip's own propagated marker (UIC-16). The view answers the propagated
names in a field of their own, `propagatedClassifications`: one entry per name, each listing the
entities it came from (DD-835). The marker's dropdown names those entities, and a row routes to
that entity's details. A name whose source the store no longer has keeps its entry with no
entities: the tag stays the entity's to show, only its origin is unknown. This supersedes
DD-607's clause that propagated tags stop showing, and DV-166 with it (DV-197 in the ledger).

**Reason.** The legacy detail page split the entity's classifications by `entityGuid` and drew
the propagated ones as a labelled row (dashboardv2's `DetailPageLayoutView`). A user asked where
a tag on a field came from, and the screen had taken that answer away when 16.5b moved the header
to the read door. The split stays what the store models (DD-090's two search fields), so the
field carries it: the entity's own names never move, which is what the editor's diff and the
mutation door's refusal rest on (DD-326, AVW-08).

**Alternatives.**

- Widen `classificationNames` with the propagated names: the editor saves that list, so a save
  would try to attach a tag that belongs to its source (fails AVW-08).
- The legacy's separate labelled row: a second structure to seat, for what the Aurelius chip
  already marks and explains on hover.
- A second request for the propagated names: a second read for one chip row (fails ADR 064 R1).
- Group by name and count the sources, as the legacy's badge did: the legacy count answers
  "how many", the source rows answer "where from", which is the question that was asked.

**Consequences.** The door answers one field, grouped by name as the legacy's dedupe grouped it,
and its click-to-tag-page becomes a click to the source entity's details — the tag page is the
dashboard's, and the webapp has none. The ui-lib marker was hover-only Bulma (UIC-16); its trigger
becomes a button and the menu opens on focus, so the keyboard reaches the sources. DD-836 lets the
cards carry the same field, so a result line marks what its header marks.

## DD-835. The read door reads the propagated tags in one batched round

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-23

**Decision.** `read_propagations(store, stored)` (in `view_derivation`, beside `read_ends`) reads
the entity's classification instances once, keeps the ones whose `entityGuid` names another
entity, and reads those entities in one `get_many` (VDR-12). `view_of` takes the result as its
`propagated` parameter and groups it by name into the view's entries. The read route passes it,
and the mutation door's conflict view computes it the same way, so one answer shape serves both
doors. The editor never sends the field, and the mutation door's parse ignores what it does not
know, so a save round-trips it unchanged.

**Reason.** The stored entity already lists every instance it carries, own and propagated alike
(DD-090), so the split is one batched classification read and one entity read — the seam
`read_ends` set for the same reason (DD-604): one entity, its own tags, one round. Deriving the
sources from the stored pairs would key them by type name and lose the status the row shows, and
searching them would split one answer across two indexes.

**Alternatives.**

- Derive the sources from the view's `sections`: pairs are relationship ends, not tag sources, and
  a tag propagates over edges the entity never lists (PRO-04's walk).
- Answer the tag's own classification instances instead: they name the type, not the entity the
  tag rode in from, which is the fact the chip shows.
- Leave the mutation door's conflict view without the field: the screen's conflict editor reads
  the same view shape, and a field missing there reads as "nothing propagated" (fails R2).

**Consequences.** The read door grows two batched store calls per open. A name the store lists
whose instance document is gone answers nothing for that name, as the entity's own names already
behave. The trace check's rule ids gain VDR-12 on `view_of` and on `read_propagations`.

## DD-836. The search door fills the propagated tags, and a source row shows its path

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-23

**Decision.** The field moves to the shared shape: `propagatedClassifications` lives on
`EntityCard`, so `EntityView` keeps it through inheritance and every door that reads the tags
fills it (VDR-12). `read_page_propagations(store, stored)` reads a whole page in the same two
calls DD-835's single read uses: one `get_classifications` over the page's entities, one
`get_many` over their sources (DD-836). A source answers a `breadcrumb` next to its name, and
only when its document has parents. The webapp draws the chip and its source rows once, as one
part the header and the card mount: a row shows the source's type icon, its name, and the stored
path in place of the type name the first cut printed.

**Reason.** The review asked for the tags on the result lines too: a list is where a user first
sees a mark, and a card that hid it could only be explained by opening every row. A field on the
shared shape is the family's own rule (ADR 064 R2), and one part is the family's other: the same
entity cannot read differently on the two screens. The path replaces the type name because the
row's name is already the entity, its type is its badge on the card, and the question the chip
answers is where a tag came from. `breadcrumb` stays optional on a related entity so a section's
end and a parentless source answer exactly what they answered before (AVS-05).

**Alternatives.**

- A second request for the page's tags: 50 cards, 50 reads on every search page (fails ADR 064
  R1).
- A card-only field beside the view's: the same name in two places, and `EntityCard.of` would
  have to forget it (fails R2).
- The path under the name and the type kept: three lines per row in a menu as wide as its card.
- The card inventing its own row markup: the header's rows and the card's would drift the first
  time either was touched.

**Consequences.** A search page grows two store reads, whatever its page size. `EntityCard.of`
projects the field, so a view turned into a card keeps it and the mutation door's answer can lose
nothing. Every existing `RelationEntity` answer (a section's ends, a parentless source) stays
byte-identical because the new key appears only with real crumbs. The part's rows stop their click
from bubbling, so a source row opens the source and not the card it sits on. A tag whose source the
store lost still marks the card, and its dropdown names no row, as VDR-12 had already left it.

## DD-837. The source row's name is the button, and the path's crumbs are links

- **Status:** Proposed
- **Increment:** 16.5b
- **Date:** 2026-11-23

**Decision.** The part's source row becomes a container of two controls instead of one whole-row
button. The first line is a button holding the source's type icon and its name: it is what routes
to the source's details, the name clips with an ellipsis and carries the full name as its tooltip.
The second line is the path as one line of breadcrumbs with wrapping off and overflow clipped, and
each crumb is a real link that routes to its own entity (amends VDR-12 as DD-836 left it). The
wider menu uses Bulma's own lever, `--bulma-dropdown-menu-min-width` set to 20rem on the chip, so
the name and its path have room on one line each. Both controls stop their click, so a row on a
card routes without opening the card (DD-836's consequence stands).

**Reason.** The review previewed the menu and asked for wider rows, no line-splitting, and clickable
breadcrumbs. The row cannot stay a single button once its path holds links: HTML forbids a link
inside a button, and the app's accessibility lint forbids a click handler on a plain div. Giving
the name the button keeps the keyboard route to the source (VDR-12 asks for it), and real anchors
for the crumbs give it free to each crumb, which is what the details screen's own trail already
does (DET-06). Clipping both lines keeps one row one height, so a menu of five sources stays
scannable.

**Alternatives.**

- The whole row clickable again, crumbs as plain text: DD-836's first cut, superseded here because
  the review wants to open an intermediate folder, not only the source.
- A div row with its own click handler and restated hover, as the editor's token picker rows are:
  rejected, the picker's rows are listbox options with that semantics, and here they would be a
  button pretending to be a div (accessibility lint refuses).
- The trail kept with wrapping on: one source then takes three lines of menu and pushes the others
  out of view.
- Per-crumb tooltips instead of clipping: the tooltip would cover the next crumb, which is the one
  you hover next.

**Consequences.** VDR-12's sentence about what routes changes: the name routes to the source and a
crumb routes to its crumb, so the specs name both clicks. The row's hover no longer paints as one
Bulma item (Bulma styles only whole items), so the name button and the crumbs carry their own
hover. The menu is wider than a small card's dropdown was: on a card the menu opens over the next
card, which is what Bulma's `dropdown-content` positioning already handles.
