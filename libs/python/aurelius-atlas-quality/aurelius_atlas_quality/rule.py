"""The closed rule vocabulary: dimensions, check kinds, and the rule with its parse-time validation (DQ-01, DQ-02).

This module is the leaf of the library: it holds what a rule is, and never a DataFrame. The build side
— the row mask each kind asks for — lives in :mod:`aurelius_atlas_quality.checks`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class QualityRuleError(ValueError):
    """A rule the vocabulary cannot express: an unknown kind, a wrong dimension, or a missing parameter (DQ-02)."""


_NO_KIND_ERROR = "the rule has no 'checkKind'"
_UNKNOWN_KIND_ERROR = "unknown check kind {kind!r}; the vocabulary holds: {known}"
_UNKNOWN_DIMENSION_ERROR = "unknown dimension {dimension!r}"
_DIMENSION_MISMATCH_ERROR = "dimension {dimension} does not fit check kind {kind}"
_MISSING_PARAMS_ERROR = "check kind {kind} needs the parameters {missing}"
_UNKNOWN_PARAMS_ERROR = "check kind {kind} has no parameters {extra}"
_THRESHOLD_NOT_NUMBER_ERROR = "threshold {threshold!r} is not a number"
_THRESHOLD_NOT_RATIO_ERROR = "threshold {threshold} is not a ratio between 0 and 1"
_UNKNOWN_TYPE_ERROR = "unknown type {type!r}; the castable types are {types}"


class Dimension(StrEnum):
    """The five quality dimensions, the same five the legacy cards list under ``dqscore_*``."""

    ACCURACY = "ACCURACY"
    COMPLETENESS = "COMPLETENESS"
    TIMELINESS = "TIMELINESS"
    UNIQUENESS = "UNIQUENESS"
    VALIDITY = "VALIDITY"


class CheckKind(StrEnum):
    """The closed vocabulary of rule kinds. A rule names one of these; adding a kind is a release."""

    COLUMN_COMPOSITE_UNIQUE = "COLUMN_COMPOSITE_UNIQUE"
    COLUMN_EQUALS_COLUMN_RATIO = "COLUMN_EQUALS_COLUMN_RATIO"
    COLUMN_IN_SET = "COLUMN_IN_SET"
    COLUMN_MATCHES_REGEX = "COLUMN_MATCHES_REGEX"
    COLUMN_NOT_NULL_RATIO = "COLUMN_NOT_NULL_RATIO"
    COLUMN_TYPE_CASTABLE = "COLUMN_TYPE_CASTABLE"
    COLUMN_UNIQUE_RATIO = "COLUMN_UNIQUE_RATIO"
    COLUMN_WITHIN_RANGE = "COLUMN_WITHIN_RANGE"
    ROW_FRESHNESS_MAX_AGE = "ROW_FRESHNESS_MAX_AGE"
    ROW_NOT_EMPTY = "ROW_NOT_EMPTY"


CASTABLE_TYPES: frozenset[str] = frozenset({"int", "integer", "long", "float", "double", "date", "datetime"})
"""The type names a :attr:`CheckKind.COLUMN_TYPE_CASTABLE` rule may name. :mod:`.checks` maps them to casts."""

_RATIO_FLOOR = 0.0
_RATIO_CEILING = 1.0


@dataclass(frozen=True)
class KindSpec:
    """One vocabulary row: the dimension a kind measures, the parameters it needs, and its reason line."""

    dimension: Dimension
    required: frozenset[str]
    optional: frozenset[str]
    reason: str


KINDS: Mapping[CheckKind, KindSpec] = {
    CheckKind.COLUMN_NOT_NULL_RATIO: KindSpec(
        Dimension.COMPLETENESS, frozenset({"column"}), frozenset(), "the value is missing"
    ),
    CheckKind.ROW_NOT_EMPTY: KindSpec(
        Dimension.COMPLETENESS,
        frozenset({"columns"}),
        frozenset({"minColumns"}),
        "the row holds too few filled values",
    ),
    CheckKind.COLUMN_UNIQUE_RATIO: KindSpec(
        Dimension.UNIQUENESS, frozenset({"column"}), frozenset(), "the value repeats a value above it"
    ),
    CheckKind.COLUMN_COMPOSITE_UNIQUE: KindSpec(
        Dimension.UNIQUENESS, frozenset({"columns"}), frozenset(), "the row repeats a row above it"
    ),
    CheckKind.COLUMN_MATCHES_REGEX: KindSpec(
        Dimension.VALIDITY,
        frozenset({"column", "pattern"}),
        frozenset(),
        "the value does not match the pattern",
    ),
    CheckKind.COLUMN_IN_SET: KindSpec(
        Dimension.VALIDITY,
        frozenset({"column", "values"}),
        frozenset(),
        "the value is not one of the allowed values",
    ),
    CheckKind.COLUMN_TYPE_CASTABLE: KindSpec(
        Dimension.VALIDITY,
        frozenset({"column", "type"}),
        frozenset(),
        "the value is not a valid value of the type",
    ),
    CheckKind.COLUMN_EQUALS_COLUMN_RATIO: KindSpec(
        Dimension.ACCURACY,
        frozenset({"column", "otherColumn"}),
        frozenset(),
        "the two columns disagree",
    ),
    CheckKind.COLUMN_WITHIN_RANGE: KindSpec(
        Dimension.ACCURACY,
        frozenset({"column", "min", "max"}),
        frozenset(),
        "the value is outside the range",
    ),
    CheckKind.ROW_FRESHNESS_MAX_AGE: KindSpec(
        Dimension.TIMELINESS,
        frozenset({"column", "maxAgeHours"}),
        frozenset(),
        "the row is older than the allowed age",
    ),
}


@dataclass(frozen=True)
class DqRule:
    """One data-quality rule: a check kind, its parameters, its dimension, and the pass threshold (DQ-01).

    ``params`` are the kind's parameters, named in camelCase (``column``, ``pattern``, ``minColumns``).
    ``threshold`` is the rule-level pass bar: the rule passes when its score reaches it. ``guid`` is the
    GUID of the entity that carries the rule, when it came from the store.
    """

    name: str
    kind: CheckKind
    dimension: Dimension
    params: Mapping[str, Any]
    threshold: float = 1.0
    guid: str | None = None

    @classmethod
    def from_json(cls, blob: Mapping[str, Any]) -> DqRule:
        """Build a rule from its JSON shape.

        The shape is ``guid``, ``name``, ``checkKind``, ``dimension``, ``params``, ``threshold``. The
        ``dimension`` may be omitted, and then the kind's own dimension is used; when present it must
        equal the kind's.

        Raises:
            QualityRuleError: the kind is unknown, the dimension disagrees, a parameter is missing
                or not known for the kind, or the threshold is not a ratio (DQ-02).
        """
        kind = _kind_of(blob)
        spec = KINDS[kind]
        params = dict(blob.get("params") or {})
        _check_params(kind, spec, params)
        dimension = _dimension_of(blob, kind, spec)
        threshold = _threshold_of(blob)
        return cls(
            name=str(blob.get("name") or kind.value),
            kind=kind,
            dimension=dimension,
            params=params,
            threshold=threshold,
            guid=blob.get("guid"),
        )


def _kind_of(blob: Mapping[str, Any]) -> CheckKind:
    raw = blob.get("checkKind")
    if raw is None:
        raise QualityRuleError(_NO_KIND_ERROR)
    try:
        return CheckKind(str(raw))
    except ValueError:
        known = ", ".join(sorted(kind.value for kind in CheckKind))
        raise QualityRuleError(_UNKNOWN_KIND_ERROR.format(kind=raw, known=known)) from None


def _dimension_of(blob: Mapping[str, Any], kind: CheckKind, spec: KindSpec) -> Dimension:
    raw = blob.get("dimension")
    if raw is None:
        return spec.dimension
    try:
        dimension = Dimension(str(raw).upper())
    except ValueError:
        raise QualityRuleError(_UNKNOWN_DIMENSION_ERROR.format(dimension=raw)) from None
    if dimension is not spec.dimension:
        raise QualityRuleError(_DIMENSION_MISMATCH_ERROR.format(dimension=dimension.value, kind=kind.value))
    return dimension


def _threshold_of(blob: Mapping[str, Any]) -> float:
    raw = blob.get("threshold", 1.0)
    try:
        threshold = float(raw)
    except TypeError, ValueError:
        raise QualityRuleError(_THRESHOLD_NOT_NUMBER_ERROR.format(threshold=raw)) from None
    if not _RATIO_FLOOR <= threshold <= _RATIO_CEILING:
        raise QualityRuleError(_THRESHOLD_NOT_RATIO_ERROR.format(threshold=threshold))
    return threshold


def _check_params(kind: CheckKind, spec: KindSpec, params: Mapping[str, Any]) -> None:
    missing = spec.required - params.keys()
    if missing:
        raise QualityRuleError(_MISSING_PARAMS_ERROR.format(kind=kind.value, missing=sorted(missing)))
    extra = params.keys() - spec.required - spec.optional
    if extra:
        raise QualityRuleError(_UNKNOWN_PARAMS_ERROR.format(kind=kind.value, extra=sorted(extra)))
    if kind is CheckKind.COLUMN_TYPE_CASTABLE and str(params["type"]).lower() not in CASTABLE_TYPES:
        raise QualityRuleError(_UNKNOWN_TYPE_ERROR.format(type=params["type"], types=sorted(CASTABLE_TYPES)))
