# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

The increment's store and door entries (DD-845..DD-847) live with
[16.5i](../../../../libs/python/aurelius-atlas-core/specs/16-5i-rule-verdicts-door/design.md).

## DD-848. The verdict boxes ride the sections store, seeded from the door

- **Status:** Proposed
- **Increment:** 7.25b
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `RelatedSectionsState` gains a second seed entry next to
{@link RelatedSectionsState.seed}: the screen hands it the verdict GUIDs per
anchor alongside the view and layout, and the store seeds those two records from
them instead of from `sectionEnds` (DET-53). Everything downstream is untouched
— the chunked resolve of 25 (VCF-02, DD-615), the keyword, sort and facet rules
of 16.5e, the page of nine, DET-18's loading/failed/missing rows, and the
{@link RelatedSectionsState.countFor} the stats bar already reads by anchor.
The two anchors enter the layout as ordinary `SectionDef`s, so `sectionViews`
draws them in one pass like every other box.

**Why.** DET-53's boxes are the legacy's `details-cards-list` — the same
component the relationship boxes use — and the Aurelius equivalent is the
sections store, which is 650 lines of resolve, filter, facet and paging rules
already speced (DET-17..DET-22, VCF-08..VCF-12) and tested. A second store that
copies them has already forked the rules: 16.5e's keyword-every-keystroke
(DD-375) and 16.5d's missing-guid rule (DD-615) would each need re-implementing
and re-deviating. The seed is the one honest difference between the boxes, so
the seed is the one thing that changes. The `kind` discriminant DD-841 added
already marks boxes the sections store does not seed; a verdict box is the
same box with a different seed, so it needs no kind — the layout names the
anchor and the screen supplies the GUIDs.

**Considered and rejected.** _A `RuleVerdictsState` twin of `GovQualityState`_
— that box draws rule rows with verdict icons, a shape no card section chrome
renders, so it needed its own store legitimately; the verdict boxes draw door
cards in the shared chrome, and copying the chrome's store rules for them buys
nothing. _Seeding through `view.sections`_ — the rule entity carries no
relationship to the entities it judged (the worker never wrote one, ASG-03),
and inventing a pseudo-end would put verdict data in the read door's answer,
which ADR 071 R2 keeps out.

## DD-849. The chart box is a layout slot, drawn by the details screen

- **Status:** Proposed
- **Increment:** 7.25b
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `TypeLayout` grows an optional `complianceChart` slot (title plus
the two legend labels); the details template renders it as one box between the
stats bar and the first section, holding the UIC-36 `DataQualityPie` at size 8
beside the legend (DET-54). The score it shows is a computed over the verdict
split (DET-51), and every layout without the slot renders nothing — the ten
shipped rows are unchanged. The box gets no nav entry and no stat, because the
legacy gave it neither (DET-50).

**Why.** It is the only box of the page that the config table cannot already
name: the description box, stats bar, card sections, properties accordion, and
navigation all exist as typed slots (7.21a), and the pie is a shipped ui-lib
part (7.24, UIC-36) needing no new component. A dedicated details component for
the rule page would fork the whole details chrome the way the legacy's
`GovQualityDetailsComponent` did, losing the shared header, alerts and editor
wiring for one box; a slot keeps the page one row of the table plus one
template block. Legend colours are the ui-lib pie's own (UIC-36's pair, the
legacy's `hsl` values) so the legend and the arc can never disagree.

**Considered and rejected.** _A ui-lib `SectionStats`-style part_ — only one
screen in the app draws a legend beside a pie; until a second does, the
template block is the smaller abstraction. _Putting the score on the door_ —
DD-847's rejected server count, for the same reason.

## DD-850. One thin client, loaded where the rules box loads

- **Status:** Proposed
- **Increment:** 7.25b
- **Date:** 2026-11-24
- **Supersedes:** –

**Decision.** `RuleVerdictsService` (VDR-15) is the family's fourth POST client
in `aurelius-atlas-data-access` — same `API_BASE_URL`, same bearer token,
retries free like the other doors (7.26). Its screen store is the increment's
only new state class: it holds the rows, loading state, split arrays and score
as computeds, asks once per entity arrival from the same effect that loads
`DetailsGovQualityState`, and clears on a null entity (DET-51, DET-55). The
store never calls the search door; card resolving stays the sections store's
(DD-848).

**Why.** The family's other POST clients (search, entity, save) each own one
route and nothing else — no state, no caching — and the verdicts read has the
same lifetime as the screen, so the screen's effect is its only caller (ADR 071
R5: one consumer). Keeping the split, counts and score as computeds over one
signal value is DET-52's `startWith(0)` posture without a second loading
flag, and DET-55's quiet empty is the store's initial state, which a failure
simply never replaces.

**Considered and rejected.** _Loading in the sections store's seed_ — the
sections store resolves cards, and owning a second fetch would make its seed
entry await a network call before the first card can even show; the screen
already sequences fetches this way for the lineage box and the rules box.
_Caching the rows on the entity view_ — the verdicts move with every worker
round (ASG-06); a stale cache would show the wrong score.
