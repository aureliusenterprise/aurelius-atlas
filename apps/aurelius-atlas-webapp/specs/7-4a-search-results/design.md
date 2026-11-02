# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-218. 7.4 splits in two, and the search bar lands in the hero; the list is infinite scroll

- **Status:** Accepted
- **Increment:** 7.4a
- **Date:** 2026-10-26

**Context.** The 7.4 row ("Query and results, the first slice with real data")
grew into the collection point of three deferrals: the results screen itself,
the browse cards' affordances (DD-143), and the Shell's search chrome (DD-145).
AGENTS.md caps an increment at roughly 1,500 production lines and says to split
before coding. The reading of the legacy app (`.scratch/aurelius`, the
`Aurelius origin` citation of 7-0) settled two UX questions the roadmap row
left open. The search bar: DD-145's wording ("the global search bar ... join
7.4") reads like a navbar feature, but the legacy navbar's start slot renders
one button per visible top-level route, and Atlas's only such route is
`hidden` — the legacy navbar carries **zero** nav buttons, and the search input
lives in the hero of the search subtree (`search.component.html`, the
`simple-search-input` above the routed content). The list: the legacy results
screen is an infinite scroll (a sentinel `IntersectionObserver` over the
results box, a "Load next page..." button as the keyboard/no-API fallback,
pages appended, page size 10), not a paged grid — the ui-lib `pagination`
component has no legacy results-screen to wire to.

**Decision.** Split 7.4 into **7.4a Search results** (this increment: the hero
with the search field, the results route and screen, infinite scroll, the
results → details entry, the browse affordances of DD-143, the sticky
navigation bar of DD-145) and **7.4b Search discovery** (facets from
quick-search `aggregationMetrics`, typeahead suggestions, advanced filters —
the parts with no legacy equivalent, so the slice that invents UX ships
separately from the slice that ports it). The search bar lands **in the hero**,
the legacy fact; DD-145's navbar wording is superseded, and the navbar's
start slot stays empty because Atlas shows no nav buttons. The results list
keeps **infinite scroll** (UIC-21..23 port the container); `Pagination` stays
unused on this screen. The split line is the discovery boundary: 7.4a answers
"type and see", 7.4b answers "narrow down".

**Alternatives.** (a) One 7.4 increment — refused: ~2,500 production lines
against the 1,500 budget, and it welds the ported screen to net-new facets;
(b) split results | entry points (header bar + browse cards) — refused: the
affordances without their destination screen are exactly the half-wired slice
DD-143 defers, and the e2e flow (card → results → details) cannot split across
PRs; (c) a paged grid with the existing `Pagination` — refused: the legacy
infinite scroll **is** the product UX (the user named it), and DD-140's
redesign licence covers the wire (App Search → `/v2/search/basic`), not the
screen; (d) a navbar search bar per DD-145's literal wording — refused: the
legacy source shows the bar in the hero, and DD-145's own reasoning is "the
header's centrepiece is the global search bar" — in Aurelius Atlas, as in the
legacy app, that centrepiece is the search hero.

**Consequences.** The roadmap row splits; DD-217's "7.4 consumes `SearchService`
directly" rides unchanged. The sticky navigation bar (DD-145's deferred half)
lands with 7.4a, closing the Shell chrome deferral. 7.4b carries its own spec
and rule ids (SDX) with the typeahead design it has no legacy copy of. The
ui-lib grows one dumb component (the infinite-scroll container) on the UIC
series; `Pagination` remains in the library for the screens that page.

### DD-219. The results URL carries the query only

- **Status:** Accepted
- **Increment:** 7.4a
- **Date:** 2026-10-26

**Context.** The legacy resolver reads one URL parameter (`query`) and leaves
filters, sort, and the accumulated pages in the in-memory store; navigating to
browse wipes the store. A modern reading would put page/sort/filters in the
URL (shareable, back-button-correct), and the 7.6 details screen already made
the URL the screen's whole state. But 7.4a ships no facets (7.4b) and no sort
control (the legacy results screen has none — ordering is relevance, the
server default), so the parameters to share do not exist yet on this screen.

**Decision.** `search/results?query=` is the whole URL contract of 7.4a
(SRH-02, SRH-08): the deep link carries the query, the store carries pages and
the explore buttons' type filters, and leaving the subtree destroys the store
(provided by the layout component) so a fresh browse visit resets the search —
the legacy `NavigationEnd` reset, by construction. 7.4b will record its own
decision for filter parameters when filters exist to name.

**Alternatives.** (a) Query + page + sort + filters in the URL — refused for
7.4a: inventing a parameter grammar the legacy app lacks, for state this slice
does not expose, is the speculative design DD-140 refuses; the grammar lands
with the controls, in 7.4b. (b) Path-based `search/basic/:queryText` (the
Atlas dashboard's shape) — refused: the Aurelius product (the port's origin)
uses the query-parameter form (ADR 046 keeps the dashboard's REST contract, not
the dashboard's routes; 7.x ports Aurelius's UI).

**Consequences.** The e2e deep link is `search/results?query=…`; the back
button re-runs the query (the resolver's `paramsOrQueryParamsChange` contract,
SRH-02). The store's page accumulation needs no URL mirror, and the spec's
"the URL is the screen's state" line is scoped to the query — the 7.6
skeleton's stronger rule (DET-07) applies to the details screen, where the
guid is the entity's address.

### DD-220. The demo pass restores the search screens' legacy chrome: title, typography, shell and plate

- **Status:** Accepted
- **Increment:** 7.4a
- **Date:** 2026-10-26

**Context.** The 7.4a code review compared the running webapp side-by-side with the
legacy Aurelius demo (the `.scratch/aurelius` origin, rendered at
`google.aurelius-atlas.com/demo/atlas`) on the browse, results, and no-results screens.
The geometry (hero, container inset, two-column shape) matched; seven details did not,
each verbatim in the legacy source: the hero's title is the literal `"Atlas"` the legacy
`search.component.html` hard-codes as `title="Atlas"` — not the app name (the first port
rendered `appName` into it); the filter shell's empty state is the legacy `#noFilters`
block, a `div.content` around `p.is-italic.has-text-centered` (the first port shipped a
bare paragraph); the count header is `h6.title.is-6` **inside** the
results box (the first port floated it outside, unstyled); the 80vh cap sits on the box
(`.box { height: 100%; max-height: 80vh }`) with the inner `.results-container` as the
scroll owner (the first port scrolled the box itself); the no-results state is the
legacy `#noData` twin — a `.card` at the **top level**, replacing the whole two-column
block (filter shell included), its `card-content` centered by the legacy
`text-align-last: center`, message `p.title.is-4`, advice `h6.title.is-6` (the first
port shipped a small `.box` inside the results column); each result row is a Bulma
`.column`, whose 0.75rem padding is the gap between cards; and every search field
carries the `ControlShell`'s left icon plate (`context.icon` = `faSearch`,
`icon is-left has-text-info` — cyan on the demo), which the DD-135 port of
`simple-search-input` dropped with the rest of the shell.

**Decision.** Port all seven verbatim: the hero title is the literal "Atlas", the
filter box's empty state is the legacy `content`/`is-italic`/`has-text-centered`
paragraph, the count moves inside `.results-box` as
`h6.title.is-6`, the box/container split takes the legacy rules, `.card.no-results-card`
replaces the columns (the `ngIf`/`ngIf:else` shape — SRH-06's pair, SRH-07's shell
shown only with data), each row is the legacy `div.column` wrapping the card (the
column's auto height keeps the card host's `min-height: 100%` inert — stretched to the
scroll container's definite height, the cards inflate to one per screen; its 0.75rem
padding is the gap between rows), and the ui-lib `search-field` renders the left plate
(its UIC-01 markup set, completed).

**Alternatives.** (a) Keep the first port's cleaner shapes — refused: the legacy
look is the product look (DD-150/152), and the demo is the parity oracle (ADR 052);
(a reader comparing screens notices all seven). (b) Port the demo's centered **card**
titles — refused: that is the demo's stuck "Loading …" per-card-GET state (DV-83's
target: the demo's search answers never resolve there); with cards rendered from the
hit, the legacy centered line applies only to the no-results card, as ported.

**Consequences.** The 7.4b facet sidebar fills the shell that only shows with data;
the `search-field` story and its specs name the plate; the results specs pin the
count-inside-box and the top-level `#noData` (no `.column` without data); the layout
spec pins the hero's "Atlas" title, the results spec the styled no-filters paragraph.

### DD-221. The empty query lists every entity through the `_ALL_ENTITY_TYPES` marker

- **Status:** Accepted
- **Increment:** 7.4a
- **Date:** 2026-10-26

**Context.** Opening the results screen without a query (`/search/results`, the
URL the explore buttons land on, a bookmark, a reload) showed the no-results card
with the invitation to "try another query". The legacy app answers that URL with
everything: the Aurelius `QueryResolver` defaults `query` to `''` — "so that when
we load the page without a search term, we can still see results" — and the demo
answers the bare URL with 683. SRH-02's wording already says the empty parameter
"searches `""`, which answers"; the store deviated, refusing to fire at all. The
refusal has a real reason: a basic search with no term, type, classification, or
term is `INVALID_SEARCH_PARAMS` (SRC-02, ATLAS-400-00-047), so posting `query: ""`
alone is a 400, not a list.

**Decision.** The store sends the empty query with Atlas's every-entity marker:
`{typeName: "_ALL_ENTITY_TYPES", query: ""}` (SRC-03 — the marker stands for every
entity, and the type satisfies SRC-02's requirement). A session type filter wins
over the marker (SRH-08's explore); a non-empty query sends no `typeName` at all,
as before. The URL effect's re-run guard becomes "the store has already run this
text" rather than "the text matches the store's": the legacy resolver ran on every
arrival, query-less included, so a first arrival at a bare `/search/results` fires
the list-everything search, while the hero-submit-then-same-URL-navigation no-op
(DD-219) is preserved.

**Alternatives.** (a) Fire `query: ""` with no type — refused: the server answers
400 (SRC-02), and the alerts drawer would fill on every landing. (b) Keep the
first port's refusal (no request, the no-results card) — refused: SRH-02 already
promises the empty query answers, the demo is the parity oracle (ADR 052), and the
card's advice is wrong for a URL that is the app's own default landing. (c) Send
`typeName: "AtlasBaseType"` — refused: Atlas 2.4.0 has no such type (`UNKNOWN_TYPENAME`,
SRC-03); the marker is the every-entity shape the store's own tests already use.

**Consequences.** The bare URL is a real landing, matching the demo; the results
specs pin the marker body and the "first arrival fires" rule; the explore e2e's
reload step asserts more rows than the one seeded glossary (the filtered re-run's
count) — the every-entity search proving the session filter is gone.
