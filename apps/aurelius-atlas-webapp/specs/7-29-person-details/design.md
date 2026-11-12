# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## Entries

### DD-518. The person row extends the layout table with three flags, not a second renderer

- **Status:** Proposed
- **Increment:** 7.29
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** `TypeLayout` gains three optional members: `descriptionBox`
(absent means true; the person row sets it false), `statsGroups` (grouped
stats-bar boxes, rendered instead of the flat `stats` when present), and
`govQualityBox` (absent means false; the person row sets it true). The dispatch,
the table, and the one renderer stay as 7.21a built them (DD-366); the person
enters as the table's tenth row.

**Reason.** The legacy shipped ten copy-pasted components, and the config table
was this product's answer (DD-366). The person differs in three places only: no
description box, a grouped stats bar, and one extra non-card box. Each is a
flag the renderer already has a slot for, so a second component tree would
fork the stats counts, the anchor scrolling, and the navigation a third time.
`ProcessOwner` stays out of the row because the legacy box never lists a
person's processes (DV-154).

**Alternatives.**

- A dedicated `person-details` component. It copies the stats bar, the
  properties accordion, and the nav wiring, and every later fix must land
  twice.
- Modelling the four stats groups as four card sections. The groups have no
  search box, no sort, and no cards: they are counts, so they belong to the
  stats-bar config, not to `sections`.

**Consequences.** `section-config.spec.ts` grows the tenth key and the flag
checks (DET-39/DET-40). The renderer's `stats` path keeps serving the nine
rows unchanged.

### DD-519. The Responsibilities box seeds from the person's five ends

- **Status:** Proposed
- **Increment:** 7.29
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** The person layout carries one card section whose `seedKeys` are
the five responsibility ends in legacy stats order: `domainLead`,
`businessOwnerEntity`, `businessOwnerAttribute`, `stewardEntity`,
`stewardAttribute`. `RelatedSectionsState` seeds it unchanged — it already
merges several keys, deduped by guid (DET-17) — and the stats bar counts each
end on its own through a small `endCount` helper that applies the same ACTIVE

- guid + dedupe rule to one key.

**Reason.** The legacy box queried the retired `atlas-dev` engine for
`derivedperson: [name]` (DV-154). The same facts sit on the opened entity as
relationship ends, need no second read, and cannot drift when a person is
renamed. 7.21a's seed already merges keys (the dataset's producers case is one
key; nothing stops five), and DET-17's dedupe keeps one entity that leads and
owns the same record to one card. The stats need per-end counts, which the
merged section cannot give back, so the helper reads the ends directly.

**Alternatives.**

- Five card sections, one per end. The legacy has one box, and five would
  render five search boxes where the legacy has one.
- Keeping the search route with a `typename`/attribute filter. A name-based
  filter breaks on rename, and a guid-based one still returns only what the
  ends already hold, at the price of a paged search.

**Consequences.** The box's counts and its cards come from the same seed rule,
so they cannot disagree. The sort list stays the DET-21 pair; the legacy's
`dqscore_*` sorts stay out with DD-369.

### DD-520. The rule box reads the store's rules by prefix and the aux API's verdicts

- **Status:** Proposed
- **Increment:** 7.29
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** `DetailsGovQualityState` (per-screen, like the sections store)
reads two calls when a person opens. The first is `POST /v2/search/basic` with
`typeName=m4i_gov_data_quality`, `entityFilters` on `qualifiedName`
`startsWith "<typeName>--"`, `excludeDeletedEntities=true`,
`includeSubTypes=false`, and the attributes `name`, `ruleDescription`,
`qualityDimension`, `active`. ACTIVE follows 12.2's reading (VEV-03): only a
false `active` is not. The second is the editor's existing
`ValidateEntityService.validateEntity(entity)` call, whose `verdicts` join the
rules on `ruleGuid`; a rule with no verdict line renders iconless (VEV-03's
unread rule). Rules sort by name; the page size is one search at `limit=100`.

**Reason.** The legacy box read the `atlas-dev-gov-quality` index, one document
per entity and rule (DV-155). That engine is retired (ADR 060) and its
per-document verdicts were a stale snapshot (14.1: 42 of 50 rules). The store
holds the rules; the verdicts of 12.7 are live answers computed over the opened
record, which is exactly what the box showed. The qualified-name prefix is the
rule→type rule LAS-13 states, so the set matches the legacy's `dataqualityrulet
ypename`. The join rides rule guids because 12.7 kept rule identity for this
box (DD-498). One page at 100 fits the corpus (the largest type carries a few
dozen rules); the engine's marker walk stays server-side.

**Alternatives.**

- Storing verdicts per entity and reading them (12.8's plan). Right shape for
  search facets, wrong increment: the verdicts of 12.7 are live, and the box
  must show the record as opened, not as last saved.
- Reading every rule and filtering in the browser. The corpus grows; the
  server-side prefix filter costs the same one call.

**Consequences.** The box re-reads on every entity arrival, like the sections
store. `unreadRules` ride the answer for the future rule box (7.28), not this
one: an unread rule simply has no verdict line.

### DD-521. The box keeps the editor's quiet swallow and its own dumb part

- **Status:** Proposed
- **Increment:** 7.29
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** A failed rule read or verdict call answers an empty box and
raises no alert (the EDT-23 swallow). A superseded answer paints nothing (the
generation guard, DET-08's sibling). The rows render through a dumb app-level
part, `gov-quality-cards.component.ts`: title link plus the `ruleDescription`
line plus the verdict line (success/warning icon, dimension titlecased), with
the screen owning the router (DET-06's rule).

**Reason.** The legacy swallowed the gov-quality failure too (its
`catchError`), and the page's other boxes stay honest: an unavailable verdict
source is an empty box, never a wrong icon. The part lives app-side, not in
`aurelius-atlas-ui`, because it knows Atlas rule fields and the ui library
stays dumb (DD-136's split); 7.25's search-side list is a different part.

**Alternatives.**

- Reusing `DetailsCardSection`. The legacy box has no count line, no search,
  and no paging; forcing it in would show chrome the legacy never drew.
- Alerting on failure. The editor's rule proved alerts there were noise; the
  same source failing on a read-only page is quieter still.

**Consequences.** The part carries no state, so its spec is a pure render
test; the store's spec carries the read, join, and swallow cases.

### DD-522. Stats clicks only scroll

- **Status:** Proposed
- **Increment:** 7.29
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** A grouped stats heading routes to its box's fragment
(`#governance-roles`, `#properties-details`) and nothing else. The click does
not rewrite any search filter.

**Reason.** The legacy heading also rewrote the box's App Search filters
(`filterResponsibilitiesByType`, keyed by `derived<role>guid` and `typename`,
DV-156). That facet has no twin here (ADR 054/060): the box lists all five ends
at once, so a filter would hide what the box exists to show. The heading still
names its box, and DET-24's scroll contract (DD-381's anchor routing) applies
to it like any other stat.

**Alternatives.**

- Filtering the section client-side to the clicked end. It reads as a promise
  the back button must undo, and the legacy's own scroll ran first anyway.
- Dropping the headings' links. The legacy bar is a navigation surface, and
  DET-24's other rows keep theirs.

**Consequences.** `SectionStats` carries grouped items through the existing
`itemClicked` contract; no new output lands in the ui part.
