"""The answers of the Aurelius-only endpoints: what ``/api/aurelius/v1`` and ``/api/as/v1`` write (QRE, SBM, ASE).

These are not Apache Atlas shapes, so they live here rather than in ``aurelius-atlas-model``: the quality
vocabulary is the deployed engine's (QRE-01, DD-475), the rule check is its parser's verdict (QRE-02), the
semantic body is quick search's parameters plus a mode (SBM-01), and the App Search answer is Elastic
App Search's own shape, which the original webapp expects (ASE-09, DD-527).
"""

from typing import Any

from aurelius_atlas_model.base import AtlasModel, JavaInt
from aurelius_atlas_model.discovery import QuickSearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, validate_query_length
from aurelius_atlas_model.params import FILTERS_WITHOUT_TYPE, NEGATIVE_PAGE
from pydantic import Field


class QualityKind(AtlasModel):
    """One check kind of the rule vocabulary (QRE-01): its dimension, parameters and reason line."""

    name: str
    dimension: str
    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    reason: str = ""


class QualityVocabulary(AtlasModel):
    """The vocabulary ``GET /quality/kinds`` answers (QRE-01, DD-475).

    Every kind of the engine beside the types a threshold casts to and the bounds it must lie within.
    """

    kinds: list[QualityKind] = Field(default_factory=list)
    castable_types: list[str] = Field(default_factory=list)
    threshold_min: float = 0.0
    threshold_max: float = 1.0


class QualityRuleCheck(AtlasModel):
    """The verdict of ``POST /quality/rules/validate`` (QRE-02/03, DD-476).

    A rule the vocabulary reads names its kind and dimension; one it cannot read carries the engine's own
    reason. Both answer 200: an unreadable rule is this endpoint's product, not a rejected request.
    """

    valid: bool = False
    kind: str | None = None
    dimension: str | None = None
    reason: str | None = None


class SemanticSearchParameters(QuickSearchParameters):
    """Quick search's parameters and the ``mode`` of a search by meaning (SBM-01, SBM-04).

    ``mode`` is ``semantic`` (default) or ``hybrid``; the query is required, and ``sortBy`` is refused —
    a search by meaning is ordered by meaning.
    """

    mode: str = "semantic"

    def checked(self) -> bool:
        """The search by meaning's own rules, in Atlas's order; whether it is ``hybrid`` (SBM-04).

        Raises:
            AtlasError: ``BAD_REQUEST`` for another ``mode``, no query, a negative page, filters with no type,
                or a ``sortBy``; ``INVALID_QUERY_LENGTH`` for a query of more than 4,096 characters.
        """
        if self.mode not in _MODES:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, _UNKNOWN_MODE)
        if not self.query or not self.query.strip():
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, _NO_QUERY)
        validate_query_length(self.query)
        if self.limit < 0 or self.offset < 0:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, NEGATIVE_PAGE)
        if not self.type_name and self.entity_filters is not None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, FILTERS_WITHOUT_TYPE)
        if self.sort_by:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, _NO_SORT)
        return self.mode == "hybrid"


_MODES = ("semantic", "hybrid")
_NO_QUERY = "A search by meaning needs a query"
_NO_SORT = "A search by meaning is ordered by meaning: sortBy is not taken"
_UNKNOWN_MODE = "mode must be one of semantic, hybrid"


class AppSearchPage(AtlasModel):
    """The page of an App Search answer's ``meta`` (ASE-09)."""

    current: JavaInt = 1
    total_pages: JavaInt = 0
    total_results: JavaInt = 0
    size: JavaInt = 10


class AppSearchEngineInfo(AtlasModel):
    """The engine an App Search answer came from (ASE-09)."""

    name: str = ""
    type: str = "default"


class AppSearchMeta(AtlasModel):
    """The ``meta`` of an App Search answer (ASE-09): alerts, warnings, precision, page, engine, request id."""

    alerts: list[Any] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    precision: JavaInt = 2
    page: AppSearchPage = Field(default_factory=AppSearchPage)
    engine: AppSearchEngineInfo = Field(default_factory=AppSearchEngineInfo)
    request_id: str = ""


class AppSearchAnswer(AtlasModel):
    """The answer of ``POST /engines/{engine}/search`` (ASE-09, DD-527).

    Each result holds the fields asked for, ``id`` always, and its ``_meta``; ``facets`` holds each facet
    field's values and counts. Both are open objects: which fields appear is the request's doing.
    """

    meta: AppSearchMeta = Field(default_factory=AppSearchMeta)
    results: list[dict[str, Any]] = Field(default_factory=list)
    facets: dict[str, Any] = Field(default_factory=dict)


class AppSearchRequest(AtlasModel):
    """The query document of an App Search search (ASE-04): what the original webapp's proxy sends.

    An unknown field in ``filters``, ``facets`` or ``sort`` is refused with 400; ``other`` keys are ignored,
    so they are not declared here.
    """

    query: str | None = None
    filters: list[dict[str, Any]] | None = None
    facets: dict[str, Any] | None = None
    sort: list[dict[str, Any]] | None = None
    page: dict[str, Any] | None = None
    result_fields: dict[str, Any] | None = None
    search_fields: dict[str, Any] | None = None


class ViewSearchRequest(AtlasModel):
    """The request of ``POST /api/aurelius/v1/search`` (AVR-02, DD-584).

    The door's own shape: flat ``limit``/``offset`` paging, ``filters`` by field
    name or ``all``/``any``/``none``, ``facets`` a list of field names or an
    object of them with sizes, ``sort`` one field or a list of them. The door
    reads the raw body and answers any unknown key itself (AVR-13), so this
    model documents the shape rather than enforcing it.
    """

    query: str | None = None
    filters: dict[str, Any] | None = None
    facets: list[str] | dict[str, Any] | None = None
    sort: Any = None
    limit: int | None = None
    offset: int | None = None


class ViewSearchAnswer(AtlasModel):
    """The answer of ``POST /api/aurelius/v1/search`` (AVR-08).

    ``cards`` holds the 16.1 cards of the page's hits; ``facets`` holds each
    asked field's ``{value, count}`` entries; ``total`` counts every hit.
    """

    cards: list[dict[str, Any]] = Field(default_factory=list)
    facets: dict[str, Any] = Field(default_factory=dict)
    total: int = 0
