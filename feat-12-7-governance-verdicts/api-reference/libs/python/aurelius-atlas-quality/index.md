# aurelius-atlas-quality

[![SonarQube Cloud](<https://sonarcloud.io/images/project_badges/sonarcloud-light.svg>)](<https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-quality>)

The data quality engine: a closed vocabulary of ten check kinds, each one a row mask over a polars frame, with its score, rollup, and the store glue.

## Installation

Part of the workspace, through the uv workspace member list.

```
[tool.uv.sources.aurelius-atlas-quality]
workspace = true
```

## Documentation

## aurelius\_atlas\_quality

Data quality for Aurelius Atlas: the closed rule vocabularies, the row-mask engine and the score rollup.

A rule is data: a check kind from a closed vocabulary (:class:`CheckKind` for a dataset's rows, :class:`GovCheckKind` for one catalogue record), a dimension (:class:`Dimension`), and parameters. The library maps a dataset rule to a row mask over a polars DataFrame (:func:`evaluate`), scores it, rolls results up per dimension (:func:`summarise`), answers a governance rule as a boolean verdict over one record (:func:`evaluate_gov_entity`), and converts to and from the shapes the store holds (:func:`rule_from_atlas_attributes`, :func:`rule_from_gov_attributes`, :func:`result_documents`).

Modules:

- **`atlas`** –

  The Atlas glue: rules read from stored entities, results written as score documents.
- **`checks`** –

  The build side of the vocabulary: how each check kind masks a DataFrame (DQ-03).
- **`evaluate`** –

  Evaluation: a rule over a DataFrame, into a score and the rows it rejects (DQ-04, DQ-05).
- **`governance`** –

  The governance rule vocabulary: two presence kinds, the rule, and the one-record verdict (GQ-01..GQ-06).
- **`rule`** –

  The closed rule vocabulary: dimensions, check kinds, and the rule with its parse-time validation (DQ-01, DQ-02).
- **`score`** –

  The score rollup: results per rule, per dimension, and the overall score (DQ-06).

Classes:

- **`CheckKind`** –

  The closed vocabulary of rule kinds. A rule names one of these; adding a kind is a release.
- **`Dimension`** –

  The five quality dimensions, the same five the legacy cards list under `dqscore_*`.
- **`DimensionScore`** –

  One dimension's share of the rules that scored: the row `quality-dimension-list` renders.
- **`DqRule`** –

  One data-quality rule: a check kind, its parameters, its dimension, and the pass threshold (DQ-01).
- **`GovCheckKind`** –

  The closed vocabulary of governance rule kinds. A rule names one of these; adding a kind is a release.
- **`GovRule`** –

  One governance rule: a presence kind, the attribute it measures, and the rule's own messages (GQ-01).
- **`GovVerdict`** –

  One rule's answer about one record: compliant or not, with the sentence to show (GQ-04).
- **`KindSpec`** –

  One vocabulary row: the dimension a kind measures, the parameters it needs, and its reason line.
- **`QualityRuleError`** –

  A rule the vocabulary cannot express: an unknown kind, a wrong dimension, or a missing parameter (DQ-02).
- **`QualitySummary`** –

  The rollup of a set of results: the overall score and the per-dimension scores (DQ-06).
- **`RuleResult`** –

  The outcome of one rule over one frame: its score, its verdict, and the rejected rows.

Functions:

- **`evaluate_gov_entity`** –

  Run one governance rule over one record's attributes (GQ-04..GQ-06).
- **`evaluate_rules`** –

  Run every rule over `df` in order (DQ-05). A column error still raises; see :func:`evaluate`.
- **`result_documents`** –

  The score documents of one run: one per scoring rule, plus the dataset's overall document (DQ-08).
- **`rule_from_atlas_attributes`** –

  Build a rule from the attributes of an `m4i_data_quality` entity (DQ-07).
- **`rule_from_gov_attributes`** –

  Build a governance rule from the attributes of an `m4i_gov_data_quality` entity (GQ-07).
- **`summarise`** –

  Roll results up into the per-dimension and overall scores (DQ-06).

Attributes:

- **`ATLAS_TO_KIND`** (`Mapping[tuple[str, str], CheckKind]`) –

  The legacy rule shapes this port reads: `dataqualitytype` and `dataqualityoperator` to a kind.
- **`CASTABLE_TYPES`** (`frozenset[str]`) –

  The type names a :attr:`CheckKind.COLUMN_TYPE_CASTABLE` rule may name. :mod:`.checks` maps them to casts.
- **`GOV_KINDS`** (`Mapping[GovCheckKind, KindSpec]`) –

  The governance vocabulary (GQ-03): the same :class:`KindSpec` rows `KINDS` uses, so one resource
- **`GOV_RULE_TYPE_NAME`** –

  The Atlas entity type that carries a governance-quality rule (GQ-07).
- **`KINDS`** (`Mapping[CheckKind, KindSpec]`) –
- **`RULE_TYPE_NAME`** –

  The Atlas entity type that carries a data-quality rule.
- **`SCORE_TYPE_NAME`** –

  The document type a scanner writes for one rule's score over one dataset.

### ATLAS\_TO\_KIND

```
ATLAS_TO_KIND: Mapping[tuple[str, str], CheckKind] = {
    ("attribute", "NOTNULL"): CheckKind.COLUMN_NOT_NULL_RATIO,
    ("attribute", "UNIQUE"): CheckKind.COLUMN_UNIQUE_RATIO,
    ("attribute", "REGEX"): CheckKind.COLUMN_MATCHES_REGEX,
    ("attribute", "ENUM"): CheckKind.COLUMN_IN_SET,
}
```

The legacy rule shapes this port reads: `dataqualitytype` and `dataqualityoperator` to a kind.

A rule stored by the legacy application carries that pair. A rule of the new vocabulary names its kind under `dqcheckkind` instead, and has no legacy twin.

### CASTABLE\_TYPES

```
CASTABLE_TYPES: frozenset[str] = frozenset({'int', 'integer', 'long', 'float', 'double', 'date', 'datetime'})
```

The type names a :attr:`CheckKind.COLUMN_TYPE_CASTABLE` rule may name. :mod:`.checks` maps them to casts.

### GOV\_KINDS

```
GOV_KINDS: Mapping[GovCheckKind, KindSpec] = {
    GovCheckKind.ATTRIBUTE_PRESENT: KindSpec(
        Dimension.COMPLETENESS,
        frozenset({"attribute"}),
        frozenset({"anyOf"}),
        "the record does not carry the attribute",
    ),
    GovCheckKind.ATTRIBUTE_NOT_EMPTY: KindSpec(
        Dimension.COMPLETENESS, frozenset({"attribute"}), frozenset({"anyOf"}), "the attribute holds no value to show"
    ),
}
```

The governance vocabulary (GQ-03): the same :class:`KindSpec` rows `KINDS` uses, so one resource can serve both. The dimension is COMPLETENESS for both kinds — the dimension every stored governance rule names. The reason line is the verdict message when the rule stores none (GQ-06).

### GOV\_RULE\_TYPE\_NAME

```
GOV_RULE_TYPE_NAME = 'm4i_gov_data_quality'
```

The Atlas entity type that carries a governance-quality rule (GQ-07).

### KINDS

```
KINDS: Mapping[CheckKind, KindSpec] = {
    CheckKind.COLUMN_NOT_NULL_RATIO: KindSpec(
        Dimension.COMPLETENESS, frozenset({"column"}), frozenset(), "the value is missing"
    ),
    CheckKind.ROW_NOT_EMPTY: KindSpec(
        Dimension.COMPLETENESS, frozenset({"columns"}), frozenset({"minColumns"}), "the row holds too few filled values"
    ),
    CheckKind.COLUMN_UNIQUE_RATIO: KindSpec(
        Dimension.UNIQUENESS, frozenset({"column"}), frozenset(), "the value repeats a value above it"
    ),
    CheckKind.COLUMN_COMPOSITE_UNIQUE: KindSpec(
        Dimension.UNIQUENESS, frozenset({"columns"}), frozenset(), "the row repeats a row above it"
    ),
    CheckKind.COLUMN_MATCHES_REGEX: KindSpec(
        Dimension.VALIDITY, frozenset({"column", "pattern"}), frozenset(), "the value does not match the pattern"
    ),
    CheckKind.COLUMN_IN_SET: KindSpec(
        Dimension.VALIDITY, frozenset({"column", "values"}), frozenset(), "the value is not one of the allowed values"
    ),
    CheckKind.COLUMN_TYPE_CASTABLE: KindSpec(
        Dimension.VALIDITY, frozenset({"column", "type"}), frozenset(), "the value is not a valid value of the type"
    ),
    CheckKind.COLUMN_EQUALS_COLUMN_RATIO: KindSpec(
        Dimension.ACCURACY, frozenset({"column", "otherColumn"}), frozenset(), "the two columns disagree"
    ),
    CheckKind.COLUMN_WITHIN_RANGE: KindSpec(
        Dimension.ACCURACY, frozenset({"column", "min", "max"}), frozenset(), "the value is outside the range"
    ),
    CheckKind.ROW_FRESHNESS_MAX_AGE: KindSpec(
        Dimension.TIMELINESS, frozenset({"column", "maxAgeHours"}), frozenset(), "the row is older than the allowed age"
    ),
}
```

### RULE\_TYPE\_NAME

```
RULE_TYPE_NAME = 'm4i_data_quality'
```

The Atlas entity type that carries a data-quality rule.

### SCORE\_TYPE\_NAME

```
SCORE_TYPE_NAME = 'm4i_dq_score'
```

The document type a scanner writes for one rule's score over one dataset.

### \_\_all\_\_

```
__all__ = [
    "ATLAS_TO_KIND",
    "CASTABLE_TYPES",
    "GOV_KINDS",
    "GOV_RULE_TYPE_NAME",
    "KINDS",
    "RULE_TYPE_NAME",
    "SCORE_TYPE_NAME",
    "CheckKind",
    "Dimension",
    "DimensionScore",
    "DqRule",
    "GovCheckKind",
    "GovRule",
    "GovVerdict",
    "KindSpec",
    "QualityRuleError",
    "QualitySummary",
    "RuleResult",
    "evaluate",
    "evaluate_gov_entity",
    "evaluate_rules",
    "result_documents",
    "rule_from_atlas_attributes",
    "rule_from_gov_attributes",
    "summarise",
]
```

### CheckKind

Bases: `StrEnum`

The closed vocabulary of rule kinds. A rule names one of these; adding a kind is a release.

Attributes:

- **`COLUMN_COMPOSITE_UNIQUE`** –
- **`COLUMN_EQUALS_COLUMN_RATIO`** –
- **`COLUMN_IN_SET`** –
- **`COLUMN_MATCHES_REGEX`** –
- **`COLUMN_NOT_NULL_RATIO`** –
- **`COLUMN_TYPE_CASTABLE`** –
- **`COLUMN_UNIQUE_RATIO`** –
- **`COLUMN_WITHIN_RANGE`** –
- **`ROW_FRESHNESS_MAX_AGE`** –
- **`ROW_NOT_EMPTY`** –

#### COLUMN\_COMPOSITE\_UNIQUE

```
COLUMN_COMPOSITE_UNIQUE = 'COLUMN_COMPOSITE_UNIQUE'
```

#### COLUMN\_EQUALS\_COLUMN\_RATIO

```
COLUMN_EQUALS_COLUMN_RATIO = 'COLUMN_EQUALS_COLUMN_RATIO'
```

#### COLUMN\_IN\_SET

```
COLUMN_IN_SET = 'COLUMN_IN_SET'
```

#### COLUMN\_MATCHES\_REGEX

```
COLUMN_MATCHES_REGEX = 'COLUMN_MATCHES_REGEX'
```

#### COLUMN\_NOT\_NULL\_RATIO

```
COLUMN_NOT_NULL_RATIO = 'COLUMN_NOT_NULL_RATIO'
```

#### COLUMN\_TYPE\_CASTABLE

```
COLUMN_TYPE_CASTABLE = 'COLUMN_TYPE_CASTABLE'
```

#### COLUMN\_UNIQUE\_RATIO

```
COLUMN_UNIQUE_RATIO = 'COLUMN_UNIQUE_RATIO'
```

#### COLUMN\_WITHIN\_RANGE

```
COLUMN_WITHIN_RANGE = 'COLUMN_WITHIN_RANGE'
```

#### ROW\_FRESHNESS\_MAX\_AGE

```
ROW_FRESHNESS_MAX_AGE = 'ROW_FRESHNESS_MAX_AGE'
```

#### ROW\_NOT\_EMPTY

```
ROW_NOT_EMPTY = 'ROW_NOT_EMPTY'
```

### Dimension

Bases: `StrEnum`

The five quality dimensions, the same five the legacy cards list under `dqscore_*`.

Attributes:

- **`ACCURACY`** –
- **`COMPLETENESS`** –
- **`TIMELINESS`** –
- **`UNIQUENESS`** –
- **`VALIDITY`** –

#### ACCURACY

```
ACCURACY = 'ACCURACY'
```

#### COMPLETENESS

```
COMPLETENESS = 'COMPLETENESS'
```

#### TIMELINESS

```
TIMELINESS = 'TIMELINESS'
```

#### UNIQUENESS

```
UNIQUENESS = 'UNIQUENESS'
```

#### VALIDITY

```
VALIDITY = 'VALIDITY'
```

### DimensionScore

```
DimensionScore(dimension: Dimension, score: float, count: int)
```

One dimension's share of the rules that scored: the row `quality-dimension-list` renders.

Attributes:

- **`count`** (`int`) –
- **`dimension`** (`Dimension`) –
- **`score`** (`float`) –

#### count

```
count: int
```

#### dimension

```
dimension: Dimension
```

#### score

```
score: float
```

### DqRule

```
DqRule(
    name: str,
    kind: CheckKind,
    dimension: Dimension,
    params: Mapping[str, Any],
    threshold: float = 1.0,
    guid: str | None = None,
)
```

One data-quality rule: a check kind, its parameters, its dimension, and the pass threshold (DQ-01).

`params` are the kind's parameters, named in camelCase (`column`, `pattern`, `minColumns`). `threshold` is the rule-level pass bar: the rule passes when its score reaches it. `guid` is the GUID of the entity that carries the rule, when it came from the store.

Methods:

- **`from_json`** –

  Build a rule from its JSON shape.

Attributes:

- **`dimension`** (`Dimension`) –
- **`guid`** (`str | None`) –
- **`kind`** (`CheckKind`) –
- **`name`** (`str`) –
- **`params`** (`Mapping[str, Any]`) –
- **`threshold`** (`float`) –

#### dimension

```
dimension: Dimension
```

#### guid

```
guid: str | None = None
```

#### kind

```
kind: CheckKind
```

#### name

```
name: str
```

#### params

```
params: Mapping[str, Any]
```

#### threshold

```
threshold: float = 1.0
```

#### from\_json

```
from_json(blob: Mapping[str, Any]) -> DqRule
```

Build a rule from its JSON shape.

The shape is `guid`, `name`, `checkKind`, `dimension`, `params`, `threshold`. The `dimension` may be omitted, and then the kind's own dimension is used; when present it must equal the kind's.

Raises:

- `QualityRuleError` –

  the kind is unknown, the dimension disagrees, a parameter is missing or not known for the kind, or the threshold is not a ratio (DQ-02).

### GovCheckKind

Bases: `StrEnum`

The closed vocabulary of governance rule kinds. A rule names one of these; adding a kind is a release.

Attributes:

- **`ATTRIBUTE_NOT_EMPTY`** –
- **`ATTRIBUTE_PRESENT`** –

#### ATTRIBUTE\_NOT\_EMPTY

```
ATTRIBUTE_NOT_EMPTY = 'ATTRIBUTE_NOT_EMPTY'
```

#### ATTRIBUTE\_PRESENT

```
ATTRIBUTE_PRESENT = 'ATTRIBUTE_PRESENT'
```

### GovRule

```
GovRule(
    name: str,
    kind: GovCheckKind,
    dimension: Dimension,
    attribute: str,
    any_of: tuple[str, ...] = (),
    compliant_message: str | None = None,
    non_compliant_message: str | None = None,
    guid: str | None = None,
)
```

One governance rule: a presence kind, the attribute it measures, and the rule's own messages (GQ-01).

`params` arrive as `attribute` (required) and `anyOf` (optional, the legacy `|` — GQ-06). `compliant_message` and `non_compliant_message` are the sentences the rule stores for its two verdicts; the type's legacy `compliantMessage`/`nonCompliantMessage` attributes carry them. There is no threshold and no score: a verdict over one record is boolean (DD-487).

Methods:

- **`from_json`** –

  Build a rule from its JSON shape.

Attributes:

- **`any_of`** (`tuple[str, ...]`) –
- **`attribute`** (`str`) –
- **`compliant_message`** (`str | None`) –
- **`dimension`** (`Dimension`) –
- **`guid`** (`str | None`) –
- **`kind`** (`GovCheckKind`) –
- **`name`** (`str`) –
- **`non_compliant_message`** (`str | None`) –

#### any\_of

```
any_of: tuple[str, ...] = ()
```

#### attribute

```
attribute: str
```

#### compliant\_message

```
compliant_message: str | None = None
```

#### dimension

```
dimension: Dimension
```

#### guid

```
guid: str | None = None
```

#### kind

```
kind: GovCheckKind
```

#### name

```
name: str
```

#### non\_compliant\_message

```
non_compliant_message: str | None = None
```

#### from\_json

```
from_json(blob: Mapping[str, Any]) -> GovRule
```

Build a rule from its JSON shape.

The shape is `guid`, `name`, `checkKind`, `params` (`attribute`, `anyOf`), `compliantMessage`, `nonCompliantMessage`, and an optional `dimension`. The `dimension` may be omitted, and then the kind's own is used; when present it must equal the kind's.

Raises:

- `QualityRuleError` –

  the kind is unknown, the dimension disagrees, a parameter is missing or not known for the kind, or `anyOf` is not a list (GQ-02).

### GovVerdict

```
GovVerdict(rule: GovRule, compliant: bool, message: str)
```

One rule's answer about one record: compliant or not, with the sentence to show (GQ-04).

Attributes:

- **`compliant`** (`bool`) –
- **`message`** (`str`) –
- **`rule`** (`GovRule`) –

#### compliant

```
compliant: bool
```

#### message

```
message: str
```

#### rule

```
rule: GovRule
```

### KindSpec

```
KindSpec(dimension: Dimension, required: frozenset[str], optional: frozenset[str], reason: str)
```

One vocabulary row: the dimension a kind measures, the parameters it needs, and its reason line.

Attributes:

- **`dimension`** (`Dimension`) –
- **`optional`** (`frozenset[str]`) –
- **`reason`** (`str`) –
- **`required`** (`frozenset[str]`) –

#### dimension

```
dimension: Dimension
```

#### optional

```
optional: frozenset[str]
```

#### reason

```
reason: str
```

#### required

```
required: frozenset[str]
```

### QualityRuleError

Bases: `ValueError`

A rule the vocabulary cannot express: an unknown kind, a wrong dimension, or a missing parameter (DQ-02).

### QualitySummary

```
QualitySummary(score: float | None, dimensions: tuple[DimensionScore, ...])
```

The rollup of a set of results: the overall score and the per-dimension scores (DQ-06).

`score` is `None` when no rule scored. A dimension with no scoring rule is absent from `dimensions`, never present at zero — an unmeasured dimension says nothing (DD-369).

Attributes:

- **`dimensions`** (`tuple[DimensionScore, ...]`) –
- **`score`** (`float | None`) –

#### dimensions

```
dimensions: tuple[DimensionScore, ...]
```

#### score

```
score: float | None
```

### RuleResult

```
RuleResult(
    rule: DqRule, score: float | None, passed: bool, rows_checked: int, rows_failed: int, failed_rows: DataFrame
)
```

The outcome of one rule over one frame: its score, its verdict, and the rejected rows.

`score` is the share of accepted rows, `None` for an empty frame — nothing was measured, and a score would be invented (the DD-369 posture: render nothing, not zero). `failed_rows` holds the rows the rule rejected, capped at `max_failed_rows`, so a caller can bound what it stores.

Attributes:

- **`failed_rows`** (`DataFrame`) –
- **`passed`** (`bool`) –
- **`rows_checked`** (`int`) –
- **`rows_failed`** (`int`) –
- **`rule`** (`DqRule`) –
- **`score`** (`float | None`) –

#### failed\_rows

```
failed_rows: DataFrame
```

#### passed

```
passed: bool
```

#### rows\_checked

```
rows_checked: int
```

#### rows\_failed

```
rows_failed: int
```

#### rule

```
rule: DqRule
```

#### score

```
score: float | None
```

### evaluate\_gov\_entity

```
evaluate_gov_entity(rule: GovRule, attributes: Mapping[str, Any]) -> GovVerdict
```

Run one governance rule over one record's attributes (GQ-04..GQ-06).

`attributes` are the record's attributes as bare JSON, the draft or the stored entity's. The check applies to the rule's attribute and to each `anyOf` attribute (GQ-06): one pass makes the verdict compliant. An attribute the record does not carry fails the check — it never raises, because an editor draft is always missing something (GQ-05). The message is the rule's own sentence for its verdict, or the kind's reason line when the rule stores none (GQ-06).

### evaluate\_rules

```
evaluate_rules(
    rules: Sequence[DqRule], df: DataFrame, *, as_of: datetime | None = None, max_failed_rows: int = 100
) -> list[RuleResult]
```

Run every rule over `df` in order (DQ-05). A column error still raises; see :func:`evaluate`.

### result\_documents

```
result_documents(
    results: Sequence[RuleResult], summary: QualitySummary, *, dataset_guid: str, run_id: str, run_at_ms: int
) -> list[dict[str, Any]]
```

The score documents of one run: one per scoring rule, plus the dataset's overall document (DQ-08).

Each rule document carries the kind, dimension, score, verdict, and row counts with the run id, so the store can pick the newest row per rule. The overall document has `ruleGuid` null and the summary's per-dimension scores. Rules without a score (an empty frame) produce nothing (DD-369).

### rule\_from\_atlas\_attributes

```
rule_from_atlas_attributes(attributes: Mapping[str, Any]) -> DqRule
```

Build a rule from the attributes of an `m4i_data_quality` entity (DQ-07).

`attributes` may carry the entity's `guid`; it travels onto the rule and onto its documents. The attributes are read under the legacy names — `name`, `dataqualityruledimension",`dataqualitytype`,`dataqualityoperator`,`columnname`,`regularexpression`,`allowedvalues`,`threshold`— and under the new names`dqcheckkind`,`dqcolumn`, and the`dq`-prefixed parameters. Each value is read bare or as the webapp's``` ` wrapper. A legacy pair maps through :data: ``ATLAS\_TO\_KIND\` and takes its parameters from the legacy attributes; a rule of the vocabulary names its kind and parameters directly.

Raises:

- `QualityRuleError` –

  the entity names no kind this port knows, or a parameter is missing. The scanner records such a rule as ERROR — the legacy-expression case.

### rule\_from\_gov\_attributes

```
rule_from_gov_attributes(attributes: Mapping[str, Any]) -> GovRule
```

Build a governance rule from the attributes of an `m4i_gov_data_quality` entity (GQ-07).

`attributes` may carry the entity's `guid`; it travels onto the rule. The rule reads under the vocabulary names — `dqcheckkind`, `dqattribute`, `dqanyOf` — plus `name`, `qualityDimension`, and the rule's messages: `compliantMessage` and `nonCompliantMessage`, the corpus's lowercase `noncompliantMessage` spelling read as the fallback. Each value is read bare or as the webapp's `{"raw": ...}` wrapper.

A rule with no `dqcheckkind` — a stored expression rule, the legacy shape — raises: the caller records it, nothing executes it (DV-146). The legacy `expression` is never read.

Raises:

- `QualityRuleError` –

  the entity names no kind of the governance vocabulary, or a parameter is missing or malformed (GQ-02).

### summarise

```
summarise(results: Sequence[RuleResult]) -> QualitySummary
```

Roll results up into the per-dimension and overall scores (DQ-06).

Each dimension is the mean of its scoring rules' scores, and the overall score the mean of the dimensions. Results without a score (an empty frame) join nothing.

## aurelius\_atlas\_quality.atlas

The Atlas glue: rules read from stored entities, results written as score documents.

This module converts; it holds no I/O. :func:`rule_from_atlas_attributes` reads a stored `m4i_data_quality` rule's attributes into a :class:`~aurelius_atlas_quality.rule.DqRule`, :func:`rule_from_gov_attributes` reads a stored `m4i_gov_data_quality` rule's attributes into a :class:`~aurelius_atlas_quality.governance.GovRule`, and :func:`result_documents` renders a run's results as the documents a scanner writes to the store (DQ-07, DQ-08, GQ-07).

Functions:

- **`result_documents`** –

  The score documents of one run: one per scoring rule, plus the dataset's overall document (DQ-08).
- **`rule_from_atlas_attributes`** –

  Build a rule from the attributes of an `m4i_data_quality` entity (DQ-07).
- **`rule_from_gov_attributes`** –

  Build a governance rule from the attributes of an `m4i_gov_data_quality` entity (GQ-07).

Attributes:

- **`ATLAS_TO_KIND`** (`Mapping[tuple[str, str], CheckKind]`) –

  The legacy rule shapes this port reads: `dataqualitytype` and `dataqualityoperator` to a kind.
- **`GOV_RULE_TYPE_NAME`** –

  The Atlas entity type that carries a governance-quality rule (GQ-07).
- **`RULE_TYPE_NAME`** –

  The Atlas entity type that carries a data-quality rule.
- **`SCORE_TYPE_NAME`** –

  The document type a scanner writes for one rule's score over one dataset.

### ATLAS\_TO\_KIND

```
ATLAS_TO_KIND: Mapping[tuple[str, str], CheckKind] = {
    ("attribute", "NOTNULL"): CheckKind.COLUMN_NOT_NULL_RATIO,
    ("attribute", "UNIQUE"): CheckKind.COLUMN_UNIQUE_RATIO,
    ("attribute", "REGEX"): CheckKind.COLUMN_MATCHES_REGEX,
    ("attribute", "ENUM"): CheckKind.COLUMN_IN_SET,
}
```

The legacy rule shapes this port reads: `dataqualitytype` and `dataqualityoperator` to a kind.

A rule stored by the legacy application carries that pair. A rule of the new vocabulary names its kind under `dqcheckkind` instead, and has no legacy twin.

### GOV\_RULE\_TYPE\_NAME

```
GOV_RULE_TYPE_NAME = 'm4i_gov_data_quality'
```

The Atlas entity type that carries a governance-quality rule (GQ-07).

### RULE\_TYPE\_NAME

```
RULE_TYPE_NAME = 'm4i_data_quality'
```

The Atlas entity type that carries a data-quality rule.

### SCORE\_TYPE\_NAME

```
SCORE_TYPE_NAME = 'm4i_dq_score'
```

The document type a scanner writes for one rule's score over one dataset.

### result\_documents

```
result_documents(
    results: Sequence[RuleResult], summary: QualitySummary, *, dataset_guid: str, run_id: str, run_at_ms: int
) -> list[dict[str, Any]]
```

The score documents of one run: one per scoring rule, plus the dataset's overall document (DQ-08).

Each rule document carries the kind, dimension, score, verdict, and row counts with the run id, so the store can pick the newest row per rule. The overall document has `ruleGuid` null and the summary's per-dimension scores. Rules without a score (an empty frame) produce nothing (DD-369).

### rule\_from\_atlas\_attributes

```
rule_from_atlas_attributes(attributes: Mapping[str, Any]) -> DqRule
```

Build a rule from the attributes of an `m4i_data_quality` entity (DQ-07).

`attributes` may carry the entity's `guid`; it travels onto the rule and onto its documents. The attributes are read under the legacy names — `name`, `dataqualityruledimension",`dataqualitytype`,`dataqualityoperator`,`columnname`,`regularexpression`,`allowedvalues`,`threshold`— and under the new names`dqcheckkind`,`dqcolumn`, and the`dq`-prefixed parameters. Each value is read bare or as the webapp's``` ` wrapper. A legacy pair maps through :data: ``ATLAS\_TO\_KIND\` and takes its parameters from the legacy attributes; a rule of the vocabulary names its kind and parameters directly.

Raises:

- `QualityRuleError` –

  the entity names no kind this port knows, or a parameter is missing. The scanner records such a rule as ERROR — the legacy-expression case.

### rule\_from\_gov\_attributes

```
rule_from_gov_attributes(attributes: Mapping[str, Any]) -> GovRule
```

Build a governance rule from the attributes of an `m4i_gov_data_quality` entity (GQ-07).

`attributes` may carry the entity's `guid`; it travels onto the rule. The rule reads under the vocabulary names — `dqcheckkind`, `dqattribute`, `dqanyOf` — plus `name`, `qualityDimension`, and the rule's messages: `compliantMessage` and `nonCompliantMessage`, the corpus's lowercase `noncompliantMessage` spelling read as the fallback. Each value is read bare or as the webapp's `{"raw": ...}` wrapper.

A rule with no `dqcheckkind` — a stored expression rule, the legacy shape — raises: the caller records it, nothing executes it (DV-146). The legacy `expression` is never read.

Raises:

- `QualityRuleError` –

  the entity names no kind of the governance vocabulary, or a parameter is missing or malformed (GQ-02).

## aurelius\_atlas\_quality.checks

The build side of the vocabulary: how each check kind masks a DataFrame (DQ-03).

Functions:

- **`mask_for`** –

  The boolean mask of the rows the rule accepts, over `df` (DQ-03).

### \_\_all\_\_

```
__all__ = ['mask_for']
```

### mask\_for

```
mask_for(df: DataFrame, kind: CheckKind, params: Mapping[str, Any], as_of: datetime | None = None) -> Series
```

The boolean mask of the rows the rule accepts, over `df` (DQ-03).

`as_of` is the run time, in UTC: a naive value reads as UTC, and a zoned one converts. The freshness kind measures ages against it; the default is now.

Raises:

- `ColumnNotFoundError` –

  a parameter names a column the frame does not have.

## aurelius\_atlas\_quality.evaluate

Evaluation: a rule over a DataFrame, into a score and the rows it rejects (DQ-04, DQ-05).

Classes:

- **`RuleResult`** –

  The outcome of one rule over one frame: its score, its verdict, and the rejected rows.

Functions:

- **`evaluate`** –

  Run `rule` over `df` and return its score, verdict, and rejected rows (DQ-04).
- **`evaluate_rules`** –

  Run every rule over `df` in order (DQ-05). A column error still raises; see :func:`evaluate`.

### RuleResult

```
RuleResult(
    rule: DqRule, score: float | None, passed: bool, rows_checked: int, rows_failed: int, failed_rows: DataFrame
)
```

The outcome of one rule over one frame: its score, its verdict, and the rejected rows.

`score` is the share of accepted rows, `None` for an empty frame — nothing was measured, and a score would be invented (the DD-369 posture: render nothing, not zero). `failed_rows` holds the rows the rule rejected, capped at `max_failed_rows`, so a caller can bound what it stores.

Attributes:

- **`failed_rows`** (`DataFrame`) –
- **`passed`** (`bool`) –
- **`rows_checked`** (`int`) –
- **`rows_failed`** (`int`) –
- **`rule`** (`DqRule`) –
- **`score`** (`float | None`) –

#### failed\_rows

```
failed_rows: DataFrame
```

#### passed

```
passed: bool
```

#### rows\_checked

```
rows_checked: int
```

#### rows\_failed

```
rows_failed: int
```

#### rule

```
rule: DqRule
```

#### score

```
score: float | None
```

### evaluate

```
evaluate(rule: DqRule, df: DataFrame, *, as_of: datetime | None = None, max_failed_rows: int = 100) -> RuleResult
```

Run `rule` over `df` and return its score, verdict, and rejected rows (DQ-04).

An empty frame has no score: the check runs over no rows, so the rule neither passes nor fails.

Raises:

- `ColumnNotFoundError` –

  a parameter names a column the frame does not have. The caller decides — the scanner records the rule as ERROR, an API answers 400.

### evaluate\_rules

```
evaluate_rules(
    rules: Sequence[DqRule], df: DataFrame, *, as_of: datetime | None = None, max_failed_rows: int = 100
) -> list[RuleResult]
```

Run every rule over `df` in order (DQ-05). A column error still raises; see :func:`evaluate`.

## aurelius\_atlas\_quality.rule

The closed rule vocabulary: dimensions, check kinds, and the rule with its parse-time validation (DQ-01, DQ-02).

This module is the leaf of the library: it holds what a rule is, and never a DataFrame. The build side — the row mask each kind asks for — lives in :mod:`aurelius_atlas_quality.checks`.

Classes:

- **`CheckKind`** –

  The closed vocabulary of rule kinds. A rule names one of these; adding a kind is a release.
- **`Dimension`** –

  The five quality dimensions, the same five the legacy cards list under `dqscore_*`.
- **`DqRule`** –

  One data-quality rule: a check kind, its parameters, its dimension, and the pass threshold (DQ-01).
- **`KindSpec`** –

  One vocabulary row: the dimension a kind measures, the parameters it needs, and its reason line.
- **`QualityRuleError`** –

  A rule the vocabulary cannot express: an unknown kind, a wrong dimension, or a missing parameter (DQ-02).

Attributes:

- **`CASTABLE_TYPES`** (`frozenset[str]`) –

  The type names a :attr:`CheckKind.COLUMN_TYPE_CASTABLE` rule may name. :mod:`.checks` maps them to casts.
- **`KINDS`** (`Mapping[CheckKind, KindSpec]`) –

### CASTABLE\_TYPES

```
CASTABLE_TYPES: frozenset[str] = frozenset({'int', 'integer', 'long', 'float', 'double', 'date', 'datetime'})
```

The type names a :attr:`CheckKind.COLUMN_TYPE_CASTABLE` rule may name. :mod:`.checks` maps them to casts.

### KINDS

```
KINDS: Mapping[CheckKind, KindSpec] = {
    CheckKind.COLUMN_NOT_NULL_RATIO: KindSpec(
        Dimension.COMPLETENESS, frozenset({"column"}), frozenset(), "the value is missing"
    ),
    CheckKind.ROW_NOT_EMPTY: KindSpec(
        Dimension.COMPLETENESS, frozenset({"columns"}), frozenset({"minColumns"}), "the row holds too few filled values"
    ),
    CheckKind.COLUMN_UNIQUE_RATIO: KindSpec(
        Dimension.UNIQUENESS, frozenset({"column"}), frozenset(), "the value repeats a value above it"
    ),
    CheckKind.COLUMN_COMPOSITE_UNIQUE: KindSpec(
        Dimension.UNIQUENESS, frozenset({"columns"}), frozenset(), "the row repeats a row above it"
    ),
    CheckKind.COLUMN_MATCHES_REGEX: KindSpec(
        Dimension.VALIDITY, frozenset({"column", "pattern"}), frozenset(), "the value does not match the pattern"
    ),
    CheckKind.COLUMN_IN_SET: KindSpec(
        Dimension.VALIDITY, frozenset({"column", "values"}), frozenset(), "the value is not one of the allowed values"
    ),
    CheckKind.COLUMN_TYPE_CASTABLE: KindSpec(
        Dimension.VALIDITY, frozenset({"column", "type"}), frozenset(), "the value is not a valid value of the type"
    ),
    CheckKind.COLUMN_EQUALS_COLUMN_RATIO: KindSpec(
        Dimension.ACCURACY, frozenset({"column", "otherColumn"}), frozenset(), "the two columns disagree"
    ),
    CheckKind.COLUMN_WITHIN_RANGE: KindSpec(
        Dimension.ACCURACY, frozenset({"column", "min", "max"}), frozenset(), "the value is outside the range"
    ),
    CheckKind.ROW_FRESHNESS_MAX_AGE: KindSpec(
        Dimension.TIMELINESS, frozenset({"column", "maxAgeHours"}), frozenset(), "the row is older than the allowed age"
    ),
}
```

### CheckKind

Bases: `StrEnum`

The closed vocabulary of rule kinds. A rule names one of these; adding a kind is a release.

Attributes:

- **`COLUMN_COMPOSITE_UNIQUE`** –
- **`COLUMN_EQUALS_COLUMN_RATIO`** –
- **`COLUMN_IN_SET`** –
- **`COLUMN_MATCHES_REGEX`** –
- **`COLUMN_NOT_NULL_RATIO`** –
- **`COLUMN_TYPE_CASTABLE`** –
- **`COLUMN_UNIQUE_RATIO`** –
- **`COLUMN_WITHIN_RANGE`** –
- **`ROW_FRESHNESS_MAX_AGE`** –
- **`ROW_NOT_EMPTY`** –

#### COLUMN\_COMPOSITE\_UNIQUE

```
COLUMN_COMPOSITE_UNIQUE = 'COLUMN_COMPOSITE_UNIQUE'
```

#### COLUMN\_EQUALS\_COLUMN\_RATIO

```
COLUMN_EQUALS_COLUMN_RATIO = 'COLUMN_EQUALS_COLUMN_RATIO'
```

#### COLUMN\_IN\_SET

```
COLUMN_IN_SET = 'COLUMN_IN_SET'
```

#### COLUMN\_MATCHES\_REGEX

```
COLUMN_MATCHES_REGEX = 'COLUMN_MATCHES_REGEX'
```

#### COLUMN\_NOT\_NULL\_RATIO

```
COLUMN_NOT_NULL_RATIO = 'COLUMN_NOT_NULL_RATIO'
```

#### COLUMN\_TYPE\_CASTABLE

```
COLUMN_TYPE_CASTABLE = 'COLUMN_TYPE_CASTABLE'
```

#### COLUMN\_UNIQUE\_RATIO

```
COLUMN_UNIQUE_RATIO = 'COLUMN_UNIQUE_RATIO'
```

#### COLUMN\_WITHIN\_RANGE

```
COLUMN_WITHIN_RANGE = 'COLUMN_WITHIN_RANGE'
```

#### ROW\_FRESHNESS\_MAX\_AGE

```
ROW_FRESHNESS_MAX_AGE = 'ROW_FRESHNESS_MAX_AGE'
```

#### ROW\_NOT\_EMPTY

```
ROW_NOT_EMPTY = 'ROW_NOT_EMPTY'
```

### Dimension

Bases: `StrEnum`

The five quality dimensions, the same five the legacy cards list under `dqscore_*`.

Attributes:

- **`ACCURACY`** –
- **`COMPLETENESS`** –
- **`TIMELINESS`** –
- **`UNIQUENESS`** –
- **`VALIDITY`** –

#### ACCURACY

```
ACCURACY = 'ACCURACY'
```

#### COMPLETENESS

```
COMPLETENESS = 'COMPLETENESS'
```

#### TIMELINESS

```
TIMELINESS = 'TIMELINESS'
```

#### UNIQUENESS

```
UNIQUENESS = 'UNIQUENESS'
```

#### VALIDITY

```
VALIDITY = 'VALIDITY'
```

### DqRule

```
DqRule(
    name: str,
    kind: CheckKind,
    dimension: Dimension,
    params: Mapping[str, Any],
    threshold: float = 1.0,
    guid: str | None = None,
)
```

One data-quality rule: a check kind, its parameters, its dimension, and the pass threshold (DQ-01).

`params` are the kind's parameters, named in camelCase (`column`, `pattern`, `minColumns`). `threshold` is the rule-level pass bar: the rule passes when its score reaches it. `guid` is the GUID of the entity that carries the rule, when it came from the store.

Methods:

- **`from_json`** –

  Build a rule from its JSON shape.

Attributes:

- **`dimension`** (`Dimension`) –
- **`guid`** (`str | None`) –
- **`kind`** (`CheckKind`) –
- **`name`** (`str`) –
- **`params`** (`Mapping[str, Any]`) –
- **`threshold`** (`float`) –

#### dimension

```
dimension: Dimension
```

#### guid

```
guid: str | None = None
```

#### kind

```
kind: CheckKind
```

#### name

```
name: str
```

#### params

```
params: Mapping[str, Any]
```

#### threshold

```
threshold: float = 1.0
```

#### from\_json

```
from_json(blob: Mapping[str, Any]) -> DqRule
```

Build a rule from its JSON shape.

The shape is `guid`, `name`, `checkKind`, `dimension`, `params`, `threshold`. The `dimension` may be omitted, and then the kind's own dimension is used; when present it must equal the kind's.

Raises:

- `QualityRuleError` –

  the kind is unknown, the dimension disagrees, a parameter is missing or not known for the kind, or the threshold is not a ratio (DQ-02).

### KindSpec

```
KindSpec(dimension: Dimension, required: frozenset[str], optional: frozenset[str], reason: str)
```

One vocabulary row: the dimension a kind measures, the parameters it needs, and its reason line.

Attributes:

- **`dimension`** (`Dimension`) –
- **`optional`** (`frozenset[str]`) –
- **`reason`** (`str`) –
- **`required`** (`frozenset[str]`) –

#### dimension

```
dimension: Dimension
```

#### optional

```
optional: frozenset[str]
```

#### reason

```
reason: str
```

#### required

```
required: frozenset[str]
```

### QualityRuleError

Bases: `ValueError`

A rule the vocabulary cannot express: an unknown kind, a wrong dimension, or a missing parameter (DQ-02).

## aurelius\_atlas\_quality.score

The score rollup: results per rule, per dimension, and the overall score (DQ-06).

Classes:

- **`DimensionScore`** –

  One dimension's share of the rules that scored: the row `quality-dimension-list` renders.
- **`QualitySummary`** –

  The rollup of a set of results: the overall score and the per-dimension scores (DQ-06).

Functions:

- **`summarise`** –

  Roll results up into the per-dimension and overall scores (DQ-06).

### DimensionScore

```
DimensionScore(dimension: Dimension, score: float, count: int)
```

One dimension's share of the rules that scored: the row `quality-dimension-list` renders.

Attributes:

- **`count`** (`int`) –
- **`dimension`** (`Dimension`) –
- **`score`** (`float`) –

#### count

```
count: int
```

#### dimension

```
dimension: Dimension
```

#### score

```
score: float
```

### QualitySummary

```
QualitySummary(score: float | None, dimensions: tuple[DimensionScore, ...])
```

The rollup of a set of results: the overall score and the per-dimension scores (DQ-06).

`score` is `None` when no rule scored. A dimension with no scoring rule is absent from `dimensions`, never present at zero — an unmeasured dimension says nothing (DD-369).

Attributes:

- **`dimensions`** (`tuple[DimensionScore, ...]`) –
- **`score`** (`float | None`) –

#### dimensions

```
dimensions: tuple[DimensionScore, ...]
```

#### score

```
score: float | None
```

### summarise

```
summarise(results: Sequence[RuleResult]) -> QualitySummary
```

Roll results up into the per-dimension and overall scores (DQ-06).

Each dimension is the mean of its scoring rules' scores, and the overall score the mean of the dimensions. Results without a score (an empty frame) join nothing.
