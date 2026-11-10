"""The score rollup: results per rule, per dimension, and the overall score (DQ-06)."""

from collections.abc import Sequence
from dataclasses import dataclass

from aurelius_atlas_quality.evaluate import RuleResult
from aurelius_atlas_quality.rule import Dimension


@dataclass(frozen=True)
class DimensionScore:
    """One dimension's share of the rules that scored: the row ``quality-dimension-list`` renders."""

    dimension: Dimension
    score: float
    count: int


@dataclass(frozen=True)
class QualitySummary:
    """The rollup of a set of results: the overall score and the per-dimension scores (DQ-06).

    ``score`` is ``None`` when no rule scored. A dimension with no scoring rule is absent from
    ``dimensions``, never present at zero — an unmeasured dimension says nothing (DD-369).
    """

    score: float | None
    dimensions: tuple[DimensionScore, ...]


def summarise(results: Sequence[RuleResult]) -> QualitySummary:
    """Roll results up into the per-dimension and overall scores (DQ-06).

    Each dimension is the mean of its scoring rules' scores, and the overall score the mean of the
    dimensions. Results without a score (an empty frame) join nothing.
    """
    by_dimension: dict[Dimension, list[float]] = {}
    for result in results:
        if result.score is None:
            continue
        by_dimension.setdefault(result.rule.dimension, []).append(result.score)
    dimensions = tuple(
        DimensionScore(dimension, sum(scores) / len(scores), len(scores))
        for dimension, scores in sorted(by_dimension.items(), key=lambda item: item[0].value)
    )
    overall = sum(d.score for d in dimensions) / len(dimensions) if dimensions else None
    return QualitySummary(overall, dimensions)
