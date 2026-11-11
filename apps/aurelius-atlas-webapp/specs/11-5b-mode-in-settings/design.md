# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-473. The search mode is a stored setting in the settings panel

- **Status:** Proposed
- **Increment:** 11.5b
- **Date:** 2026-11-11
- **Supersedes:** DD-478

**Decision.** The settings panel chooses Words, Meaning or Both, in a Search by section after Language.
`SearchModeService` stores the choice in the browser, as `PageSizeService` stores the page size, and the
settings facade drives it (DD-160). The results store reads the mode from it and, through its `changed`
stream, searches the shown query again when the mode changes. The URL keeps carrying the query only.

**Reason.** Users choose how they search once, not per search; the switch under the field took a row of the
hero for a choice that rarely changes. A stored setting survives the session, as the other settings do. The
store hears the change through a stream, not an effect on the signal, so a mode read at start-up searches
nothing, and only a choice the user makes restarts the search.

**Alternatives.**

- The switch under the field (DD-478): a row of the hero for a choice made once.
- A `?mode=` parameter: as DD-478 said, a URL that differs by how, not what, was searched for.

**Consequences.** A shared link opens in its reader's own mode. A server without search by meaning stores Words
(SBW-06), so the panel and the results agree. Opening and closing a drawer keeps the URL's query
(SBX-04): before, the drawer's links and its close dropped it, and the results behind the panel would list every
entity instead of the search whose mode changed.

### DD-474. No Similar entities box on the details page

- **Status:** Proposed
- **Increment:** 11.5b
- **Date:** 2026-11-11
- **Supersedes:** DD-480

**Decision.** The details page shows no Similar entities box; its component and its four labels are removed.
`SearchByMeaningService.similar` and the server's `/entity/guid/{guid}/similar` stay.

**Reason.** A box on every details page is noise for a reader who came for that one entity. The endpoint costs
nothing while unused, and a later screen can call it when it is asked for.

**Alternatives.**

- The box behind a setting: a setting for a box nobody asked to keep.

**Consequences.** The details page is as it was before 11.5.
