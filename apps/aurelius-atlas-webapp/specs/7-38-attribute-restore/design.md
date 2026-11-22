# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-822. The restore writes one attribute, and the form follows the conflict merge

- **Status:** Proposed
- **Increment:** 7.38
- **Date:** 2026-11-22

**Decision.** The restore button of a changed attribute row sends one
single-attribute write — `AtlasEntitiesService.partialUpdateAttribute(guid,
value, name)` — with the old value the change list shows (EWR-15). The success
path drops the entity from the read cache, re-reads it through the read door,
and merges the stored view into the form with the same helper the save conflict
uses (`valuesAfterConflict`, VDE-07). The editor's existing write-bus effect
fills the status line, and the drawer keeps the pane and the open row the
person was reading. A refusal alerts once and changes nothing. No hold-to-
confirm applies, and no new store or service enters the editor.

**Reason.** The wire already has the narrowest write the product needs:
`PUT /api/atlas/v2/entity/guid/{guid}` with a `name` parameter sets exactly one
attribute (EWR-15), and the server refuses anything but a primitive or a
reference, which is the boundary this increment shows the person — a row with
a text, number or boolean old value can go back, and every other row cannot.
Keeping the drawer open is what the screen is for: the person came from a
change list, so a Save-style navigation would drop them off the page they were
reading. Staying open also rules out the dangerous shape, because the form
holds unsaved edits when the write lands. The conflict merge answers that
combination with code the app already ships and tests: an untouched control
answers the stored entity, a touched one keeps its value (DD-610). Re-seeding
the whole form instead would silently throw away edits the person never asked
to lose. The audit trail re-reads on the next History visit (HST-03), so the
row's button disappears without a second write, and the change list never
claims a restore that did not reach the store. Alerts answer a failure the way
the audit read answers one (HST-06): one error, drawer open, no navigation.

**Alternatives.** A hold-to-confirm button, like the delete (EDT-19): refused,
the restore writes one attribute, the old value stays visible in the change
list, and pressing restore again on the new row puts the value back, so the
house 3-second hold costs more care than the action needs. Navigating to the
details screen after a restore, like Save does (VDE-06): refused, it abandons
the change list the person opened and discards unsaved edits in other fields.
Sending the whole entity through Save with only that one attribute replaced:
refused, it writes every field the person may have mid-edit changed, and Save
navigates. Rolling back client-side without a write: refused, the store would
still hold the wrong value, and the next read would undo what the screen just
showed. A server-side restore endpoint: refused, `PUT .../guid/{guid}` already
does the job (EWR-15) and the Java surface has no such endpoint.
