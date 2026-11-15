# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an
accepted entry is never edited except its status line, and a changed decision is
a new entry that
supersedes the old one.

## DD-630. A trail with no stored parent draws nothing, the legacy guard's shape

- **Status:** Proposed
- **Increment:** 16.5g
- **Date:** 2026-11-15
- **Supersedes:** DD-606's own-crumb-alone clause (amends VDR-06, VCF-01)

**Decision.** `trailOf` returns the empty list when the card or view carries an
empty `breadcrumb`, before it appends the entity's own crumb. A parentless
entity therefore renders no trail in the details header and no trail on its
rich card, because both screens build the trail through this one function
(DD-616). A trail with a stored parent is exactly what DD-606 and DD-616 draw
today: stored crumbs top down, the entity's own crumb last, the mount's active
crumb unchanged (DD-625), crumb routing unchanged (DET-06). The breadcrumbs
component keeps its own empty guard (UIC-11); the rule lives in the app's trail,
so the lib stays a renderer.

**Reason.** The legacy component wrapped its whole `nav` — the entity's own
`showLast` crumb included — in `*ngIf="breadcrumbs.length"`: no stored parents,
no trail. DD-606 chose the opposite for the details header ("a page shows no
name above its own title"), and 16.5d's shared rule carried that choice onto
every card too (DD-616). The review asked for the legacy shape back, and the
single-crumb trail is the demo's only visual mismatch left on these two screens:
it repeats the title line, which sits directly above it on the header and is the
card's own linked title on a card. One guard in the shared function restores
parity on both screens at once, with no new component input and no lib change.

**Alternatives.**

- Hide at each mount (header `@if`, card `@if`): two guards for one rule, and
  the shared card's "one rule, two screens" contract (DD-616) is the reason
  they cannot diverge — the guard belongs where the trail is built.
- Hide only on the results card, keep the header crumb: the header and the card
  then answer different questions about the same entity, against ADR 064 R2.
- Keep DD-606 (own crumb alone): the title repeats itself on every parentless
  page and card, the exact mismatch the review named.

**Consequences.** DET-12's "own crumb alone" pin and VCF-01's results-row trail
pin flip to the empty trail; the e2e results assertion flips from "one crumb,
active" to "no trail". The seeded mini-graph scenario (domain → entity) proves
the filled trail survives. VDR-06 and VCF-01 are amended in place and DD-606 is
superseded by name, never edited.
