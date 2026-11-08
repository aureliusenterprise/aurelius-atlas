# Design decisions: 7.22e — Lineage diagram: the archimate shape language

> **Purpose:** the `DD-NNN` entries of this increment, written before the code and
> updated while it changes. Read-only history: every entry ever made also lives in
> [`docs/architecture/conversion/design-log.md`](../../../../docs/architecture/conversion/design-log.md),
> which is the archive (an entry lives in exactly these two places, and the archive
> is never edited — DD-001). New entries are numbered consecutively across the
> repository: check the archive's topmost number and the sibling `specs/*/design.md`
> files for the largest `DD-NNN` in use before taking the next.

| Id      | Title                                                                 |
| ------- | --------------------------------------------------------------------- |
| DD-418. | The archimate language is ported as plain data tables and literal CSS |

## Decisions

### DD-418. The archimate language is ported as plain data tables and literal CSS

- **Status:** Proposed
- **Increment:** 7.22e
- **Date:** 2026-11-08

**Decision.** The archimate language lands as one data module,
`archimate-shapes.ts`. It holds the legacy's four tables (the 65-row shape
table, the 65-row fill-class table, the 64-row glyph table, and the 8-row
marker table) and the 12-row style switch as plain `const` records and pure
functions (`ar3NodeShape`, `ar3Class`, `ar3Icon`, `ar3ConnectionStyle`,
`nodePath`). The two fill blocks ride as table strings (`AR3_NODE_FILLS`,
`AR3_ICON_FILLS`), but each of the three components that needs them (the
viewer, the entity table, and the selection panel) ships a literal copy inside
its own `styles`, with a comment that names the source table. Three tests pin
every declaration of each table into each component's compiled `ɵcmp.styles`,
so a drifted copy fails CI. The reader's `Ar3Relation` gains an `options` pair
read with the legacy's own gating. Amends LDG-13/LDG-14's scope (the archimate
sets they left out) and LDG-11 (the two attributes).

**Reason.** The legacy tables are lookup data with a CSS-shaped tail. Plain
records fit the signals idiom WBP-02 asks for, because they need no DI, no
services, and no `BehaviorSubject`s, and a computed reads them. Verbatim rows
are what the parity review (ADR 052) compares against the vendored files line
by line. The literal CSS copies are forced. The Angular builder drops an
imported constant interpolated into a component's `styles`, so
`${AR3_NODE_FILLS}` never reaches the compiled block. This was verified: the
emitted `ɵcmp.styles` carries no fill rules when the constant is interpolated.
A drift-pinned literal copy is the smallest fix that keeps one source of
truth. The table stays the single list a reviewer reads, and the pins fail the
build the moment a copy and the table disagree.

**Alternatives.** (1) Port a subset: the layer fills and the junction shapes
only. It loses. The user chose the full port, and a partial table is a second
taxonomy that no legacy file answers to. (2) Import the legacy's compose
closures. `ar3Elements` builds `d3` path closures per row. It loses. WBP-02
forbids the library's idioms, and closures cannot be reviewed as rows against
the vendored file. (3) A shared `styleUrls` stylesheet for the fills. It
loses. The repo has zero `styleUrls` precedent, because every component of the
lineage tree inlines its styles. And the drawer's two icon sites need the
rules scoped under different selectors anyway (`.icon` versus
`.aurelius-selection-type .icon`). (4) Runtime injection of the table strings,
where a service appends a `<style>` tag. It loses. It defeats view
encapsulation, adds a DOM side effect for what is static data, and cannot be
pinned by the component's own spec the way `ɵcmp.styles` is.

**Consequences.** LDG-13's plain-rectangle fallback stays the default branch of
`ar3NodeShape`, so 7.22b's tests pass unchanged and LDG-14's `generic-arrow`
pin holds against the marker table's copy of the same row. Archimate rows now
render glyphs in the drawer's three icon sites, and the card badge stays
lineage-only. DD-405's family has no archimate entry, so the table's
`ar3BadgeClass` answers undefined. The three drift pins (the viewer,
model-tab, and selection-panel specs) are the guard the literal copies need. A
change to a fill must touch the table and all three copies, and the pins say
which copy drifted. The unit suite grows to 568 tests, and the e2e suite does
not change, because the shipped producer still emits only the lineage pair.
