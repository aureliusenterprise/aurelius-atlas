# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-143. The landing page is ported statically; search affordances and Shell chrome join the search slice

- **Status:** Proposed
- **Increment:** 7.5
- **Date:** 2026-10-20

**Decision.** 7.5 ports the Aurelius landing page (`browse`) as the static screen it is:
hero, the three context cards, and the info modals with their hardcoded type tables. The
cards' `simple-search-input` fields and `directTo*` "explore" buttons — every affordance
that sets `SearchService.query/filters` and routes to `/search/results` — are not ported
in this slice, and the Shell chrome (header/footer, whose centrepiece is the global search
bar) is deferred with them. Both join the search slice (7.4), which the user has placed on
hold until the server search API exists (4.1 basic search, 2.3 entity read).

**Reason.** The landing page's content — cards, info modals, type tables — is entirely
static and fully keyed in the XLIFF bridge, so the screen can be ported and proven today;
its search affordances are navigation into a screen that has no API, and shipping a search
box whose results page 404s is the speculative build DD-140 refuses, one level up. The
Shell is deferred for the same reason in chrome form: Aurelius's header carries the global
search bar and session UI, so wiring the chrome is one decision taken together with the
search entry point, not two. The user's 2026-10-20 direction ("port the landing page;
hold off on any search until the API is ready") fixes exactly this seam.

**Alternatives.** Port the cards with their search fields wired to a stub: the affordance
works in dev and dies in the e2e stack's real server — a UI promise the increment cannot
keep. Ship the Shell now and hide its search bar: chrome with its main control removed is
neither the legacy screen nor a clean seam.

**Consequences.** The 7.5 page has no route out except the info modals (BRW-06); 7.4
re-adds the affordances as part of the search slice, at which point the Shell row of the
7.x ledger is taken with it. The 7.5 roadmap row is retitled to the landing page; browse
domain grids, if kept from the legacy design, follow with the search slice.

### DD-144. i18n ids carry no description suffix; the bridge key must equal the extracted id

- **Status:** Proposed
- **Increment:** 7.5
- **Date:** 2026-10-20

**Decision.** An `i18n` attribute in the webapp or `aurelius-atlas-ui` is written
`i18n="@@<dictionary.path>"` only — never `@@<id>|<description>`. Where a unit wants a
translator note, the note lives in an adjacent comment. `aurelius-atlas-ui`'s four chrome
units (`components.sortableTableShell.previous|next|noData`, `components.accordion.toggleContent`)
drop their `| … (DD-136)` suffixes, and the `SortableTable` component drops
`TableColumn`/`TableRow` from its `imports` (caller-projected directives, NG8113).

**Reason.** Angular joins the `|description` half into the extracted trans-unit id, so the
key-keyed bridge (DD-128, DD-136) can never match such a unit: `extract-i18n` emits
`components.sortableTableShell.next|Aurelius table shell …` where the catalogue carries
plain `components.sortableTableShell.next`. The nl-NL build then answers "No translation
found" for the unit — the chrome string ships untranslated in the one language the bridge
exists for. The defect was latent in 7.2 (the ui-lib has no app build of its own to
surface it; the accordion unit never matched, unnoticed) and surfaced in 7.5 when the
landing's info-modals pulled the sortable table and its pagination into the app's
translation graph. The completeness spec cannot catch it: it compares the committed
catalogues to the fixtures, and extracts ids only as a set-diff (`UIC-04` scans template
`@@components.*` literals, which include the suffix). The production build is the gate
that sees it. NG8113 has the same root as the import fix: the table's own template never
applies the column/row directives — callers do — so listing them is a lie the compiler now
flags once the table is app-compiled.

**Alternatives.** Keep the descriptions and teach the bridge to split on `|`: one more
key-mangling rule in the generator for a note the XLIFF `<note>` element (which
`extract-i18n` emits from the marker's description) already carries — the catalogue
already proves round-tripping works without it. Register the chrome strings in the
catalogues _with_ the suffix: breaks the "id equals the legacy dictionary path" invariant
DD-136 states in its title.

**Consequences.** `nx extract-i18n aurelius-atlas-webapp` output is now a strict subset of
the bridge catalogue, so `nx build aurelius-atlas-webapp` is warning-clean and can be used
as the id-parity gate; the 7.2 spec's chrome-string rule (UIC-04) is unchanged, and the
accordion's toggle-content unit starts translating in nl-NL for the first time.
