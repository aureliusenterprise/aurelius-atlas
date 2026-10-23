"""The governance-quality answer of the validate-entity API (CL-40, VE-02; DD-114).

The body the 8.3 mock answers — the four cards the webapp's editor renders, the
``AppSearchResult<GovQualitySearchObject>`` shape of the legacy
``libs/atlas/api::GovQualityApi`` (ADR 055 R4) — stated as models so a caller
parses it and the app's constant is checked against one shape (VE-02, DV-14).

Every leaf is a ``{"raw": …}`` wrapper, and the ``doc-…`` ids, string
``compliant`` flags and ``_meta.engine`` of the mock are part of the browser
contract, so they are modelled as they arrive, not normalised. The card keys and
``isNonCompliant`` are camelCase, the legacy's names.
"""

from pydantic import BaseModel, ConfigDict, Field


class GovQualityValue(BaseModel):
    """A ``{"raw": …}`` wrapper — every leaf of the governance document is one (VE-02)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw: str | list[str]
    """The value: a string, or a list of strings (``usedattributes``)."""


class GovQualityMeta(BaseModel):
    """The ``_meta`` of an item: the engine, score and document id (VE-02)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    engine: str
    """The engine that produced the item; the mock names ``atlas-dev-gov-quality`` (DV-14)."""

    score: int
    """The item's score."""

    id: str
    """The document id; the mock's ``doc-…`` ids are the browser contract."""


class GovQualityItem(BaseModel):
    """One governance check: a verdict item of a card (VE-02)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result: GovQualityValue
    """The human-readable verdict."""

    dataqualitytype: GovQualityValue
    """The kind of check; the mock's items are ``attribute`` checks (the legacy's lower-case name)."""

    usedattributes: GovQualityValue
    """The entity attributes the check reads."""

    name: GovQualityValue
    """The check's name; the mock's items name ``Attribute - <key>``."""

    compliant: GovQualityValue
    """The verdict flag, a string ``'0'``/``'1'`` — as the legacy emits it (VE-02)."""

    meta: GovQualityMeta = Field(alias="_meta")
    """The producing engine's record."""

    id: GovQualityValue
    """The item's document id, wrapped like every leaf."""


class ValidationCard(BaseModel):
    """One governance card: the items of one aspect, with the card's verdict (VE-02)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[GovQualityItem] = Field(default_factory=list)
    """The checks of this card."""

    is_non_compliant: bool = Field(alias="isNonCompliant")
    """Whether any item fails; the editor's badge."""


class ValidationResponse(BaseModel):
    """The ``POST /`` answer: the four governance cards (VE-02, DV-14; CL-40).

    The keys are the legacy's — ``dataEntity``, ``definition``, ``domainLead``,
    ``name`` — the aspects the editor's governance panel renders.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid", frozen=True)

    data_entity: ValidationCard = Field(alias="dataEntity")
    definition: ValidationCard
    domain_lead: ValidationCard = Field(alias="domainLead")
    name: ValidationCard
