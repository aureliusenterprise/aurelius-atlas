# 7.44 Search keeps its layers

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-870 (here). No new rule ids. Cites EDT-09/TEN-05 (7.7a, 15.6:
  the write gate that moved), WFE-01/WFE-02 (19.6, DD-327/DD-803: the write tick
  that moved), VDE-01/VDR-05/EDT-15 (16.5c, 16.5b, 7.7c, DD-608: the view draft
  that moved), DET-23/VCF-15/AVS-10/ASD-06 (7.21a, 16.5f: the People rows that
  moved), and DD-869 (7.43: the layer rule this increment makes enforceable).

## Scope

`search/` had four wrong-way imports — code two screens needed living inside one
of them, so the other reached across. They were the last ones standing after
7.43 moved the score mapping, and each was a candidate for the boundary rule
7.43's design named but could not yet turn on. This increment moves all four
into the shared layer and then enforces the rule.

The moves (each a leaf or a pure extraction, no value changes):

- `search/editor/can-write-entities.ts` → `search/shared/can-write-entities.ts`.
  The details screen and the search layout both gate their write affordances on
  it (EDT-09), so it was not the editor's. Its spec moves with it.
- `search/editor/entity-written.ts` → `search/shared/entity-written.ts`. The
  editor fires the write tick, the details screen hears it (WFE-01/WFE-02) — a
  two-party event, so it lives between them, not inside the firing side. It has
  no spec of its own (its behaviour is asserted where it is fired and heard).
- `search/details/shared/people.ts` → `search/shared/people.ts`. The rich
  catalogue card (`search/shared/catalogue-card.component.ts`, VCF-15) has read
  the same three role ends since 16.5f, so `shared/` was importing **up** into
  `details/` for them (the `PEOPLE_ENDS` edge 7.43 left open on purpose).
- `entityFromView` lifted out of `search/editor/view-as-entity.ts` into a new
  `search/shared/entity-from-view.ts`. The details screen's governance banner
  (EDT-23) built the same draft the editor's form helpers do, so it imported
  `../../editor/view-as-entity` across the boundary. The function is a pure leaf
  (data-access types only), so lifting it is a move; `view-as-entity.ts` imports
  it back and keeps `bodyFromEdits` and the conflict re-seed helpers, which only
  the editor uses.

Twelve consumers repoint to the new paths (eight production: `gov-quality.state`,
`related-sections.state`, `details.component`, `editor-state`,
`entity-editor.component`, `view-as-entity`, `catalogue-card.component`,
`search-layout.component`; four specs: `details.component.spec`,
`editor-state.spec`, `view-as-entity.spec`, `testing/harness.spec`). The moved
`entityFromView` tests stay in `view-as-entity.spec.ts`, which already builds the
`VIEW` fixture the `bodyFromEdits` tests share — the spec file neither grows nor
splits (81 files, unchanged).

Then the boundary rule turns on in `scripts/check-webapp-purity.sh` (which CI
already runs as a `dependsOn` of `test`). It greps `search/` and fails if a
feature (`browse`, `details`, `editor`, `results`) imports a sibling feature, or
if a shared layer (`shared`, `meta`) imports any feature — the tree's actual
shape once the four edges closed.

It does **not** deliver: any behaviour, template, or string change; a rename of
the rule-id references or `java-map` rows that name the old paths (those record
the increment that wrote them — DD-870 carries the move); a move of the editor's
`bodyFromEdits` or the conflict helpers (only the editor uses them, so they stay
put); a rule id for the boundary (it is grep-enforced, like WBP-02/WBP-03, not a
tested rule — see DD-870); or the layout rules for `src/testing/` beyond the one
import it repoints.

## Semantics

No new rule ids. What this increment pins, as stated:

- **The moves carry no value.** Each function/type moves byte-for-byte; only
  import lines change. Proven by the unchanged totals: 1,045 tests in 81 files,
  same as 7.43, with the moved symbols' own tests asserting exactly what they
  asserted before.
- **The tree is layered, and the gate now proves it.** The four features read
  only down into `shared/` and `meta/`; neither shared layer reads a feature. The
  gate is red on a forbidden import and green on the tree as it stands — verified
  by injecting a probe `details → editor` import (red), then removing it (green).
- **A shared helper has a shared home.** When two features need the same code it
  moves to a shared layer, so neither reaches into the other. That is the whole
  content of the four moves: the write gate, the write tick, the people rows, and
  the view draft were never one feature's.
- **The trace tool sees no change.** Webapp TS specs name rule ids in test names,
  not in `covers()` marks, and no test text moved — `uv run aurelius-atlas-trace
check` reports the same single pre-existing finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 ships no shared-layer rule and no equivalent of the write
tick, the view draft, or the shared people rows — all four are Aurelius code
ported in earlier increments. Re-homing a helper adds nothing a parity test can
see, so this increment adds no row to
[Java map](../../../../docs/architecture/conversion/java-map.md).

## Deviations

None from Apache Atlas. Moving a function between files changes no value a parity
test can observe, so the increment adds no row to
[Deviations](../../../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                          | Command                                                                                                                           | Level |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----- |
| The suite passes with the same total as before | `nx test aurelius-atlas-webapp -c ci`                                                                                             | 1     |
| The gate stays green on the moved tree         | `nx test aurelius-atlas-webapp -c ci` (purity `dependsOn`)                                                                        | 1     |
| The gate goes red on a forbidden import        | inject a `details → editor` import, `bash …/check-webapp-purity.sh`, remove                                                       | 0     |
| No old path is imported anywhere               | `grep -rn "editor/can-write-entities\|editor/entity-written\|details/shared/people\|\.\./\.\./editor/view-as-entity" src` — empty | 0     |
| The bundle still type-checks and builds        | `nx build aurelius-atlas-webapp`                                                                                                  | 1     |
| Lint clean (0 errors)                          | `nx lint aurelius-atlas-webapp`                                                                                                   | 0     |
| Every rule id still names a test               | `uv run aurelius-atlas-trace check`                                                                                               | 0     |

Before 7.44: 1,045 tests in 81 files. After: 1,045 tests in 81 files — the spec
that would have split (the moved `entityFromView` tests) stays in
`view-as-entity.spec.ts` because its `VIEW` fixture is shared, so no file is
gained or lost.
