"""The view family's shapes: the card of a result and the view of one entity (AVS-01, AVS-04, AVS-07, ADR 064).

These are Aurelius-native models: the one shape family the webapp reads rich catalogue data in, answered by
the view family's doors (16.2, 16.3). A card holds what a result line, a chip and a badge need; a view is a
card plus one entity's own values, its related sections and its quality detail. ``aurelius_atlas_core``
derives both from a stored entity document (``view_derivation``, AVS-08, DD-581); the derived fields mirror
the App Search document of 14.2 under these names. The server, the Python client and the webapp's mirrored
Angular models treat this module as the one definition of the fields (AVS-07, DD-580).
"""

from typing import Any

from pydantic import Field

from aurelius_atlas_model.base import AtlasModel, Timestamp
from aurelius_atlas_model.instance.entity_status import EntityStatus


class CardBreadcrumb(AtlasModel):
    """One crumb of a card's trail: the entity named, by GUID, name and type, as its document names it (AVS-01)."""

    guid: str
    name: str | None = None
    type_name: str | None = None


class CardQuality(AtlasModel):
    """One quality dimension's roll-up on a card: its score, the scores counted, their total, and the rules (AVS-01).

    ``dimension`` names the dimension or ``overall``; ``rule_guids`` lists the rules behind a field's totals
    (LAS-12). The per-rule verdicts are not here: they live in their own index (ASG-03, DD-583).
    """

    dimension: str
    score: float = 0.0
    count: float = 0.0
    total: float = 0.0
    rule_guids: list[str] = Field(default_factory=list)


class RelationEntity(AtlasModel):
    """One related entity: its GUID and name, and its type and state where the reader read them (AVS-02, AVS-04)."""

    guid: str
    name: str | None = None
    type_name: str | None = None
    status: EntityStatus | None = None


class EntityRelation(AtlasModel):
    """The entities related under one attribute name: a stored pair or the entity's own end (AVS-02, AVS-04)."""

    attribute: str
    entities: list[RelationEntity] = Field(default_factory=list)


class EntityCard(AtlasModel):
    """One catalogue entity as a search result, a chip and a badge need it (AVS-01, ADR 064).

    The derived fields — ``breadcrumb``, ``relations``, ``quality``, ``governed``, ``stale`` — come from the
    entity's stored App Search document; an entity without one has them empty and ``governed`` absent (AVS-02).
    ``displayText`` is the name, or the qualified name when there is no name (AVS-03, DD-582). ``stale`` is the
    stored document's mark and ``updateTime`` the entity's: the shape's whole freshness claim (AVS-06, DD-583).
    """

    guid: str
    type_name: str
    super_type_names: list[str] = Field(default_factory=list)
    name: str | None = None
    qualified_name: str | None = None
    display_text: str = ""
    definition: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE
    create_time: Timestamp | None = None
    update_time: Timestamp | None = None
    created_by: str | None = None
    updated_by: str | None = None
    classification_names: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    breadcrumb: list[CardBreadcrumb] = Field(default_factory=list)
    relations: list[EntityRelation] = Field(default_factory=list)
    quality: list[CardQuality] = Field(default_factory=list)
    governed: bool | None = None
    stale: bool = False

    @classmethod
    def of(cls, view: EntityView) -> EntityCard:
        """The card of a view: its shared fields, its own values and sections left out (AVS-04, DD-581)."""
        return cls(**view.model_dump(include=set(cls.model_fields), by_alias=False))


class EntityView(EntityCard):
    """One entity as a screen needs it: a card plus its own values, sections and business metadata (AVS-04, ADR 064).

    ``attributes`` are the entity's own attribute values as the store holds them; ``sections`` merge the entity's
    own relationship ends with its document's stored pairs, each end listed once under its attribute (AVS-04).
    """

    attributes: dict[str, Any] = Field(default_factory=dict)
    business_metadata: dict[str, dict[str, Any]] | None = None
    sections: list[EntityRelation] = Field(default_factory=list)
