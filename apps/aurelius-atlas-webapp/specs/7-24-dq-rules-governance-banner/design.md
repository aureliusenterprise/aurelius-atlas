# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-434. The rules box seeds from the relationship end, not a quality index

- **Status:** Proposed
- **Increment:** 7.24
- **Date:** 2026-11-10

**Decision.** The field page's Data Quality Rules box (DET-35) is one more row
of the 7.21a section machinery: its seed is the opened field's own
`relationshipAttributes.dataQuality`, and its cards are the resolved
`m4i_data_quality` entities. The legacy's `dqscore` and
`dataqualityruledimension` sort options stay out, so every layout keeps the
same two-option sort (DET-19).

**Reason.** The legacy filled the box from the App Search `data_quality` index
with the filter `fieldguid: [entityId]`, joined so each rule document also
carried its computed `dqscore`. ADR 054 retired that index surface, and the
server evaluates no rule expression, so the score has no source (DD-369). The
association itself needs none of that: the sample corpus carries the
`dataQuality` end on 25 fields, and DET-17's bulk reads already resolve
relationship seeds for the other seven boxes. The dimension stays visible as a
card column (the rule entity's own `qualityDimension`), only the sort drops.

**Alternatives.** Query `POST /search/basic` for rules that point at the field.
It loses twice over as DD-368 argues for the other boxes: the seed is already
the whole set, and the relationship condition has no `SearchParameters` form.
Ship the dimension sort now, sorted client-side over the resolved entities. It
loses DET-19's uniformity for one box whose rows are nine at a page; 7.25
re-adds both sorts when real rows exist, and a config row cannot half-sort a
set the browser already holds.

**Consequences.** The box costs one config row plus its DET-36 stats/nav pair —
no new component, no new request shape. When 7.25 brings the scores back, the
score stat, the sort list, and the card badge column arrive through their own
entries, and this box does not change.

### DD-435. The browser reaches validate-entity as 7.22a reaches lineage-model

- **Status:** Proposed
- **Increment:** 7.24
- **Date:** 2026-11-10

**Decision.** The editor calls the aux API at the same-origin path
`/validate-entity/`: one new nginx location (TLS-verified upstream, name
pinned, DD-142's posture), one new `bearerTokenConfig` prefix, one optional
`validateEntityBaseUrl` key in `AppConfig` defaulting to that path, one dev
proxy entry to `:21003`, the serve dependency, and the e2e compose container.
The aux app gains no new setting: VE-03 already verifies the browser client's
own token (DV-75, audience `aurelius`), so no `auth_extra_audiences` join is
needed.

**Reason.** LDG-06 and DD-384 settled this shape for the second backend and
stated the rule for the rest: "if a later slice adds the data2model or
validate-entity surface to the browser, each takes its own location and its own
key by the same rule." The app's audience differs from the lineage app's,
though, and the difference is worth naming. The lineage chain forwards the
caller's raw token upstream (LM-04), so DD-385 had to widen its verifier
without losing the service identity. validate-entity forwards nothing (8.3: no
upstreams, VE-03), and its spec set its audience to the browser client from
the start (AUX-04: "the browser calls this endpoint with its own token, so this
app verifies tokens for that audience"). The endpoint is the browser's from
begin to end.

**Alternatives.** Fold the route under `/api/` so no new location is needed. It
loses for the reason DD-384 gives: `/api/` proxies to one upstream, and a
prefix collision with the Atlas server's namespace costs more than one location
block. Second, mount the route on the gateway. It loses for the same DD-285
reason, and a second browser origin in the CSP and in Keycloak. Third, copy
DD-385's extra-audience setting anyway. It loses a fact: the setting would
express a join that VE-03 already covers, and an unused setting is a chart
contract nobody tests.

**Consequences.** The webapp chart gains the two upstream placeholders
(`AURELIUS_ATLAS_WEBAPP_VALIDATE_ENTITY_UPSTREAM`, `..._UPSTREAM_NAME`) beside
the lineage pair (DD-294's URL shape), and the umbrella's ingress allow gains
the webapp → validate-entity leg (CHT-60..73's additive rule). `connect-src
'self'` already covers the same-origin path, so the CSP does not change.

### DD-436. The banner swallows failures and matches cards to controls by key

- **Status:** Proposed
- **Increment:** 7.24
- **Date:** 2026-11-10

**Decision.** A failed validation renders nothing and alerts nothing: the
drawer stays usable (EDT-23). Each rule line lands under the form control whose
key names its response card (`name`, `definition`, …), and a response card with
no rendered control of that key renders nowhere (EDT-24). The call fires on
open and on every change debounced 200 ms.

**Reason.** This is the legacy behaviour exactly, and the legacy had it right
twice. The validation is advisory while a record is drafted, so a 502 from an
aux API is not a reason to interrupt a person who is typing (`catchError` to
the empty answer, the quiet `ManagedTask`). And the response is a fixed four
cards whatever the entity (the mock, VE-02; the real evaluator the same shape),
while the drawer's controls come from the entity's type. Keying the two by
name — the legacy `rules.name as rules` pattern — keeps every type's drawer
honest: a card nobody can see is a complaint about a field the editor never
showed.

**Alternatives.** Alert on failure, as the sections' failed chunks do. Refused
because those chunks lose cards a person came to read, while the banner adds
verdicts nobody asked for; the alert budget belongs to the first. Second, drop
the debounce and validate on blur. It loses the legacy's live feel at no
real cost saving: the mock is fixed, and the debounce is one operator. Third,
match lines positionally. It loses the moment a drawer renders a subset of the
keys.

**Consequences.** The state is small enough to stay inside the drawer
component (the editor-state pattern, DD-330's neighbours): one signal for the
answer, one counter for the generation. 7.25's verdicts arrive on the same
channel unchanged, so this entry holds for real data too.

### DD-437. The quality components ship dumb, with stories only

- **Status:** Proposed
- **Increment:** 7.24
- **Date:** 2026-11-10

**Decision.** UIC-36..39 (the pie, the dimension list, the governance dropdown,
the card badge) land in `aurelius-atlas-ui` now: signal inputs, a story each,
unit tests each, and no product screen. They take plain data — a number, a
dimension row, a message row — and know nothing of `dqscore_*` documents or
App Search shapes.

**Reason.** The user asked for the UI elements, and the roadmap's 7.25 row owns
the data that fills them. DD-369 refuses placeholder chrome on a real screen,
and this slice honours that: the components exist where the seam is (the
`entity-card` `[card-quality]` projection input, 7.13's `showQuality` flag, the
details layouts' score stat), and the screen gains them only when a source
does. Building them dumb is also what makes them testable today: the story is
the acceptance the data-free components can have, the same way UIC-27's grid
proved itself before 7.21a wired it.

**Alternatives.** Wait for 7.25 and build the components there. Refused for the
size: that slice already carries the evaluator's return across nine pages, and
four new components plus their visual tests would push it past the increment
budget. Second, ship them wired to empty signals on the details page. Refused
by DD-369: an always-empty pie advertises a broken feature, the exact defect
that entry was written to prevent.

**Consequences.** 7.25's UI half becomes wiring: its spec cites UIC-36..39 as
pre-existing and adds only the source and the rule ids. The pie's stylesheet
rides the styles pipeline (the webapp styles builder), so the stories prove
theme compatibility now, not there.
