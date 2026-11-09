# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-424. The results store runs the quick search as one call, with `includeSubTypes`

- **Status:** Accepted
- **Increment:** 7.4b
- **Date:** 2026-11-08

**Context.** The 7.4a store posts a basic search (SRH-03), and the 7.4a deferral table
said the facet sidebar rides quick-search `aggregationMetrics` "a second call". Server
4.2b (shipped, QSR-01..04) answers the quick search as one call: the page of results
and the facet counts in the same answer, the counts aggregated from the search's own
query (DD-093). The client method and DTOs already exist (`SearchService.quickSearch`,
`AtlasQuickSearchResult`, APC-11). Swapping the endpoint replaces the basic search
rather than adding a request, but the two endpoints differ in two details the store
must carry: the quick-search model defaults `includeSubTypes` to `false`
(`QuickSearchParameters`, the Java `QuickSearchParameters` default), while the basic
search defaults it to `true` (SRC-01, `SearchParameters`), and the quick-search answer
nests the entities and count one level down, under `searchResults` (QSR-02).
The browse explore buttons filter on a supertype (DV-84: `AtlasGlossary`,
`Infrastructure`) and rely on sub-type inclusion — with `includeSubTypes` left out,
`explore("AtlasGlossary")` would answer only entities typed exactly `AtlasGlossary`
and SRH-08's listings break.

**Decision.** The store switches from `searchWithParameters` (POST `/search/basic`) to
`quickSearch` (POST `/search/quick`) and sends `includeSubTypes: true` always
(SDX-01). It reads entities and `approximateCount` from `searchResults` and the facet
counts from `aggregationMetrics` of the same answer (SDX-02). No second call exists
anywhere in the slice; every page's answer refreshes the facet signal, which DD-093
makes stable because the counts are unpaged. SRH-03 and SRH-08's transport are
amended in place by SDX-01, their screen rules (paging, cards, explore filters)
unchanged.

**Alternatives.** (a) Keep the basic search and add a quick-search call per search for
the counts — refused: two requests for one query, and the second re-runs the same
match work DD-093's single aggregation exists to avoid. (b) Send the GET form of the
quick search — refused: the POST body is the validated route the client already uses
for the basic search (SRC-02/QSR-01), the GET form skips validation (the legacy
header-search-bar reading), and the POST is what the data-access service's
`quickSearch` wraps. (c) Rely on `includeSubTypes` being absent — refused: the model
default is `false` (the Java default ported), unlike the basic search the store used
until now; the difference is exactly the kind DD-217's "the client sends an absent
field as its absence" rule surfaces, and the explore listings prove it.

**Consequences.** The 7.4a deferral row's "a second call" wording is superseded by
this record (the row's own pointer said 7.4b decides). The store's `load()` reads one
answer for both signals; the alerts path (the DD-214 failure strip) is unchanged
because the error shape is the same typed Atlas error (APC-04). The quick search
appends `*` to a query without a tokenising character (QSR-02), a small relevance
change under the same words: `data` now matches `database` too, the legacy prefix
behaviour App Search had. The e2e's seeded names stay single-word run-unique tokens,
so the change cannot destabilise them.

### DD-425. The facet selection stays session state, the URL rule DD-219 reserved for 7.4b

- **Status:** Accepted
- **Increment:** 7.4b
- **Date:** 2026-11-08

**Context.** DD-219 made `search/results?query=` the screen's whole URL and recorded
that "7.4b will record its own decision for filter parameters when filters exist to
name". The legacy app is the reference for what exists: its facet toggles rode the
in-memory App Search store, never the URL — a deep link could carry the query and
nothing else. A modern reading would put the selection in the URL (shareable,
back-button-correct), and the repo does prefer URL state where the legacy had it
(7.6's DET-07). But the legacy never had a filterable URL here, inventing a parameter
grammar DD-219 already refused once as speculative design, and the store's lifetime
rule (SRH-02: leaving the subtree destroys it, the legacy `NavigationEnd` reset) is
itself the reset behaviour a URL parameter would complicate (a link pasted with
`&typeName=` would resurrect a selection the legacy gives you only by clicking).

**Decision.** The facet selection is session state in the layout-scoped store
(SDX-06), exactly the explore buttons' filter rule (SRH-02/SRH-08) generalised: the
hero submit clears it, a URL query change keeps it, leaving the subtree destroys it.
`?query=` remains the screen's whole address; DD-219 stands unchanged.

**Alternatives.** (a) `?typeName=a,b` in the URL — refused for now: the grammar has no
legacy source, and DD-219's refusal reason still holds. (b) Keep a separate list from
the explore filter — refused: both are the same wire field (`typeName`, SRC-03's
comma list), and two signals for one field re-create the sync bug SRH-08's "submit
clears filters" rule exists to prevent. The selection _is_ the filter list; the
explore button sets it to one value, a checkbox toggles membership.

**Consequences.** SRH-02's sentence "filters ... are session state" gains its first
real filters without changing. A back-navigation into the subtree after visiting
browse resets the selection (store destroyed), which is the legacy behaviour. When a
future slice wants shareable filters, it supersedes this record and DD-219 together.

### DD-426. Only the type facet filters; narrowed counts keep seen values visible

- **Status:** Accepted
- **Increment:** 7.4b
- **Date:** 2026-11-08

**Context.** The legacy sidebar was all-checkboxes because every App Search facet was
a query clause the client could add. The quick-search contract (QSR-01) takes one
narrowing field, `typeName`. `__state` has no parameter (the store always sends
`excludeDeletedEntities: true`, so the facet answers `ACTIVE` alone — the colleague's
run confirms it); `Asset.owner` maps to no filter either, and the sample data sets no
owner, so it answers empty; `ServiceType` is derived from the type counts (QSR-04) and
is not a searchable field of the quick search. The second problem is counting: Atlas
counts the entities its _whole_ query matches (QSR-03, DD-093), so after ticking
`m4i_data_domain` the type facet answers that one type alone. The legacy
self-faceting (a facet's own field excluded from its own counts) showed every value
under the tick; App Search did it, Atlas quick search does not, and the server is
parity-locked (ADR 046, QSR-03's scenario pins it). A naive UI would then show a
single checked row and no way back except unticking it — the colleague's run saw the
same narrowing.

**Decision.** Only `__typeName` is interactive (SDX-04); `__state`, `Asset.owner`, and
`ServiceType` render as read-only count rows (SDX-05, DV-143). The sidebar keeps a
per-query _seen set_ of type values in the store (SDX-07): each answer updates the
counts it carries, and a value the narrowed answer no longer carries keeps its last
count and stays listed (unchecked, clickable). Unticking restores the broad answer,
whose counts refresh everything. The seen set resets on query change.

**Alternatives.** (a) Render only what the server answers — refused: ticking the last
visible row leaves a checked row alone in the menu, and unticking needs a click on
the row the UI just hid; the sidebar becomes a trap. (b) A second facet query without
the type clause (App Search's self-faceting emulation) — refused: a second request
per search against the DD-424 one-call rule, a client-side reinterpretation of
QSR-03 the parity rules forbid inventing for a UI convenience, and the counts it
shows would then disagree with the results beside them. (c) Radio buttons (single
select) — refused: the wire supports a list (SRC-03), the legacy was a checkbox
multi-select, and a radio cannot un-narrow without a dedicated "clear" control the
legacy has none of. (d) Drop `__state`/`ServiceType` from the sidebar entirely —
refused: the legacy showed every non-empty facet the answer carried (the
`filter.component.html` loop), and they are free information (the state row is the
user's proof that deleted entities are excluded).

**Consequences.** The store grows one small signal (the seen type values and their
last counts, keyed by the live query text). DV-143 records both halves (narrowing,
read-only) against the legacy product. A future server slice that adds facet
parameters (a state filter, an owner facet with data) can make those rows
interactive without touching the component's contract (UIC-34's `selectable` flag
already carries it).

### DD-427. The sidebar ships as one dumb ui-lib component with four new bridge keys

- **Status:** Accepted
- **Increment:** 7.4b
- **Date:** 2026-11-08

**Context.** The legacy sidebar is three components (`filter`, `facet`, `check-box`)
plus two store services, but the Aurelius shape (UIC rules, 7.2) is dumb ui-lib
components with `input()`/`output()` and app-owned state — the `check-box.service.ts`
store pair is exactly what WBP-02's purity gate removes. The 7.4a note already
assigned "a new ui-lib component" to this slice. The strings are the second question:
7.4a required zero new catalogue keys (SRH-10), but the legacy facet titles were App
Search field names (`typename`, `supertypenames`, `sourcetype`, keys the vendored
dictionary does carry) while this server answers Atlas field names (`__typeName`,
`__state`, `Asset.owner`, `ServiceType`) with no dictionary key anywhere, in either
catalogue or legacy app.

**Decision.** One ui-lib component, `facet-list` (UIC-33..35), rendering every facet
(menu label, rows, counts, show-more, selectable flag); the app's results component
maps the store's facet signal to its inputs, as it already maps cards. The four
facet titles get new bridge keys (`search.components.filter.type`, `.state`,
`.owner`, `.serviceType`) entered in both fixture catalogues and regenerated through
the DD-128 bridge, the way 7.7a's `search.createEntity.newEntity` did; SRH-10's
"no new keys" is scoped to 7.4a and ends here. Show-more/show-less and the shell text
reuse the existing keys (they exist in both locales already). Type values render
through `nameDisplay` (DD-379's map, the card badges' rule), so a ticked
`m4i_data_domain` reads "Data Domain" in the row and sends the raw name.

**Alternatives.** (a) Port all three legacy components — refused: `facet` and
`check-box` differ only by one flag here, two more public APIs and stories for it;
(b) an app-local component, no ui-lib — refused: the 7.4a deferral row assigns the
component to the ui lib, and a facet list is catalogue chrome in exactly the sense
`entity-card` is; (c) render the raw field names as titles, zero new keys — refused:
"__typeName" and "Asset.owner" as menu labels are not shippable text, and SRH-10's
reason was coverage (both locales prove every used id), not a ban on growth;
(d) reuse `@@typename` for the type title — refused: it means "Type Name" (a field
label), it carries no Dutch counterpart for the sidebar's use, and one word, one
meaning rules the catalogue too.

**Consequences.** `aurelius-atlas-ui` grows one component on the UIC series with the
UIC-35 story; the app adds four keys to `tests/fixtures/en-US.json` and `nl-NL.json`
and regenerates `src/locale/*.xlf` (never hand-edited, the bridge rule). The SHL-08
completeness gate is the guard that both locales land in the same PR.
