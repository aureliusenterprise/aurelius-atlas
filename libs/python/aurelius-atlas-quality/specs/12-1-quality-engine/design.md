# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-450. The engine is polars row masks, not Pandera

- **Status:** Proposed
- **Increment:** 12.1
- **Date:** 2026-11-10

**Decision.** Each check kind builds one polars expression over the frame, and
the mask it answers — `True` on the accepted rows — is the check (DQ-03). The
score is the share of accepted rows (DQ-04). No schema-validation library
enters the dependency list: the lib depends on `polars` only.

**Reason.** The first draft of this engine used Pandera, the usual Python
choice for frame checks, and it broke on the stack as first pinned: Pandera
0.36 against pandas 3.1 raises `'FieldInfo' object has no attribute
'set_name'` on every `pa.Field`. Its polars integration does run — probed
2026-11-10 on this interpreter: `pandera[polars]` 0.36 over polars 2.1.0
validates a `LazyFrame`, and `validate(df, lazy=True)` lists every failing
row's index. The decision rests on the answer's shape, not the dependency.
This engine scores every rule on every dataset, and the scanner runs each
rule alone so one bad rule fails alone (DQS-08, 12.2) — a schema answers a
whole frame at once, and one rule with a missing column aborts that
validation. Isolation then forces one call per rule, a schema built per
rule from the stored attributes, and each score read back through a
raised exception's failure-case frame. The polars check API makes the
extra step visible: a check is a function returning a boolean `LazyFrame`
— a row mask. The mask is the part this engine needs, so the engine keeps
it and calls it directly.

**Alternatives.** Pandera over its polars backend, for the contract it
fits: a schema fixed in code over one frame, pass/fail with a report.
Here the rules are data with per-run parameters (freshness scores against
an `as_of`), so a schema would be built per rule and run per rule anyway.
An open check object also fights the closed vocabulary (DD-451): the
engine must refuse to run what it cannot name. Its Narwhals backend
variant, which promises portable checks over several engines, drops the
stored artifact: the failing row's position comes back null there, where
the native backend reports it (probed 2026-11-10, polars 2.1.0) — SQL-lazy
backends have no row order, and this engine scores rows. Source breadth
is the scanner's reader seam instead (12.2): each source becomes a polars
frame before any check runs. A Great Expectations-style suite: it suites
a notebook workflow, not a per-rule score store, and it drags a
checkpoint format the Atlas shapes have no room for. Hand-written pandas:
the same code, slower, and the scanner (12.2) reads sources through
polars anyway.

**Consequences.** The engine's whole dependency surface is `polars`, which the
store client already pulls. Frame input is a polars `DataFrame`, and callers
in 12.2 read sources straight into one. polars 2.x dropped the string-to-date
casts, so the time kinds use the explicit `str.to_date`/`str.to_datetime`
parsers (DQ-03's freshness shapes) — a rule never depends on cast leniency
polars may change again.

### DD-451. Rules are data from a closed vocabulary; stored expressions stay out

- **Status:** Proposed
- **Increment:** 12.1
- **Date:** 2026-11-10

**Decision.** A rule names one of ten check kinds and its parameters (DQ-01),
and parsing validates it against the kind's parameter shape (DQ-02). The
library executes nothing it cannot name: a blob outside the vocabulary raises
instead of running. A custom-rule escape hatch is deliberately absent; it
needs its own decision record before it exists.

**Reason.** The legacy stored a Python expression string per rule and
evaluated it in the Flink job. An expression in the store is code with the
scanner's full privileges — every source reader and every credential in its
environment — and a stored string is invisible to review, testing, and the
trace check (ADR 056). The ten kinds cover every rule the sample corpus
carries and the operators the webapp's rules box shows (7.24). The UI is
already a dumb form over kind-plus-params (DD-447), so a closed vocabulary is
the shape the deployed front end can already send.

**Alternatives.** Ship `eval` behind a flag. It loses on the privilege
argument above, and an unreviewed flag is the vulnerability, not the
mitigation. A sandboxed expression language (simpleeval, asteval): a real
option, and the right shape if custom rules prove necessary — but it is a
second language to spec, test, and pin, and no corpus rule needs it yet. A
plugin entry point per tenant: deployment-time code, which belongs with the
customer-environment plan (12.2), not smuggled into the rule format.

**Consequences.** A legacy rule the map cannot read raises, and the scanner
records it as ERROR (DD-454) — a rule that cannot be authored in the new
vocabulary cannot silently change meaning. When custom rules arrive, the
entry point is a `checkKind` the vocabulary adds, so the storage format and
every reader survive; `spec.md`'s not-delivered table keeps the commitment
visible.

### DD-452. The rollup weighs each dimension once, and an unmeasured dimension is absent

- **Status:** Proposed
- **Increment:** 12.1
- **Date:** 2026-11-10

**Decision.** `summarise` answers each dimension as the mean of its scoring
rules' scores, and the overall score as the mean of the dimensions, each
weighed once (DQ-06). A dimension with no scoring rule is absent from the
summary — not present at zero. A set with no scoring rule at all has
`score=None`.

**Reason.** The legacy score document carried a flat score per rule plus the
dimension labels, and the webapp's pies weight the dimensions equally
(UIC-36/37, 7.24): five wedges, no wedge sized by rule count. A mean over all
rules would let ten completeness rules drown one timeliness rule and make the
overall number disagree with the pie it feeds. Absence rather than zero is
DD-369's posture read from the store side: a dimension nobody measures has no
number, and inventing zero tells the field owner their data is bad when in
fact nothing looked at it.

**Alternatives.** Weight the overall by rule count (a flat mean over rules).
It is the arithmetic default, and it loses exactly where the pie disagrees
with the headline. Weight by dimension severity (accuracy twice completeness):
the corpus ranks no such order and neither does the legacy UI, so a weight
table would be invented policy — a later ADR's decision, not an engine
constant.

**Consequences.** Two numbers in the document set (the dimension map and the
overall) always agree with each other and with the pie. The dimension count
rides with each dimension score (`count` in `DimensionScore`), so a reader can
tell a one-rule dimension from a measured one without a second request.

### DD-453. An empty frame has no score, and an unscored rule stores nothing

- **Status:** Proposed
- **Increment:** 12.1
- **Date:** 2026-11-10

**Decision.** `evaluate` over a frame with no rows answers `score=None`,
`passed=False`, zero rows (DQ-04), and `result_documents` writes no document
for a rule with no score and no overall document when nothing scored (DQ-08).
The score is never 0.0 for want of rows.

**Reason.** This is DD-369 ("render nothing, not zero") moved from the webapp
to its source. 7.24's rule cards render no score precisely because no
evaluator exists; the day one does, an empty extract must not change the
story. A dataset that was truncated at midnight, or a reader that matched no
partitions, answers 0.0 under the careless arithmetic (`0/0` guarded to 0, or
`mean` of nothing read as 0) and the badge goes red by morning. `None` keeps
"not measured" a separate fact the UI already knows how to draw blank.

**Alternatives.** `score=1.0` — vacuous truth, "no row broke the rule". It
makes an unread dataset indistinguishable from a perfect one, which is worse:
a green badge on nothing hides the broken reader. `passed=True` with no score
so the rule stays quiet: a verdict without a measurement is still an
invention, and the document set has no place for half a result.

**Consequences.** Every consumer — the scanner (12.2), the REST surface and
the score box (7.25) — sees `None` and the DD-369 blank, and none of them
needs its own empty-frame guard. The engine raises rather than scores when a
column is missing (DQ-03): "the rule does not fit this data" is an error, not
a zero.

### DD-454. Legacy rules read through a named pair map; the free-text case is an error, not a guess

- **Status:** Proposed
- **Increment:** 12.1
- **Date:** 2026-11-10

**Decision.** `rule_from_atlas_attributes` reads new-vocabulary rules from
`dqcheckkind` plus the `dq`-prefixed parameters, and legacy rules through a
map from the stored `dataqualitytype`/`dataqualityoperator` pair to a check
kind — four pairs, the ones the sample corpus carries (DQ-07). A pair outside
the map raises `QualityRuleError`. DV-146 records the vocabulary change; this
entry fixes how the reader answers what it cannot map.

**Reason.** The corpus stores a rule's identity in that pair plus legacy
parameter attributes (`columnname`, `regularexpression`, `allowedvalues`), and
7.24's box already resolves those entities for display, so the reader must
keep them legible. The legacy's fifth case, the free-text Python expression
on the Flink rule type, maps to no kind — and guessing one (a regex string is
"kind of" a `COLUMN_MATCHES_REGEX` rule) would silently swap an expression's
meaning for a mask's. Raising keeps the failure honest: 12.2 turns it into an
ERROR verdict on the rule with the pair named, a field owner can act on.

**Alternatives.** Best-effort mapping of expression rules to their closest
kind. It loses the audit trail: a wrong score looks like a right score.
Drop unmapped rules from reads entirely: the rules box would quietly shrink,
which is how migrations hide lost data. Wrap every read in a permissive
result type: the engine has exactly one error path and the caller decides
(REST answers 400, the scanner answers ERROR) — a permissive union everywhere
for one decision point is the wrong shape.

**Consequences.** The pair map is one table in `atlas.py` with a test per row,
so a corpus survey that finds a fifth pair adds one row. Values arrive bare or
in the webapp's `{raw: …}` wrapper, so the reader unwraps both (the shapes
2.x's entity read returns). `deviations.md` carries DV-146, and the stored
new-rule attribute names (`dqcheckkind`, `dq*`) are this increment's own
contract for 7.25 and 12.2 to share.
