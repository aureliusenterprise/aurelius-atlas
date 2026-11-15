# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design
log apply: an accepted entry is never edited except its status line, and a changed
decision is a new entry that supersedes the old one.

## Entries

### DD-637. The field and data-entity hierarchy rules become OR pairs

- **Status:** Proposed
- **Increment:** 12.7c
- **Date:** 2026-11-15
- **Supersedes:** none; extends DD-635 (Proposed, 12.7b) to the rest of the corpus

**Decision.** Two more rule records of the sample corpus change in both shipped
bundles (`sample_data.zip`, `only_gov_quality.zip`). `m4i_field--datasets`
(`cad0a3bf-9f7f-464f-aeb5-9ce97eb993b3`) carries the expression
`length('datasets', 1) | length('parentField', 1)` and `m4i_data_entity--attributes`
(`c4d10911-7661-4058-a2df-a25fbed0e093`) carries
`length('attributes', 1) | length('childEntity', 1)`, each with its pair name and
pair sentences. No rule retires and no code changes: GQ-06 and ASG-02 already
parse the whole `|` form, VEV-09 (DD-636) already carries the alternatives on the
verdict, and the editor already paints under each measured control. The audit of
the remaining 91 rules keeps eight one-sided rules as they are, because none of
them has an honest hierarchy alternative (DD-637's spec table names them).

**Reason.** The contention DD-635 fixed for datasets runs through the whole
metamodel: every hierarchy carries a parent end and a child end
(`parentField`/`childField`, `parentEntity`/`childEntity`), and a one-sided rule
penalizes the node that holds its content or placement through the other end.
16 of the sample's 264 fields are nested struct fields (`EFFECTIVE_DATE` and
15 beside it) whose parent field (`payload`) rides the dataset — the rule named
"should belong to a dataset" a field that no dataset can own directly. One data
entity (`Personnel`) carries its eleven attributes on its child entities — the
rule named it empty. The corpus itself already pairs the same shape twice:
`m4i_data_entity--dataDomain | parentEntity` and, since 12.7b, the two dataset
pairs. The pair is the corpus's idiom for a hierarchy edge, not an invention
here. The audit keeps honesty as the bar: a pair over `parentSystem` was refused
because the two systems missing a collection hold no parent either — the pair
would hide a real gap — and the two paired rules still fail a node that holds
neither edge (the empty `test` entity proves it).

**Alternatives.** Pair `m4i_system--collections | parentSystem` and the other
one-sided membership rules (refused: no sample node flips honestly; a pair that
saves nobody softens the rule). Retire the two rules instead (refused: the
demand is real for the 248 direct fields and the 14 attribute-holding entities).
Leave all eight and call the warnings honest (refused: a struct field cannot
belong to a dataset directly — the warning is wrong on its face, the same defect
class as 12.7a's empty picker and 12.7b's dataset pairs).

**Consequences.** 17 stored verdicts move to compliant (16 fields, 1 entity);
the governance gate's met/missed counts move from 1,750/808 to 1,767/791 with
the same 2,558 total. The frozen oracle falsifies for exactly the two rules
(DV-172): 280 stale descriptions (264 + 16), the renamed records join DV-171's
name list (3 → 5), and the three 14.6 gates re-baseline naming every moved
document's rule. The editor paints each pair's line under both controls
(VEV-09 shipped in 12.7b), so the nested-field picker and its parent's picker
agree. The eight kept rules keep their warnings, and the audit's table (in the
spec) is the record of why.
