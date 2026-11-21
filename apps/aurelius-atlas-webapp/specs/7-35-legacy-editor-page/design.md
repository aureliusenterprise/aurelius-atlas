# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the Design Log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-816. The editor is a page again, not a drawer

- **Status:** Proposed
- **Increment:** 7.35
- **Date:** 2026-11-21
- **Supersedes:** 7.7a's drawer (EDT-01) and the editor's place in DD-166's drawer family

**Decision.** Create and edit are one page in the main outlet, `search/editor`, editing when its `guid` query
parameter names an entity and creating when it names none; full content width, as the legacy's pages were. The
legacy had two routes around the one editor; one page keeps one URL shape for both.

**Reason.** The forms have up to nine fields, most of them pickers with a column of verdicts beside them. In a
drawer they are squeezed into a third of the screen and the verdict column has no room; the user asked for the
legacy page back (2026-11-21), reversing the drawer chosen on 2026-11-03.

**Alternatives.**

- A wider drawer: still beside the page, still too narrow for two columns on a laptop.
- The legacy's two routes, `create-entity` and `edit-entity`: two URLs for one component, by user direction
  folded into one (2026-11-21).

**Consequences.** The settings and alerts drawers stay drawers. The editor loses the drawer's "page stays
behind" effect; Cancel returns to where the user came from.

### DD-817. One form per type, from a table in the webapp

- **Status:** Proposed
- **Increment:** 7.35
- **Date:** 2026-11-21
- **Supersedes:** EDT-03's every-attribute field set, for the ten types with a legacy form

**Decision.** The webapp holds one form definition per type: the fields, their order, labels, inputs and pickers
of the legacy form. The type definitions still say which attributes exist; the form definition says which of
them the editor shows and in which order.

**Reason.** The legacy forms were written by hand per type, showing the fields a steward fills and hiding the
rest (`typeAlias`, technical attributes). Deriving the form from the type definition shows every attribute,
ordered by label.

**Alternatives.**

- An order and a visibility flag in the type definitions: the metamodel would carry the editor's layout, for
  one screen.

**Consequences.** An attribute added to one of these types appears in the editor only when its form definition
lists it.

### DD-818. The parents keep disabling each other's picker

- **Status:** Proposed
- **Increment:** 7.35
- **Date:** 2026-11-21

**Decision.** Of two mutually exclusive parents, the second picker stays disabled while the first holds a pick
(18.3 PME-10, 18.5 DCP-05), not cleared as the legacy did.

**Reason.** Clearing a pick the user made, because they made another, loses data without asking; the server
refuses both together anyway (PME-07).

### DD-819. Types without a legacy form keep the generic form; the data quality rule keeps its own

- **Status:** Proposed
- **Increment:** 7.35
- **Date:** 2026-11-21

**Decision.** A type the legacy had no form for keeps today's generic form on the page; the create type select
lists the ten legacy types first. `m4i_data_quality` keeps 7.27's quality mode, though the legacy edited it with
the governance rule's free-text form.

**Reason.** The legacy listed those types and showed an empty form for them, which could only save a nameless
entity. A data quality rule here is a check from a closed vocabulary (DQ-01, DV-146); a free-text form would
store checks the scanner then marks ERROR (DQS-08).
