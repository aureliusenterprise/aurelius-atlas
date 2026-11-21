# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-816. The history rides the editor drawer, not the details screen

- **Status:** Proposed
- **Increment:** 7.35
- **Date:** 2026-11-21

**Decision.** The entity's change history opens inside the editor drawer, as an
Entity/History tab pair, in edit mode only. The drawer's `drawer-subhead` slot
carries the pair (DD-180), the Entity pane holds the form as before, and the
History pane holds the audit list. The audit read fires on every switch to the
History tab, never while the form is shown. The commit foot (Save, Delete)
renders in the Entity pane only. The pair is full width and the halves split
evenly, like the lineage pair: `is-fullwidth` (DD-402) with a zero flex basis,
`width: 100%` on the native buttons so label and underline centre (Bulma's own
rule targets `<a>` only, FORM-CUSTOM-002), and `flex-shrink: 0` on the strip so
the hairline under the tabs cannot shift over a long body (DD-416).

**Reason.** The legacy app had it exactly this way: `editor.component.html`
swapped the form for the audit list through `currentTab`, and the foot rendered
on the entity tab only. The user asked for "the history tab in the editor", and
the increment that 7.7a deferred it to (7.9) names the same place. A details-
screen placement would be a new product surface the legacy never had. Keeping
the read behind the tab keeps the drawer's open cheap: a person who edits reads
the audit trail only when they ask for it.

**Alternatives.** A History section on the details screen (where the audit
would be visible without opening the editor): refused, the legacy had no such
section and the details screen's layout is frozen by DET's spec rows. A
server-sent live trail that updates while the drawer is open: refused, no Atlas
screen had one and the read is a plain request. A route segment for the tab
(like the editor's type, DD-330): refused, the legacy held it as plain
component state, and no link or reload needs it here.

### DD-817. The audit read rides the drawer on the Atlas client, not the view doors

- **Status:** Proposed
- **Increment:** 7.35
- **Date:** 2026-11-21

**Decision.** `EntityEditor` calls `AtlasEntitiesService.getAuditEvents(guid)`
directly and keeps the result in a component signal. The query stays empty, so no
parameter travels and the server answers its newest 100 events in newest-first key
order (AUD-08). The read does not move into `EditorState`, and it does not ride the
16.5 view doors (`/api/aurelius/v1/...`).

**Reason.** `EditorState` is the store of the view-door plumbing: the read, the
chain, the tag box, the pickers, the save and its conflict (VDE-01..VDE-10). The
audit trail shares none of it: no caching rule applies (HST-03 re-reads on every
switch), no conflict path exists, and no other screen reads the same signal. A
component signal is the smallest home, and the drawer already owns its entity read
(EDT-02, DD-322). The endpoint stays the Atlas v2 one because the doors carry no
audit route: the read is not a view, and VDE-11 set the precedent that a read
outside the doors stays an Atlas endpoint. The client call and the
`EntityAuditEventV2` DTO already exist (AEN-05, 8.17), so nothing is added to the
data-access layer.

**Alternatives.** The read in `EditorState`: refused, it would grow the store with
state no sibling uses. A paged, infinite-scroll list: refused, the legacy
page-fetched the whole trail and no product need asks past the newest page; the
limit is recorded as DV-190. A `startKey` Load-more button: refused, nothing in the
product asks for it and HST-03's re-read keeps the newest page correct instead.

### DD-819. A re-read clears the audit list before it starts

- **Status:** Proposed
- **Increment:** 7.35 (a fix, 2026-11-21)
- **Date:** 2026-11-21

**Decision.** `loadAudits` empties the audit list when it starts a read, beside
setting the loading flag (HST-05, HST-06).

**Reason.** HST-03 re-reads the trail on every switch to History, and 7.35 as
written left the previous answer in the signal while the new read ran. The pane
showed the loading line above the old rows for as long as the read took, which
reads as a screen that has both loaded and not loaded. Every other loading pane
in the app hides its content while it loads — the details page asks
`state.loading() && !entity()`, the quality fields switch on their loading
state, the editor's form hides through `formVisible()`, and the browse store
clears its entries on a restart (SRH-04). Clearing once at the start of the read
gives the History pane the same shape, and it also makes a failed re-read leave
the list empty, which HST-06 already required.

**Alternatives.** Keep the rows and hide the line while data exists: the reader
would see no sign that the list is stale, and a slow re-read looks settled.
Gate the rows on `!auditsLoading()` in the template: the same screen, with the
pane's data signal now lying about what is shown.

**Consequences.** A switch to History shows an empty pane with the line, then
the rows. The read's own answer is unchanged, and the in-flight guard means an
empty pane never shows a second request.
