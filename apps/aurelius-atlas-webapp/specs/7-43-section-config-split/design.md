# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-869. A layout's shapes, its rows, and its derived values live in three files

- **Status:** Proposed
- **Increment:** 7.43
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** `section-config.ts` becomes three files. The shapes a layout
consumer names (`SectionDef`, `TypeLayout`, the stats and nav types, the facet
and layout-key unions) move to `search/details/sections/section.model.ts`. The
eleven-row `LAYOUTS` table and the constants a row's content names move to
`search/details/sections/layouts.ts`. The Data Quality score mapping — the
helpers that turn a view's `quality` rows (AVS-01) into the box's rows, the
sort keys, the source gate, and the stat's percent — moves to
`search/shared/quality-mapping.ts`, a peer of `search/shared/`. Every
declaration moves byte-for-byte; only the import lines of eight consumers
change.

**Why.** One file answered three unrelated questions, and the wrong question
was load-bearing: the score mapping sat in the layout config, so the shared
catalogue card had to import it across the feature boundary, from `shared/`
**up** into `details/sections/`. That edge is the reason the layering plan's
Phase 3 cannot yet ban `shared/ → details/` — the ban would fail on the card
until the mapping moves. Moving the mapping to `shared/` where both readers
meet it is the smallest change that inverts the edge, and it lets Phase 3
name the boundary without naming an exception. The model split rides along
because `layouts.ts` otherwise still imports the shapes it would export, and a
670-line config that re-exports nine types gives the same coupling a shorter
name; the consumers that only need a type (`layout.state`, `details.component`)
import it from `section.model` and no longer drag the table. The spec splits
with the code so a reader of the mapping finds its test, and `layouts.spec.ts`
keeps `git mv` history through the rename.

**Considered and rejected.** _Two files (model + one config)_ — the mapping
would stay inside `details/sections/` and the card would keep importing up,
which is the whole defect; _three files inside `sections/`, none in `shared/`_
— fixes the size and not the edge, leaving the Phase 3 rule to carry a named
exception forever; _move `PEOPLE_ENDS` here too_ — it is a second inversion in
the same import, but the people rows belong to the details screen's card and
their owner is Phase 3's question; pulling them now widens the diff past the
move for no Phase-2 benefit; _an `index.ts` barrel for the three_ — the
consumers import from one named file today, and a barrel would hide which of
the three a value comes from, which is the clarity the split buys.

**Consequences.** `src/app/` no longer references `section-config` at all. The
score mapping is now importable by `search/shared` and `search/details` without
either reaching into the other, so the next increment's purity rule
(`shared/ ↛ {details,editor,…}`) can go in with this edge already closed. The
`java-map` rows and the accepted specs that name `section-config.ts` keep their
wording — they record what each increment wrote at the time, and the ledger
carries a stale path already (a 7.25a row names `search/details/components/
governance-quality-cards/`, a folder no longer there) which shows the table
tracks increments, not paths. The
one stale page that describes the file as needing nothing,
`docs/architecture/platform/separation-and-seams-plan.md` (19.6, accepted), is
history too and stays. `section-config.spec.ts` no longer exists, so a future
edit to the table opens `layouts.spec.ts`; the score test now lives in
`search/shared/quality-mapping.spec.ts`, beside the code it pins. The
`@link` from the rules-box sort keys to `qualitySortKey` becomes prose, the one
cross-file reference the split broke.
