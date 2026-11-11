# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-487. Governance checks evaluate one record's attributes, not a frame

- **Status:** Proposed
- **Increment:** 12.6
- **Date:** 2026-11-11

**Decision.** The governance half of the engine is its own module, `governance`,
with its own rule type and a verdict over a plain attributes mapping
(GQ-01, GQ-04). No polars frame enters it, and DD-450's mask machinery stays
the dataset half's. The two halves share the leaf's discipline — a closed
vocabulary, one parse door, one error type — and nothing else.

**Reason.** The subjects differ. A 12.1 kind measures a column across the rows
of a dataset extract and answers a ratio; a governance rule asks whether one
catalogue record holds a value, and the only data the caller has is the entity
attributes of a draft or a stored record. A one-row frame would smuggle the
wrong shape: every mask builder in `checks.py` is a column statistic, and a
null-accepting ratio rule over one row answers 1.0 or 0.0 through machinery
built for thousands (DQ-03, DQ-04). The verdict is boolean (DD-489), so none
of the scoring, rollup, or score-document code applies either. Keeping one
module per subject also keeps 12.1's dependency story true in the browser
path: 7.28's validate-before-save reads the governance module without pulling
frame evaluation behind it.

**Alternatives.** One `DqRule` with an entity-subject kind set inside `KINDS`
(refused: `KindSpec` carries a dimension and parameters, but every 12.1
consumer — the scanner's door, the QRE-01 resource, the 7.27 form — iterates
`KINDS` and expects each kind to answer a row mask; a hidden subject switch
inside the hot loop is the fork this avoids). A pandas row (refused: DD-450
rejects the library outright, and an attributes mapping is what the server and
webapp already hold). Forcing gov rules through the scanner (refused: a gov
rule has no dataset; DQS-03 walks a rule's `fields` end, which gov rules do
not have).

### DD-488. The governance vocabulary is two presence kinds

- **Status:** Proposed
- **Increment:** 12.6
- **Date:** 2026-11-11

**Decision.** `GOV_KINDS` holds two rows: `ATTRIBUTE_PRESENT` (the attribute
holds a value, GQ-04) and `ATTRIBUTE_NOT_EMPTY` (the value holds content,
GQ-04), each with the optional `anyOf` list that restates the legacy `|`
(GQ-06). The fifteen legacy quality functions are not a vocabulary, and the
thirteen unused ones are not ported.

**Reason.** The shipped corpus fixes the set. The legacy
`m4i-governance-data-quality` definitions use three shapes over 27 rules:
`length('x', 1)` fifteen times, `completeness('x')` eleven times, and one
`length('a', 1) | length('b', 1)`. Every rule names dimension `completeness`.
A governance rule that needs more than presence is a dataset rule in the wrong
place — the `validity('x', […])`-style checks live on `m4i_data_quality` and
read through 12.1's vocabulary. DD-451's rule applies: a stored expression
outside the vocabulary raises and re-authors, and re-authoring the two legacy
functions into two kinds covers every stored governance rule, so nothing in
the corpus needs a third.

**Alternatives.** One kind with a mode parameter (refused: the editor renders
`KindSpec` rows as the choice, 7.27's posture; a mode picker inside a kind
forks the form). Porting the full legacy function set as kinds (refused:
thirteen kinds no rule uses, each needing a parameter form and a test — DD-451
ships the closed set the product uses). A generic "present in any of" kind
alone, folding `length` into it (refused: the two functions disagree on the
empty string — `completeness` scores it 1, `length` scores it 0 — and GQ-04
keeps that distinction instead of silently changing verdicts for stored
rules).

### DD-489. A gov verdict is boolean and answers with the rule's own message

- **Status:** Proposed
- **Increment:** 12.6
- **Date:** 2026-11-11

**Decision.** `evaluate_gov_entity` answers `compliant`, the rule's dimension,
the kind, and the message; no score, no threshold, no row counts, and no
`m4i_dq_score` document (GQ-01, GQ-04, GQ-06). The message is the rule's
`compliantMessage` or `nonCompliantMessage` — the fields the type already
carries for this — with the kind's reason line as the fallback.

**Reason.** Over one record a ratio is the record itself: present or not, with
nothing to average. The legacy agreed — its row score was 1 or 0, and the
`dq_score` summary only existed because Flink averaged rows. A score field
would invite the scanner's consumers to read a gov rule as a 0-or-100 percent
dataset score, which it is not. The messages are the point of the surface:
every stored rule carries both sentences, and the editor banner shows exactly
one of them (the mock cards VE-02 froze that display). DD-369's "render
nothing, not zero" needs no application here — a boolean never invents a
zero.

**Alternatives.** Reusing `RuleResult` with `score=1.0|0.0` (refused: carries
`rows_checked` and a threshold verdict the surface cannot fill honestly, and
7.28's banner would have to un-invent the score). Reusing `result_documents`
to stamp `m4i_dq_score` per entity (refused: the scoreKey is
`{datasetGuid}/{ruleGuid}`, a gov rule has no dataset, and per-record score
entities would flood the store — a bulk re-validation surface is a later
increment's decision with its own record). The engine composing fixed message
text ("This entity has a name") as the mock cards do (refused: the rule
already stores its own sentence; a stored rule's message is its content, not
the engine's).

### DD-490. Patch 002 adds three attributes and deletes nothing

- **Status:** Proposed
- **Increment:** 12.6
- **Date:** 2026-11-11

**Decision.** `002-gov_data_quality_vocabulary.json` applies patch 001's
envelope to `m4i_gov_data_quality`: `ADD_ATTRIBUTE`, `applyToVersion` 1.0,
`updateToVersion` 1.1, id `TYPEDEF_PATCH_M4I_0011_002`. It adds
`dqcheckkind`, `dqattribute`, and `dqanyOf`, and touches nothing else. The
legacy `expression`, `expressionVersion`, `ruleType`, and `qualityDimension`
stay on the type.

**Reason.** Patch 001 is the on-record precedent for adding vocabulary to a
shipped m4i type (DD-457): the server applies the patch folder at boot
idempotently, so no migration script runs. Removing the legacy attributes
would delete stored values on the next write (EWR-09 materialises primitives,
and a typedef removal drops the value), which breaks ADR 046's keep-the-data
posture and DV-148's message that a field leaves the _form_, not the type —
7.27 set that pattern for `m4i_data_quality`, and the gov type follows it.
The three new names skip the type's `dqcolumn` collision story: gov rules
measure a catalogue attribute, not a dataset column, so `dqattribute` names
the parameter honestly and the 7.28 form renders one picker.

**Alternatives.** Renaming `expression`'s meaning onto `dqcheckkind` by patch
removal (refused: silently reinterprets stored text). Storing the gov
vocabulary only in code, no patch (refused: the editor form and 7.28's
validate-before-save read the typedef's attributes, and a store that rejects
`dqcheckkind` on a gov entity fails the save). A new `m4i_gov_data_quality_v2`
type (refused: splits the search surface and the webapp's type chrome for no
gain — patching is the recorded path, ADR 023).
