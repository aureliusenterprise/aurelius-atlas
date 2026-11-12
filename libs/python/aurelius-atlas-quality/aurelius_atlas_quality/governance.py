"""The governance rule vocabulary: two presence kinds, the rule, and the one-record verdict (GQ-01..GQ-06).

This module is the entity-subject half of the library: a governance rule asks whether one catalogue
record holds a value, and the answer is a boolean verdict, not a score over rows (DD-487). It holds no
DataFrame — the row-mask machinery of :mod:`aurelius_atlas_quality.checks` is the dataset half's. It
shares the leaf's discipline: a closed vocabulary, one parse door, one error type.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from aurelius_atlas_quality.rule import Dimension, KindSpec, QualityRuleError

_GOV_NO_KIND_ERROR = "the rule names no 'checkKind': a stored expression rule needs re-authoring (DV-146)"
_GOV_UNKNOWN_KIND_ERROR = "unknown governance check kind {kind!r}; the vocabulary holds: {known}"
_GOV_UNKNOWN_DIMENSION_ERROR = "unknown dimension {dimension!r}"
_GOV_DIMENSION_MISMATCH_ERROR = "dimension {dimension} does not fit check kind {kind}"
_GOV_MISSING_PARAMS_ERROR = "check kind {kind} needs the parameters {missing}"
_GOV_UNKNOWN_PARAMS_ERROR = "check kind {kind} has no parameters {extra}"
_GOV_ANY_OF_NOT_LIST_ERROR = "anyOf must be a list of attribute names, not {value!r}"


class GovCheckKind(StrEnum):
    """The closed vocabulary of governance rule kinds. A rule names one of these; adding a kind is a release."""

    ATTRIBUTE_PRESENT = "ATTRIBUTE_PRESENT"
    ATTRIBUTE_NOT_EMPTY = "ATTRIBUTE_NOT_EMPTY"


GOV_KINDS: Mapping[GovCheckKind, KindSpec] = {
    GovCheckKind.ATTRIBUTE_PRESENT: KindSpec(
        Dimension.COMPLETENESS,
        frozenset({"attribute"}),
        frozenset({"anyOf"}),
        "the record does not carry the attribute",
    ),
    GovCheckKind.ATTRIBUTE_NOT_EMPTY: KindSpec(
        Dimension.COMPLETENESS,
        frozenset({"attribute"}),
        frozenset({"anyOf"}),
        "the attribute holds no value to show",
    ),
}
"""The governance vocabulary (GQ-03): the same :class:`KindSpec` rows ``KINDS`` uses, so one resource
can serve both. The dimension is COMPLETENESS for both kinds — the dimension every stored governance
rule names. The reason line is the verdict message when the rule stores none (GQ-06)."""


@dataclass(frozen=True)
class GovRule:
    """One governance rule: a presence kind, the attribute it measures, and the rule's own messages (GQ-01).

    ``params`` arrive as ``attribute`` (required) and ``anyOf`` (optional, the legacy ``|`` — GQ-06).
    ``compliant_message`` and ``non_compliant_message`` are the sentences the rule stores for its two
    verdicts; the type's legacy ``compliantMessage``/``nonCompliantMessage`` attributes carry them.
    There is no threshold and no score: a verdict over one record is boolean (DD-487).
    """

    name: str
    kind: GovCheckKind
    dimension: Dimension
    attribute: str
    any_of: tuple[str, ...] = ()
    compliant_message: str | None = None
    non_compliant_message: str | None = None
    guid: str | None = None

    @classmethod
    def from_json(cls, blob: Mapping[str, Any]) -> GovRule:
        """Build a rule from its JSON shape.

        The shape is ``guid``, ``name``, ``checkKind``, ``params`` (``attribute``, ``anyOf``),
        ``compliantMessage``, ``nonCompliantMessage``, and an optional ``dimension``. The ``dimension``
        may be omitted, and then the kind's own is used; when present it must equal the kind's.

        Raises:
            QualityRuleError: the kind is unknown, the dimension disagrees, a parameter is missing or
                not known for the kind, or ``anyOf`` is not a list (GQ-02).
        """
        kind = _gov_kind_of(blob)
        spec = GOV_KINDS[kind]
        params = dict(blob.get("params") or {})
        _gov_check_params(kind, spec, params)
        any_of = params.get("anyOf")
        if any_of is not None and not isinstance(any_of, list):
            raise QualityRuleError(_GOV_ANY_OF_NOT_LIST_ERROR.format(value=any_of))
        raw_attribute = params.get("attribute")
        attribute = str(raw_attribute).strip() if raw_attribute is not None else ""
        if not attribute:
            raise QualityRuleError(_GOV_MISSING_PARAMS_ERROR.format(kind=kind.value, missing=["attribute"]))
        return cls(
            name=str(blob.get("name") or kind.value),
            kind=kind,
            dimension=_gov_dimension_of(blob, kind, spec),
            attribute=attribute,
            any_of=tuple(str(name) for name in (any_of or [])),
            compliant_message=_message(blob.get("compliantMessage")),
            non_compliant_message=_message(blob.get("nonCompliantMessage")),
            guid=blob.get("guid"),
        )


def _message(raw: Any) -> str | None:  # noqa: ANN401 - a stored message is a string or absent
    """A stored message as text, or ``None`` when the rule stores nothing to show."""
    if raw is None or raw == "":
        return None
    return str(raw)


def _gov_kind_of(blob: Mapping[str, Any]) -> GovCheckKind:
    raw = blob.get("checkKind")
    if raw is None:
        raise QualityRuleError(_GOV_NO_KIND_ERROR)
    try:
        return GovCheckKind(str(raw))
    except ValueError:
        known = ", ".join(sorted(kind.value for kind in GovCheckKind))
        raise QualityRuleError(_GOV_UNKNOWN_KIND_ERROR.format(kind=raw, known=known)) from None


def _gov_dimension_of(blob: Mapping[str, Any], kind: GovCheckKind, spec: KindSpec) -> Dimension:
    raw = blob.get("dimension")
    if raw is None:
        return spec.dimension
    try:
        dimension = Dimension(str(raw).upper())
    except ValueError:
        raise QualityRuleError(_GOV_UNKNOWN_DIMENSION_ERROR.format(dimension=raw)) from None
    if dimension is not spec.dimension:
        raise QualityRuleError(_GOV_DIMENSION_MISMATCH_ERROR.format(dimension=dimension.value, kind=kind.value))
    return dimension


def _gov_check_params(kind: GovCheckKind, spec: KindSpec, params: Mapping[str, Any]) -> None:
    missing = spec.required - params.keys()
    if missing:
        raise QualityRuleError(_GOV_MISSING_PARAMS_ERROR.format(kind=kind.value, missing=sorted(missing)))
    extra = params.keys() - spec.required - spec.optional
    if extra:
        raise QualityRuleError(_GOV_UNKNOWN_PARAMS_ERROR.format(kind=kind.value, extra=sorted(extra)))


@dataclass(frozen=True)
class GovVerdict:
    """One rule's answer about one record: compliant or not, with the sentence to show (GQ-04)."""

    rule: GovRule
    compliant: bool
    message: str


def _holds_a_value(value: Any) -> bool:  # noqa: ANN401 - a stored attribute is any JSON value
    """Whether ``value`` is a value at all: present means not null (GQ-04)."""
    return value is not None


def _holds_content(value: Any) -> bool:  # noqa: ANN401 - a stored attribute is any JSON value
    """Whether ``value`` holds content: a filled string or collection, or any other present value (GQ-04)."""
    if isinstance(value, str | list | tuple | set | frozenset | dict):
        return len(value) > 0
    return _holds_a_value(value)


_CHECKS = {
    GovCheckKind.ATTRIBUTE_PRESENT: _holds_a_value,
    GovCheckKind.ATTRIBUTE_NOT_EMPTY: _holds_content,
}


def evaluate_gov_entity(rule: GovRule, attributes: Mapping[str, Any]) -> GovVerdict:
    """Run one governance rule over one record's attributes (GQ-04..GQ-06).

    ``attributes`` are the record's attributes as bare JSON, the draft or the stored entity's. The
    check applies to the rule's attribute and to each ``anyOf`` attribute (GQ-06): one pass makes the
    verdict compliant. An attribute the record does not carry fails the check — it never raises,
    because an editor draft is always missing something (GQ-05). The message is the rule's own
    sentence for its verdict, or the kind's reason line when the rule stores none (GQ-06).
    """
    check = _CHECKS[rule.kind]
    compliant = any(check(attributes.get(name)) for name in (rule.attribute, *rule.any_of))
    stored = rule.compliant_message if compliant else rule.non_compliant_message
    return GovVerdict(rule=rule, compliant=compliant, message=stored or GOV_KINDS[rule.kind].reason)
