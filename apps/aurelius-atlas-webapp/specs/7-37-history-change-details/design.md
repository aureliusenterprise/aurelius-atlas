# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-821. The client diffs the stored audit bodies

- **Status:** Proposed
- **Increment:** 7.37
- **Date:** 2026-11-22

**Decision.** The change list of an audit row is derived in the webapp. A
helper parses the row's `details` string — the action's prefix and the entity's
JSON the listener stored (AUD-03) — into the entity state the event carried,
and a differ compares that state with the state of the nearest older row in the
loaded trail that carries one. The result is a list of attribute changes
(changed, added or removed, each with the values it needs) and relationship
changes (added or removed, matched by the end entity's GUID). The component
keeps a set of open rows, and renders a row's list from a computed map built
over the loaded events. The webapp sends no request for a change list.

**Reason.** The audit wire already carries the answer. `audit_detail` writes
the entity's whole JSON into `details` for the four entity-state actions, so an
event holds its own after-state, and the newest-first order (HST-03) means the
event before it in the trail is the one the write replaced. Parsing and
comparing that text costs one pass over the events already on screen and no
new wire contract, and the store stays exactly as Atlas defines it (AUD-06).
The two shapes a cut-down body can have stay visible instead of guessed:
AUD-04 drops `attributes` above the size cap, which the helper reports as
`partial`, and an event older than the loaded window has no comparison pair,
which the row reports as "not loaded" until a next page brings the pair
(HST-08). A create is compared with the empty state, because the entity did
not exist before it. The UI library's `Accordion` is a card header and does not
fit inside a Bulma media row, so the row keeps the disclosure shape the
editor's combobox already uses: a plain button with `aria-expanded` and the
accordion's `aria-controls` pairing (FORM-CUSTOM-001) over a region that exists
only while open.

**Alternatives.** A server-side diff endpoint: refused, Atlas's audit surface
has no such endpoint, its own dashboard shows no diff, and one screen does not
earn a new API the Java server does not have. Diffing the row against the
entity as it is now: refused, it answers "what differs from today" rather than
"what did this event change", and any row but the newest would show later edits
as its own. Writing a per-event attribute delta in the listener: refused, it
changes the stored wire (AUD-03, AUD-04) and cannot fill the events already
stored, while the parse gives the same answer for old and new events alike.
