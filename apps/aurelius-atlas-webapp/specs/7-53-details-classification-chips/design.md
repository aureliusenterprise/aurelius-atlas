# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-880. The chips row is a leaf; the header box stays in the screen (no wide DetailsHeader)

- **Status:** Proposed
- **Increment:** 7.53
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The header's classification chips row (DET-09's one chip per tag,
VDR-12's propagated chips, DV-197's source dropdown) moves into one component,
`ClassificationChips`, in the details feature. It takes two signal inputs — the
own-tag labels and the propagated entries, both built by the screen's
`classifications()` and `propagatedClassifications()` — re-emits a source click,
and paints nothing else. Its own guard (`both lists empty, hide the row`) moves
with it because it reads only those two inputs, not a store. The screen keeps the
whole `.aurelius-details-header` box — the title, the type-name line, the trail,
the edit affordance, and the loading line — and keeps `classifications()` /
`propagatedClassifications()` and `onSourceClick`. No stylesheet moves: the row
owns no rule (Bulma and the chip carry it), so the child needs none, unlike the
first row (7.51) and the stats bar (7.52) that took a `:host { display: block; }`
sheet.

**Why.** This is the header's only clean leaf. The chips row is a pure painter on
two hand-built lists with one re-emitted event and a guard that reads only inputs
— the exact 7.50/7.51/7.52 shape. The rest of the header is not a leaf. A single
`DetailsHeader` would take the title, the type name, the type alias, the icon,
both classification lists, the trail, the guid, a can-write flag, an edit label,
and a loading flag (about twelve inputs) and emit edit, crumb, and source clicks
(about four outputs). That wide contract is the trap the plan named: a component
with twelve inputs has no single job and is harder to read than the box it
replaces, and two of its guards (`@if (canWrite())` for the edit button,
`state.loading() && !entity()` for the loading line) read the permission store and
the entity store — store reads the painter must not take (DET-06). So the box
stays the screen's composition container and its self-contained chip row is the
one part that leaves. Narrowing here is 7.49's lesson applied at the header: move
the part that has no store or contract to design, leave the container that owns
them.

**Considered and rejected.** _Extract the whole header as `DetailsHeader`_ — the
twelve-input, four-output contract with the `canWrite` and loading store-read
guards is a container, not a painter; splitting it into sub-children (a title
part, a trail part, a chips part) with the box still in the screen is the real
shape, and this increment ships the first of those. _Fold the trail in too (it is
also a Breadcrumbs mount)_ — the trail is a second self-contained leaf; bundling
it with the chips would name the increment for two things, grow the contract, and
touch DET-12's breadcrumb-empty guard for no gain over its own leaf. _Pass the
entity and derive the chips inside the row_ — that moves the filter, the
empty-string drop, and `nameDisplay` of both lists into the child, which is the
store-shaping work DET-09 owns in the screen; the row paints lists it is handed.
_A shared details test harness so the chips get their own spec_ — the details spec
owns its `setup` helpers inline (unlike the editor's `editor-testing.ts`); DET-09
and VDR-12 keep driving the whole screen, as 7.48 through 7.52 do.

**Consequences.** `details.component.ts` drops two component imports and gains one
(779 lines), its template drops from 300 to 290, and its stylesheet stays at 65;
`classification-chips.component.ts` (55 lines, doc plus inline template, no
stylesheet) holds the row. The card's direct mount of the shared
`PropagatedChips` control is untouched (DD-836 keeps it shared). No test moves, so
the suite stays at 1,047 across 85 files (DET-09, VDR-12, and DV-197 pass against
the whole screen, which now paints the row through the child, and the e2e and unit
pins on the chip row and its dropdown are unchanged). No string moves (the row
prints no text of its own), so both locale fixtures stay byte-equal (SHL-08's gate
untouched). The header box itself is the next split (a title/type leaf, a trail
leaf) in later increments — 7.54 onward — or stays, once the screen's anatomy is
all parts; that call comes when the rest of the screen is split. No `AGENTS.md`
change: the details feature documents its own components in their file headers.
