# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-870. The search layer rule is grep-enforced, and its four exceptions move to shared

- **Status:** Proposed
- **Increment:** 7.44
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** `search/` is two layers. `shared/` and `meta/` sit at the bottom;
`browse`, `details`, `editor`, and `results` sit above them as peers. A feature
imports a shared layer, never a sibling feature; a shared layer imports no
feature. The rule is enforced by a grep block in `scripts/check-webapp-purity.sh`
(the CI gate that already blocks the legacy constructs), not by a tested rule.
The four edges that broke it move to `shared/`: the write gate
(`can-write-entities.ts`), the write tick (`entity-written.ts`), the people rows
(`people.ts`), and the view draft (`entityFromView`, lifted out of
`view-as-entity.ts`). All twelve consumers of those files repoint to the shared
paths; `view-as-entity.ts` becomes one of them, importing the moved
`entityFromView` back, and the moved function's own tests stay in
`view-as-entity.spec.ts` (its `VIEW` fixture is shared with the save-body tests).

**Why.** 7.43/DD-869 named this rule but left it on paper: turning it on then
would have failed on `catalogue-card → details/shared/people`, so it deferred the
ban to exactly this increment. Four edges remained, and each had the same cause —
a helper two features use lived inside one of them. Every one was already a
peer's: `details` and the layout gate writing on `canWriteEntities`; the editor
firing and `details` hearing `EntityWritten`; the card and the details screen
reading the same `PEOPLE_ENDS`; `details`' governance banner and the editor's
form building the same `entityFromView` draft. A grep over the whole `search/`
tree confirms the moves leave it clean — zero feature→sibling and zero
shared→feature imports across all four features — so the general rule holds with
no named exception, and the gate can ban the whole class instead of four
instances. Grep (not a tested rule) because the tree already obeys the other
grep-enforced rules (WBP-02, WBP-03) the same way: a boundary is a fact about
import lines, review catches its intent, and CI catches the line.

**Considered and rejected.** _Ban only `shared → feature`, leave features
sideways_ — DD-869 named the wider rule, and the grep shows no sideways edge
exists, so banning the wider class costs nothing and stops the next cross-feature
import from shipping; _keep the four helpers in place and add `// eslint-disable`
exceptions_ — that ships the inversion as policy, the thing the rule exists to
remove; _move `entityFromView` into a new `search/view/` layer_ — one function is
not a layer, and `shared/` already holds view-adjacent helpers; _split the
`entityFromView` tests into a new `entity-from-view.spec.ts`_ — the spec's `VIEW`
fixture is shared with the `bodyFromEdits` tests, so a new file would either
duplicate the fixture or extract it, both widening the diff to gain one file
count for no clarity; _a TS-specific layer-lint plugin (eslint-plugin-boundaries)_
— the purity gate is a shell script CI already runs and the webapp's eslint config
is minimal, and a plugin cannot read the tree-level facts the script states in
plain English.

**Consequences.** The four wrong-way edges are closed and cannot reopen without a
failing CI check. `src/app/search/details/shared/` is gone — its only file moved
up to `shared/`, so `shared/` now owns every helper a feature borrows. Because
the rule is grep, a new forbidden import fails `nx test` locally (the gate is a
`dependsOn`) before review, matching how WBP-02/03 already work. The `java-map`
rows and accepted specs that name the old paths keep their wording — they record
what each increment wrote, and the ledger carries stale paths already (a 7.25a
row names a folder long gone) — DD-870 is where the move is recorded. The purity
script's success line names the layers now, and `apps/aurelius-atlas-webapp/AGENTS.md`
states the layer rule where its porting rules live, so the rule is discoverable
where a contributor reads the boundaries.
