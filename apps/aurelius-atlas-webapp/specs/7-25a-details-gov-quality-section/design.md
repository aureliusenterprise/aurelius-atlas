# Design record: Governance Quality Rules as a card section (7.25a)

Design decisions for [spec.md](spec.md). Rules, entry template and number
policy: [../0-1-adopt-template/design.md](../0-1-adopt-template/design.md).
Read the [archive](../../../../docs/architecture/conversion/design-log.md) first.

---

## DD-841: The box joins the layout's section list and borrows the card section chrome

- Status: Proposed
- Increment: 7.25a (details pages — Governance Quality Rules as a card section)
- Date: 2026-11-23

**Context.** DET-42's box (7-29) sits outside the sections loop: its own
`<div>` with a plain heading and its own card grid, mounted by a
`govQualityBox` flag. The legacy box is a `details-cards-list`, the same
component as every other card box — chrome, funnel, sort, keyword, scroll. The
user picked that shape.

**Decision.** The box becomes the last entry of `TypeLayout.sections` (DET-48),
marked with a new `SectionDef.kind: "gov-quality"` rather than a seed key. The
template draws it inside the sections loop, wrapped in the same `.box` and given
the same anchor `#gov-quality`, and hands the shared chrome (UIC-27) the box's
title, count line, sorts, funnel and keyword. It projects its rows into the
chrome's `<ng-content>` grid, and `GovQualityCardsComponent` drops its own
`.columns` wrapper so the chrome owns the grid. The `govQualityBox` flag goes
with it: one list now orders every box a screen draws.

**Considered alternatives.**

- _Keep the box outside the loop and bolt the chrome onto it._ Rejected — the
  template then holds two section paths and the side nav keeps a hand-written
  entry per page for something the list already knows. The nav entry is the
  reason DET-48's entries want to come from the same row that draws the box.
- _Feed the box's rows through the sections store._ Rejected — the sections
  store seeds from a relationship key and resolves guides; the box reads rules
  by a `qualifiedName` prefix and joins a verdict from a different service.
  Forcing that through the seed path would mean inventing a seed key per type
  and a resolver branch that only one section uses. Its store stays its own.

**Consequences.** DET-44..DET-47 come free of new chrome: the chrome's count
line, funnel, sort select and keyword input are the legacy's, and DET-42's rows
are unchanged content (spec). One more `kind` on `SectionDef` is the seam;
`DetailsSectionsState` ignores it and `DetailsGovQualityState` owns it. The
person page's box moves position only in the sense that it is now ordered by the
list — it stays last before Properties, which is where DET-42 put it.

---

## DD-842: Sorts, facets, keyword and paging run in the browser over the rules already read

- Status: Proposed
- Increment: 7.25a (details pages — Governance Quality Rules as a card section)
- Date: 2026-11-23

**Context.** DET-42 reads the type's ACTIVE rules once and asks the aux service
for their verdicts once. The legacy asked the engine for its box rows, so its
sorts, facets, keyword and page size were engine asks. There is no engine
(ADR 008), and DET-42's verdict join happens in the browser anyway. The legacy
sorts and facets are four and two (spec Background).

**Decision.** The box filters, sorts and pages the rows it already holds
(DET-44..DET-47). The view is the same shape the sections store uses
(`related-sections.state.ts`): seed rows → keyword → facets → sort → first
`shown` rows, recomputed as derived signals.

- Keyword: a row matches when its rule name, description, dimension or rule type
  contains the term, case-insensitive (DET-47).
- Facets (DET-46): counted over the set the keyword and the selections passed,
  within a group OR, across groups AND, empty groups dropped — VCF-09..VCF-12
  carried. The box's rule read gains `ruleType` alongside the four attributes
  DET-42 already fetches, because that is the second group's value.
- Sorts (DET-45): Relevance is DET-42's name order; the other four compare the
  rule field the option names, with `Compliant` ordering rows with no verdict
  last. A row missing a value goes last ascending, first reversed; ties keep
  Relevance's order.
- Paging (DET-47): nine rows on screen, the chrome's next-page ask grows it by
  nine — DET-22's rule, applied to a store that ends after the read.
- Reset (DET-44): the chrome's count-line ask returns keyword, selections, sort
  and direction to their defaults, and shows nine rows again.

**Considered alternatives.**

- _Server-side the box through a search ask._ Rejected — it needs an engine to
  facet and sort on, and the verdict lives outside the store. The aux call
  answers per entity; only the browser holds both halves.
- _Sort only what DET-42 already reads._ Rejected — the legacy's four sorts name
  a dimension, a verdict and a rule type, and a missing read would make an
  option dead. The rule read widens by one attribute instead.
- _Localise the `Name` and `Compliant` option labels._ Rejected — neither has a
  key in either catalogue and DV-102's rule keeps a translated option list
  honest. DET-21 solved the same collision by drawing raw literals, so these
  two options read "Name" and "Compliant" while the others use the legacy's
  translated dimension and rule-type labels.

**Consequences.** DET-45's orderings are Aurelius' own — DV-199 carries the
difference, and the rule page (7.25b) inherits the same comparators if it wants
them. The `dataqualityruledimension` and `dataqualitytype` keys join
`FacetGroupKey` with the titles from the catalogue ids that already exist in
both catalogues, so no new key enters the i18n gate.

---

## DD-843: Nine layouts gain the box last, with the legacy nav entry above Properties

- Status: Proposed
- Increment: 7.25a (details pages — Governance Quality Rules as a card section)
- Date: 2026-11-23

**Context.** DET-42 built the box for the person page alone and deferred the
other pages to 7.25. In the legacy the box appears on nine pages, always last
among the card boxes, always before the Properties accordion, with the nav entry
`search.details.<layout>.governanceQualityRules` in the same position (verified
against all nine templates). Nine layouts is a small enough change to land at
once, and the user picked it.

**Decision.** Every one of the nine layouts gets the box as its final section
entry, and a nav entry before its Properties entry labelled with the legacy's
key for that page — the keys exist in both catalogues already (DET-48). The
box's heading stays the one shared title key DET-42 uses, because the legacy's
box headings are all the same translated string. The `m4i_data_quality` rule
page does not gain it: in the legacy that page carries the score details
component, not this box, and DET-42 scopes the rules to the entity's own type.

**Considered alternatives.**

- _Land the dataset page first and spread the rest over 7.25's siblings._
  Rejected — the increment's work is one store plus nine config lines; splitting
  it would repeat the same review nine times for a config toggle.
- _Add a stat to each page's stats bar for the box._ Rejected — on the checked
  layouts the legacy's stats bar carries no governance-quality heading at all,
  so a stat would be an invention. DET-24's stat list stays as it is; the box
  reports its own count line (DET-44).

**Consequences.** DET-43's box narrows to the person page's nav entry and the
rows' verdict join, both still its own. `section-config.spec.ts` gains the
per-layout check (position and nav key), and the existing person tests keep
passing because the person box keeps its anchor and rows. The box's rule read
runs on every details page now: one basic search for the type's rules and one
aux call, both per entity (DET-41's seam), which is a cost worth carrying for
the parity it buys and stays quiet on failure (DET-49).
