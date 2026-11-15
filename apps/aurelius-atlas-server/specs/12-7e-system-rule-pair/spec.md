# 12.7e The system rule answers as a hierarchy pair

- **Status:** in review
- **Pull request:** #374
- **Records:** adds DD-639 (here) and DV-174; amends nothing on the wire. Relies on
  DD-635 (12.7b, the pairs as data), VEV-09 (12.7b, the alternatives travel), and
  GQ-06/ASG-02 (the `|` pair parses and passes on any name). DD-637 (12.7c)
  refused a pair over the other end of this edge; this increment pairs the
  subsystem end on the user's instruction.

## Scope

A system sits in two hierarchies: it holds collections, and it sits beside
other systems through the `parentSystem`/`childSystem` pair
(`m4i_system_parent_assignment` in
`0010-m4i_data_dictionary_model.json`, both ends `array<m4i_system>` SET).
The rule `m4i_system--collections` asked for a collection only, so a system
that groups its content through subsystems — the same shape as the dataset
rule before 12.7b — answered "should have at least one collection".

12.7c's audit left this rule one-sided because the pair over the parent end
saved no node in the sample corpus. The user's product decision now covers the
subsystem end: a system should either have a subsystem or a collection. The
webapp already treats `childSystem` as the subsystems a system owns (the
details drawer's "Subsystems" cards read it), so the edge is a first-class
placement, not a stray attribute.

| Rule                          | Type       | Contention                                         | Treatment                                  |
| ----------------------------- | ---------- | -------------------------------------------------- | ------------------------------------------ |
| `m4i_system--collections`     | 13 systems | a system that groups through subsystems holds none | paired here: `\| length('childSystem', 1)` |
| `m4i_dataset--fields`         | —          | a dataset holds a child dataset                    | paired by 12.7b (DV-171)                   |
| `m4i_field--datasets`         | —          | a struct field hangs off a parent field            | paired by 12.7c (DV-172)                   |
| `m4i_data_entity--attributes` | —          | an entity carries attributes on its children       | paired by 12.7c (DV-172)                   |

The audit's other seven one-sided rules (12.7c's list, minus this one) stay
alone: none has an honest hierarchy alternative.

## Semantics

No new rule id. VEV-09, GQ-06, and ASG-02 already carry a pair end to end; this
increment changes one record as data, as DD-635 and DD-637 did. Python tests
name the ids with `@pytest.mark.covers(..., rules=[...])` (ADR 056).

The record changes in both shipped bundles:

- `m4i_system--collections` (`1afbce14-aebe-4c3f-beba-562ee4aa86b1`):
  expression `length('collections', 1) | length('childSystem', 1)`, name
  "System has a collection or a subsystem", pair sentences for
  `ruleDescription`/`compliantMessage`/`nonCompliantMessage`.

No rule is retired and the pair keeps its demand: a system with neither a
collection nor a subsystem still answers its refusal line (the sample's two
systems without a collection hold no subsystem either, so both stay failing —
the pair saves nobody today and still measures the gap).

## Aurelius origin

- `data/atlas-sample/sample_data.zip` — the record; the metamodel's
  `m4i_system_parent_assignment` (`parentSystem` | `childSystem`, both
  `array<m4i_system>` SET) is the hierarchy the pair reads.
- The webapp's system details sections (`section-config.ts`: the "Subsystems"
  cards seed from `childSystem`) are the UI-side evidence that the end is a
  placement users see.
- The corpus's own `m4i_data_entity--dataDomain` pair is the in-repo
  precedent, unchanged here.

## Deviations

[DV-174](../../../../docs/architecture/conversion/deviations.md): the sample
corpus's system rule is a pair, where the frozen `atlas-dev` oracle judged the
one-name rule. The oracle falsifies for exactly that rule: 13 of its verdict
documents carry a description the record no longer holds, and the renamed
record joins DV-171's name-difference list (5 → 6). No verdict moves — no
sample system carries a subsystem — so every stored answer stays as it was.
The edit was accepted with the damage named (the user's decision, DD-639).

## Acceptance

The pair reads and travels through 12.7b's legs; no new unit leg is needed for
the wire. The proof is the re-baselined 14.6 gates, on the fake client
(`uv run pytest libs/python/aurelius-atlas-core/tests`):

- `test__app_search_governance.py`: 43 of 95 read (unchanged); 2,030 verdicts,
  1,767 met and 263 missed (unchanged — the pair flips nothing in the corpus);
  the 29 moved legacy verdicts still all belong to the four 12.7b/12.7c pairs,
  and the system pair contributes none (DV-174).
- `test__legacy_app_search_fixtures.py`: 337 stale descriptions, all five pair
  rules' (324 + the 13 system verdicts); 6 name differences; the
  `usedattributes`/first-name disagreement still 199 (the oracle is unchanged).
- `test__app_search_indexer.py`: 6 name differences.
- 14.6's reading code is untouched (ASG-02/ASG-04) — only the corpus's rule and
  the counts moved.

Both bundles verified byte-surgical: integrity OK, 690/98 entries, and only the
one rule entry differs from HEAD.
