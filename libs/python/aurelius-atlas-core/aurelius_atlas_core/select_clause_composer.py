"""``SelectClauseComposer``: a DSL query's ``select`` items, their labels and aggregates (DSP-01 to DSP-04).

Atlas's class also writes the Gremlin of each item; here it keeps what an item reads (an attribute, the entity, or
an aggregate) for ``select_clause_projections``. ``DSLVisitor.visitSelectExpr`` builds it from the syntax tree.
"""

from dataclasses import dataclass, field
from enum import Enum

from aurelius_atlas_dsl.dsl_tree import CountClause, MaxClause, MinClause, SelectExpr, SumClause
from aurelius_atlas_typesystem.attribute import AtlasAttribute


class Aggregator(Enum):
    """``AggregatorFlag``."""

    NONE = "NONE"
    COUNT = "COUNT"
    MIN = "MIN"
    MAX = "MAX"
    SUM = "SUM"


@dataclass
class SelectClauseComposer:
    """The items of a ``select``: per item its label, its text, its aggregator and what it reads."""

    labels: list[str]
    items: list[str]
    aggregators: list[Aggregator]
    attributes: list[AtlasAttribute | None] = field(default_factory=list)
    primitive: set[int] = field(default_factory=set)
    is_select_noop: bool = False
    introduced_types: int = 0

    @classmethod
    def of(cls, select: SelectExpr) -> SelectClauseComposer:
        """``visitSelectExpr``: an item's label is its ``as`` name, else its text; an aggregate's item its argument,
        ``count`` for ``count()`` (DSP-01).
        """  # noqa: D205 - one sentence
        labels, items, aggregators = [], [], []
        for expression in select.expressions:
            comp_e = expression.expr.comp_e
            labels.append(expression.alias.text if expression.alias is not None else expression.text)
            match comp_e:
                case CountClause():
                    items.append("count")
                    aggregators.append(Aggregator.COUNT)
                case SumClause() | MinClause() | MaxClause():
                    items.append(comp_e.expr.text)
                    aggregators.append(_AGGREGATORS[type(comp_e)])
                case _:
                    items.append(expression.expr.text)
                    aggregators.append(Aggregator.NONE)
        return cls(labels, items, aggregators, [None] * len(items))

    @property
    def has_aggregators(self) -> bool:
        """``hasAggregators``."""
        return any(aggregator is not Aggregator.NONE for aggregator in self.aggregators)

    def is_aggregator_with_argument(self, index: int) -> bool:
        """``isAggregatorWithArgument``: ``max``, ``min`` or ``sum``."""
        return self.aggregators[index] in {Aggregator.MAX, Aggregator.MIN, Aggregator.SUM}

    @property
    def has_multiple_referred_types(self) -> bool:
        """``hasMultipleReferredTypes``."""
        return self.introduced_types > 1

    @property
    def has_mixed_attributes(self) -> bool:
        """``hasMixedAttributes``: referred and primitive items together."""
        return self.introduced_types > 0 and bool(self.primitive)


_AGGREGATORS = {SumClause: Aggregator.SUM, MinClause: Aggregator.MIN, MaxClause: Aggregator.MAX}
