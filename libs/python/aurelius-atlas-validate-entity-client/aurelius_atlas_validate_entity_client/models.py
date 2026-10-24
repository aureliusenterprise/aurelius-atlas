"""The governance-quality answer of the validate-entity API (CL-40, VE-02; DD-114).

The body the 8.3 mock answers — the four cards the webapp's editor renders, the
``AppSearchResult<GovQualitySearchObject>`` shape of the legacy
``libs/atlas/api::GovQualityApi`` (ADR 055 R4) — stated as models so a caller
parses it and the app's constant is checked against one shape (VE-02, DV-50).

Every leaf is a ``{"raw": …}`` wrapper, and the ``doc-…`` ids, string
``compliant`` flags and ``_meta.engine`` of the mock are part of the browser
contract, so they are modelled as they arrive, not normalised. The card keys and
``isNonCompliant`` are camelCase, the legacy's names.
"""

from pydantic import BaseModel, ConfigDict, Field


# VE-02.
class GovQualityValue(BaseModel):
    """A ``{"raw": …}`` wrapper — every leaf of the governance document is one."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw: str | list[str] = Field(
        description="The value: a string, or a list of strings (``usedattributes``).",
    )


# VE-02.
class GovQualityMeta(BaseModel):
    """The ``_meta`` of an item: the engine, score and document id."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    engine: str = Field(
        description="The engine that produced the item, e.g. ``atlas-dev-gov-quality``.",
    )

    score: int = Field(description="The item's score.")

    id: str = Field(description="The document id, e.g. a ``doc-…`` id.")


# VE-02.
class GovQualityItem(BaseModel):
    """One governance check: a verdict item of a card."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result: GovQualityValue = Field(description="The human-readable verdict.")

    dataqualitytype: GovQualityValue = Field(
        description="The kind of check; ``attribute`` checks carry the legacy's lower-case name.",
    )

    usedattributes: GovQualityValue = Field(description="The entity attributes the check reads.")

    name: GovQualityValue = Field(description="The check's name, e.g. ``Attribute - <key>``.")

    compliant: GovQualityValue = Field(
        description="The verdict flag, a string ``'0'``/``'1'`` — as the legacy emits it.",
    )

    meta: GovQualityMeta = Field(alias="_meta", description="The producing engine's record.")

    id: GovQualityValue = Field(description="The item's document id, wrapped like every leaf.")


# VE-02.
class ValidationCard(BaseModel):
    """One governance card: the items of one aspect, with the card's verdict."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[GovQualityItem] = Field(default_factory=list, description="The checks of this card.")

    is_non_compliant: bool = Field(
        alias="isNonCompliant",
        description="Whether any item fails; the editor's badge.",
    )


# VE-02; DV-50; CL-40. The keys are the legacy's — ``dataEntity``,
# ``definition``, ``domainLead``, ``name`` — the aspects the editor's
# governance panel renders.
class ValidationResponse(BaseModel):
    """The ``POST /`` answer: the four governance cards."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid", frozen=True)

    data_entity: ValidationCard = Field(alias="dataEntity", description="The card for the data entity aspect.")

    definition: ValidationCard = Field(description="The card for the definition aspect.")

    domain_lead: ValidationCard = Field(alias="domainLead", description="The card for the domain lead aspect.")

    name: ValidationCard = Field(description="The card for the name aspect.")
