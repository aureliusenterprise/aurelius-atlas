# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design
log apply: an accepted entry is never edited except its status line, and a changed
decision is a new entry that supersedes the old one.

## Entries

### DD-639. The system rule pairs a collection with a subsystem

- **Status:** Proposed
- **Increment:** 12.7e
- **Date:** 2026-11-15
- **Supersedes:** none; narrows DD-637 (Proposed, 12.7c), which refused a pair
  over the other end of this edge

**Decision.** One rule record of the sample corpus changes in both shipped
bundles (`sample_data.zip`, `only_gov_quality.zip`). `m4i_system--collections`
(`1afbce14-aebe-4c3f-beba-562ee4aa86b1`) carries the expression
`length('collections', 1) | length('childSystem', 1)` with its pair name
("System has a collection or a subsystem") and pair sentences. No rule retires
and no code changes: GQ-06 and ASG-02 already parse the whole `|` form, VEV-09
(DD-636) already carries the alternatives on the verdict, and the editor
already paints under each measured control.

**Reason.** The user asked for it directly: a system should either have a
subsystem or a collection. The metamodel carries the edge —
`m4i_system_parent_assignment` joins `parentSystem` and `childSystem`, both
`array<m4i_system>` SET — and the webapp already shows `childSystem` as the
subsystems a system owns, so grouping through subsystems is a placement users
see, not a hidden attribute. DD-637 refused the system pair because its audit
tested the parent end and no sample system holds it; the subsystem end is the
one the product question is about, and the refusal's reason ("a pair would hide
a real gap") does not apply the same way: the pair keeps its demand for the
node that holds neither edge, and in the corpus the two systems without a
collection hold no subsystem either, so both keep failing. The pair changes the
rule's text today and measures the honest shape on any store where systems do
group through subsystems.

**Alternatives.** Keep the rule one-sided (refused: the user's product call
covers the subsystem end, and the one-sided warning repeats the 12.7b/12.7c
defect class on the third hierarchy). Pair over `parentSystem` too (refused:
12.7c's reason stands — no sample node holds it, and a system's parent is not
where its content lives). Retire the rule (refused: the completeness demand is
real for the eleven systems that hold a collection directly).

**Consequences.** No stored verdict moves: the governance gate keeps its
43 read, 2,030 verdicts, 1,767 met and 263 missed, and the 29 moved documents
still all belong to the four 12.7b/12.7c pairs. The frozen oracle falsifies
for exactly this rule (DV-174): 13 stale descriptions (324 → 337 across the
five pair rules) and the renamed record joins DV-171's name list (5 → 6, in
both the fixtures and indexer gates). `docs/architecture/conversion/index.md`
and `deviations.md` carry the row in the same pull request.
