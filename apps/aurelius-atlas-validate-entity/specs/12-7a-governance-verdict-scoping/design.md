# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design
log apply: an accepted entry is never edited except its status line, and a changed
decision is a new entry that supersedes the old one.

## Entries

### DD-631. A verdict answers only the draft's own type, by LAS-13's join

- **Status:** Proposed
- **Increment:** 12.7a
- **Date:** 2026-11-15
- **Supersedes:** none; amends VEV-02/VEV-03 of 12.7 (DD-498, DD-499, Proposed)

**Decision.** The app reads the rule's `qualifiedName` beside its other attributes
(VEV-03 amended). A rule is for the type its qualified name names before the first
`--` (LAS-13, ASG-02): `m4i_dataset--name` is for `m4i_dataset`, that type and no
other. `evaluate_draft` keeps the rules whose type equals the draft's `typeName` and
answers nothing for the rest — no verdict, and no `unreadRules` entry either (VEV-03
amended). A rule with no prefix, or a draft with no `typeName`, joins nothing. The
cache of VEV-05 keeps the one whole read; the type filter runs per call on it.

**Reason.** 12.7 ran every ACTIVE rule over every draft. On the dev store — the m4i
sample corpus, 95 rules over ten types — that painted another type's sentences on the
editor's controls: `m4i_system--kibanaSpace` banners the Name control of a dataset,
because both types carry a `name`. The product already owns the join: LAS-13 states
it, 14.6's engine scopes by it (ASG-02), and the details box asks the store for the
opened type's rules (DET-42/DD-520). The editor path was the last path without it,
and the two paths now answer the same rules for the same type. The webapp cannot do
the filtering: a verdict carries no type (DD-498's shape stands), and a client-side
rule search would repeat DET-42's read on every keystroke burst.

**Alternatives.** Ask the server with an `entityFilters` prefix per call and key the
cache per type (refused: the editor debounces at 200 ms; a per-type cache turns a
keystroke burst into a search per type visited, and VEV-05's one window covers the
whole corpus anyway). Visit every type's chain and accept the union of supertypes'
rules (refused: LAS-13 names one type, not a chain — a `DataSet` draft is judged by
the `DataSet--` rules only, as 14.6 judges it; a corpus rule for `Asset` would judge
a stored `DataSet` nowhere else).

**Consequences.** The banner shows only this type's rules; the corpus's foreign lines
disappear. A rule whose qualified name breaks the convention (no `--`) goes silent
everywhere — the details box already hides it (DET-42's search filters the same
prefix), so the two surfaces agree. `unreadRules` narrows with the verdicts.

### DD-632. The draft's relationship picks ride the record the check reads

- **Status:** Proposed
- **Increment:** 12.7a
- **Date:** 2026-11-15
- **Supersedes:** none; extends VEV-01 (12.7's wording, DD-498, Proposed)

**Decision.** `DraftEntity` grows two keys it already receives: `typeName` (DD-631's
join) and `relationshipAttributes`. The app builds the record the engine checks as
the draft's unwrapped attributes plus one value per relationship key: a list stays a
list, one entry object stays an object, a `null` becomes none. The unwrapping of the
webapp's `{"raw": x}` wrapper runs over the draft too, as it already runs over a
stored rule (DV-132). VEV-01's meaning grows: the draft's attributes, its type, and
its picks are read; the rest of the body stays ignored.

**Reason.** 16 of the sample's 47 read rules check a relationship (`length('fields',
1)`). The draft carries its picks under `relationshipAttributes` (EDT-16 — the key
drops out of `attributes` on purpose, DD-340), and 12.7's engine read only
`attributes`, so every such rule answered its refusal sentence forever: the banner
pinned a warning under a picker that holds picks. 14.6 solved the same read for a
stored entity by ASG-04/DD-536 — a relationship name reads the ends, a list by its
length, one end as itself. The draft's entries are the same shape (guid, typeName)
and need no ends resolved: the editor knows what is picked, and the verdict must
change as the person picks (EDT-23's trigger). ASG-04's empty set reads `[]`, which
holds a value but no content — the draft keeps that reading exactly.

**Alternatives.** Resolve the draft's picks to stored ends (refused: the picks are
the person's unsaved state; resolution adds a read and can only lag the form). Keep
relationships out and hide their lines (refused: the rule is real, the picker is the
field it measures, and the details box already shows a verdict for it — DET-42
joins on `ruleGuid` and its rows would disagree with the banner).

**Consequences.** The `{"raw": …}` unwrapping now applies to the draft (a wrapper
used to count as content, flipping compliance). The details box sends the same
draft shape (its view's sections folded the same way, DD-608's helper), so the box's
relationship rows answer honestly too. A draft without picks answers an empty list
or a null, not a missing key.

### DD-633. The description alias runs one way

- **Status:** Proposed
- **Increment:** 12.7a
- **Date:** 2026-11-15
- **Supersedes:** none; corrects the code 12.7 shipped for EDT-24's alias (DD-498, Proposed)

**Decision.** The editor's alias map keeps one entry: the `description` control also
shows a verdict whose attribute is `definition`. A `description` verdict names only
the `description` control (EDT-24 amended).

**Reason.** 12.7's spec records the legacy's one direction (the `gov-quality-display`
card key `definition` displayed under the Description control — the legacy types
carry `definition`, this catalogue's carry `description`), and DD-498 says the same.
The shipped map was symmetric, so on a type that renders both markdown controls one
verdict painted twice — a line duplicated under a control no rule measured.

**Alternatives.** Keep the pair (refused: it contradicts both records and duplicates
a line on one control).

**Consequences.** Nothing changes on this catalogue's shipped types, which carry
only `description`. A re-imported legacy type, which carries both, shows each rule's
line once.
