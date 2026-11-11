# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

Until 2026-11-11 these entries were numbered DD-444 to DD-447, the numbers 7.24 had already claimed in a
parallel branch; they are renumbered DD-478 to DD-481, and their content is unchanged.

## Entries

### DD-478. The search mode is the session's choice, under the field, not in the URL

- **Status:** Superseded by DD-473 (11.5b)
- **Increment:** 11.5
- **Date:** 2026-11-10
- **Supersedes:** none

**Decision.** A three-button switch under the search field chooses Words, Meaning or Both. The results store
holds the choice for the session, as it holds the type selection; the URL keeps carrying the query only.

**Reason.** The URL's state is the query alone (DD-219), and the facet selection stayed out of it for the same
reason (DD-425): a link names what was searched for, the screen remembers how. Under the field, the switch is
where the search starts, in a row of its own so the field and the create button keep the title row's width
(beside them, it pushed the create button off a 1,280-pixel screen); three buttons show all choices at once,
where a menu would hide two.

**Alternatives.**

- A `?mode=` parameter: a URL that differs by how, not what, was searched for.
- A setting in the settings panel: a choice made once, far from the field it changes.

**Consequences.** A shared link opens in Words until its reader switches.

### DD-479. In the meaning modes, a full page asks for the next one, and the header counts what is shown

- **Status:** Proposed
- **Increment:** 11.5
- **Date:** 2026-11-10
- **Supersedes:** none

**Decision.** In Meaning and Both, the list asks for another page while the last one was full and fewer than
1,000 entities are shown, and the header counts the entities shown, as closest matches.

**Reason.** A search by meaning answers the `offset + limit` nearest, so its `approximateCount` is the number
asked for, not a number of matches (SBM-02): the quick search's rule, all loaded once the list reaches the
count, would stop after the first page, and "10 results" would claim a total that does not exist. The server
answers at most 1,000 (DD-441).

**Alternatives.**

- The quick search's count and rule: one page only, and a wrong total.
- A count of every entity with an embedding: a number of no use to the reader.

**Consequences.** The facets count over the entities loaded so far, and grow as the list does.

### DD-480. Similar entities is a box of its own on every details page, after the card sections

- **Status:** Superseded by DD-474 (11.5b)
- **Increment:** 11.5
- **Date:** 2026-11-10
- **Supersedes:** none

**Decision.** A component fetches the 6 entities nearest to the shown one and renders them as the details page's
entity cards, in a box after the layout's card sections and before the properties. It owns its own fetch and its
states, as the Lineage Model box does (DD-388), and renders nothing on a server without search by meaning.

**Reason.** The card sections are per m4i type and read relationships (DET-17); nearness applies to every entity,
of any type, so it is one box beside them, not a section in each layout. Six fill two rows of the three-across
grid (DD-377). A box that cannot work on a server leaves no empty frame.

**Alternatives.**

- A section of each layout: eight entries for one box, and none for the types without a layout.
- A paged list: the nearest few are what helps; the search by meaning goes further.

**Consequences.** The box asks once per details page; an entity not yet embedded shows a note until the next
visit.

### DD-481. The client of Aurelius's own endpoints is a service of its own in the data-access library

- **Status:** Proposed
- **Increment:** 11.5
- **Date:** 2026-11-10
- **Supersedes:** none

**Decision.** `SearchByMeaningService` lives in `src/lib/aurelius/` of `aurelius-atlas-data-access`, beside the
Atlas clients (`atlas/`) and the auxiliary APIs' (`aux/`), and builds its URLs from `API_BASE_URL` with the
`/aurelius/v1` prefix.

**Reason.** The endpoints are the server's, under the same base as Atlas's (DD-440), so the same base URL and
authentication interceptor serve them; they are not Atlas's, so `SearchService`, the client of `DiscoveryREST`,
stays a client of Atlas only.

**Alternatives.**

- Two methods on `SearchService`: Atlas's client calling an API Atlas does not have.

**Consequences.** Later Aurelius endpoints join the same folder.
