"""The Aurelius-native shapes of ``/api/aurelius/v1``, as the client's contract (CAV-01..CAV-04, DD-562).

The shapes of the Aurelius-only endpoints — the semantic search's body, the rule
vocabulary, one check kind, the rule validation's verdict, and the view search
door's request and answer — are the server app's (``aurelius_atlas_server/models.py``),
never Apache Atlas's, so the client cannot import them (DD-562). This module repeats
them the way ``lineage.py`` repeats the lineage body (CL-12): the client and the
server state the same wire shape, each in its own library, and each answer still
arrives as a model. The view search's cards are the model library's ``EntityCard``
models, reused whole (DD-309).

``SemanticSearchParameters`` extends the model library's ``QuickSearchParameters``
exactly as the server's does: quick search's parameters plus the ``mode``.
"""

from typing import Any

from aurelius_atlas_model.discovery import QuickSearchParameters
from aurelius_atlas_model.typedef import AtlasModel
from aurelius_atlas_model.views import EntityCard
from pydantic import Field


class SemanticSearchParameters(QuickSearchParameters):
    """Quick search's parameters and the ``mode`` of a search by meaning (SBM-01, SBM-04, CAV-02).

    ``mode`` is ``semantic`` (default) or ``hybrid``. The client sends what it
    was given: the mode and the empty query are the server's ``BAD_REQUEST``s
    (CL-12), checked by no method of the client.
    """

    mode: str = "semantic"


class QualityKind(AtlasModel):
    """One check kind of the rule vocabulary (QRE-01, CAV-04): its dimension, parameters and reason line."""

    name: str
    dimension: str
    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    reason: str = ""


class QualityVocabulary(AtlasModel):
    """The vocabulary ``GET /quality/kinds`` answers (QRE-01, DD-475, CAV-04)."""

    kinds: list[QualityKind] = Field(default_factory=list)
    castable_types: list[str] = Field(default_factory=list)
    threshold_min: float = 0.0
    threshold_max: float = 1.0


class QualityRuleCheck(AtlasModel):
    """The verdict of ``POST /quality/rules/validate`` (QRE-02/03, DD-476, CAV-04).

    A rule the vocabulary reads names its kind and dimension; one it cannot read
    carries the engine's own reason. Both answer 200 (CAV-04): an unreadable rule
    is the product of the endpoint, not a rejected request.
    """

    valid: bool = False
    kind: str | None = None
    dimension: str | None = None
    reason: str | None = None


class ViewSearchRequest(AtlasModel):
    """The request of ``POST /api/aurelius/v1/search`` (AVR-02, DD-584, CLV-04).

    The view search door's own shape, mirroring the server's model of it: flat
    ``limit``/``offset`` paging, ``filters`` by field name or ``all``/``any``/``none``,
    ``facets`` a list of field names or an object of them with sizes, ``sort`` one
    field or a list of them. The door reads the raw body and answers any unknown
    key itself (AVR-13), so this model documents the shape rather than enforcing
    it — as the server's own model states, and as ``SemanticSearchParameters``
    sends no mode check (CL-12), this client sends no filter or facet check either.
    """

    query: str | None = None
    mode: str | None = None
    """``keyword`` (default), ``semantic`` or ``hybrid`` (ASV-01)."""
    filters: dict[str, Any] | None = None
    facets: list[str] | dict[str, Any] | None = None
    sort: Any = None
    limit: int | None = None
    offset: int | None = None


class ViewSearchAnswer(AtlasModel):
    """The answer of ``POST /api/aurelius/v1/search`` (AVR-08, CLV-04).

    ``cards`` holds the 16.1 cards of the page's hits, parsed into the model
    library's ``EntityCard`` models (DD-309); ``facets`` holds each asked field's
    ``{value, count}`` entries; ``total`` counts every hit.
    """

    cards: list[EntityCard] = Field(default_factory=list)
    facets: dict[str, Any] = Field(default_factory=dict)
    total: int = 0
