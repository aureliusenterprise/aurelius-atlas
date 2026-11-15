# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design
log apply: an accepted entry is never edited except its status line, and a changed
decision is a new entry that supersedes the old one.

## Entries

### DD-635. The sample corpus's two dataset rules become OR pairs

- **Status:** Proposed
- **Increment:** 12.7b
- **Date:** 2026-11-15
- **Supersedes:** none; edits data, not a rule of any spec

**Decision.** Four rule records of the sample corpus change in both shipped
bundles (`sample_data.zip`, `only_gov_quality.zip`). `m4i_dataset--fields`
(`cfd24715-125d-46e2-854d-b0c1b16340bf`) carries the expression
`length('fields', 1) | length('childDataset', 1)`, `m4i_dataset--collections`
(`fb2c608f-d7ff-4574-8c2d-a240c8c79e91`) carries
`length('collections', 1) | length('parentDataset', 1)`, and each carries the
pair name and pair sentences for `ruleDescription`, `compliantMessage`, and
`nonCompliantMessage`. The two presence rules the pairs replace
(`m4i_dataset--childDataset`, `m4i_dataset--parentDataset`) carry `active: false`
in place of deletion. No code change makes the pair work: GQ-06 and ASG-02
already parse the whole `|` form and the engine passes on the first name or any
alternative.

**Reason.** The product's rule for a dataset is a pair: it must hold a field or
a child dataset, and it must belong to a collection or have a parent. The four
one-name records answer a dataset that meets the rule through its other half
with a warning line, on every surface — the editor banner, the details box, the
rule pages — because each rule measures half the rule. The corpus's own
`m4i_data_entity--domained` record (`length('dataDomain', 1) |
length('parentEntity', 1)`) is the precedent: the store, the 12.6 grammar, and
14.6's engine all already carry an OR pair end to end, so the fix is data.
Deactivation over deletion, because `atlas-export-order.json` names the two
retired GUIDs and a deleted record breaks the bundle's own import order;
VEV-03's reading and DET-42's search both hide an inactive rule, so the retired
lines leave every surface with one attribute edit.

**Alternatives.** Write the pair as two rules and OR them in the UI (refused:
the banner shows one line per rule, and a "both halves miss" pair of warnings
cannot show one pass for one half). Leave the records and teach the engine
dataset-specific logic (refused: the rule is data; a hard-coded pair contradicts
GQ-06's reading). Delete the two retired rules (refused: the export-order file
names their GUIDs, and the corpus's own removal idiom is deactivation).

**Consequences.** Eight of the sample's datasets answer the pair sentences
differently: each holds a child (or a parent) without a field (or a collection)
and moves from its refusal line to its compliant one — 12 stored verdicts,
counted by the re-baselined 14.6 gate. The frozen `atlas-dev` oracle falsifies
for exactly the two edited rules (DV-171): 44 of its verdict documents carry the
old `ruleDescription`, 12 of its verdicts hold the old verdict, and the renamed
records join DD-485's name-difference list. The three 14.6 gates re-baseline with
the damage named per document — each moved verdict is one of the pair's own, and
every other one of the oracle's 1,612 verdicts still answers as it was. The
`only_gov_quality.zip` bundle carries the same edit so the two bundles stay the
same 95 rules; `test__m4i_models.py` compares only type definitions against the
bundles, so it is unmoved.

### DD-636. An OR verdict names every attribute it measures

- **Status:** Proposed
- **Increment:** 12.7b
- **Date:** 2026-11-15
- **Supersedes:** none; extends VEV-02 (12.7, DD-498, Proposed) and EDT-24
  (7.24, amended by 12.7/12.7a, DD-498/DD-633, Proposed)

**Decision.** `GovernanceVerdict` grows an optional `anyOf`: the JSON list of the
names that follow the rule's first in its expression, in order (GQ-06's
alternatives, ASG-02's parse). The aux API sends the key only when the list is
non-empty — a one-name verdict omits it wholly (the route answers with
`response_model_exclude_none`), so the parity scenarios' whole-body comparison of
a one-name answer is unchanged. The TS twin grows the same optional field. The
editor paints a verdict under each rendered control whose name the verdict
carries in `attribute` or `anyOf` (EDT-24 amended): the filter tests the control
against both sides, so a pair's line rides both pickers once each. The
description alias of DD-633 runs over the same filter unchanged.

**Reason.** A pair verdict measures two pickers and names one. With DD-635's
edit shipped as data, the fields pair's line could ride only the Fields picker:
a person who picks a child sees the warning under Child Dataset stay put while
an unseen line under Fields quietly turns green — the banner contradicts itself
across the two controls the rule measures. The wire had no field to carry the
second name; the engine already holds it (`GovRule.any_of`). The legacy did the
same thing: its governance documents list every name of the pair in
`usedattributes` (the 16 `domained` documents of the frozen oracle name both
`dataDomain` and `parentEntity`), and the legacy editor's card map displayed a
line under each name's card. 14.6's `usedattributes` joins the honest reading in
the same PR — the engine already stored only its first name, which was wrong for
a pair the same way.

**Alternatives.** Paint the pair's line only under its first name (refused: the
picker that carries the passing half keeps a stale warning — the exact wrong
verdict 12.7a retired). Send the whole expression on the verdict and parse it in
the browser (refused: the wire is typed data, not grammar; VEV-02's shape stands).
Resolve alternatives to a second verdict per name (refused: one rule answers one
verdict by VEV-02's letter, and the rule box counts rules, not names).

**Consequences.** One new optional key on the aux API's answer: an old client
ignores it, and the details box (DET-42, joined on `ruleGuid`) is unmoved. The
webapp's verdict type and its 727-test suite carry the shape. The banner can now
show the same line twice on one screen — under each picker it measures — which is
the honest reading of a pair, and a rule whose alternative names no rendered
control paints nowhere for that half, as VEV-02 states for a one-name rule.
