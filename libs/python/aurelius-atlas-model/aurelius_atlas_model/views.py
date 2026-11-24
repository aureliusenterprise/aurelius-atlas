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
    (LAS-12). The refused per-rule verdicts ride the card itself, in ``verdicts`` (AVS-11, DD-838).
    """

    dimension: str
    score: float = 0.0
    count: float = 0.0
    total: float = 0.0
    rule_guids: list[str] = Field(default_factory=list)


class CardVerdict(AtlasModel):
    """One non-compliant governance verdict on a card: the rule it refuses, named, and the message (AVS-11, DD-838).

    ``rule`` is the rule's GUID and ``name`` its name; ``message`` is the verdict's ``noncompliant_message``
    (ASG-03). These are the rows the card's governance mark counts and lists (VCF-19); the compliant verdicts
    stay in their index (ASG-03, DD-839).
    """

    rule: str
    name: str
    message: str


class RuleVerdict(AtlasModel):
    """One stored governance verdict of a rule, as the verdicts door answers it (AVS-12, DD-846).

    ``entity`` is the judged entity's GUID; ``compliant`` is the document's ``"1"`` or ``"0"`` as a boolean,
    ``null`` for a document holding neither (ASG-03). ``name`` and ``message`` are the rule name and the
    verdict's ``noncompliant_message`` the document copied when it was written — the rows the rule page's
    card lists and chart draw (VDR-14).
    """

    entity: str
    compliant: bool | None
    name: str = ""
    message: str = ""


class RuleScore(AtlasModel):
    """One quality result of an entity, as the read door joins it (AVS-13, DD-863).

    ``rule`` is the rule GUID the score's result names, ``name`` its name, ``dimension`` its dimension word,
    ``score`` the ``dqscore`` of ASQ-02's stored result — the four fields the legacy box's ``result_fields``
    asked for. A field's rules scored on it answer one row each, in score GUID order (ASQ-09, VDR-16); these
    are the rows the field page's rule cards print (DET-65).
    """

    rule: str
    name: str = ""
    dimension: str = ""
    score: float = 0.0


class RelationEntity(AtlasModel):
    """One related entity: its GUID and name, and its type and state where the reader read them (AVS-02, AVS-04).

    ``breadcrumb`` holds the trail its document stored, top down, so a propagation source's row can show where
    the source sits, as a card's own trail does (VDR-12, DD-836). Only a related entity read with a document
    that has parents carries it: a section's end or a source with no trail answers none, so no answer gains a
    key it did not hold before (AVS-05).
    """

    guid: str
    name: str | None = None
    type_name: str | None = None
    status: EntityStatus | None = None
    breadcrumb: list[CardBreadcrumb] | None = None


class EntityRelation(AtlasModel):
    """The entities related under one attribute name: a stored pair or the entity's own end (AVS-02, AVS-04)."""

    attribute: str
    entities: list[RelationEntity] = Field(default_factory=list)


class ClassificationSource(AtlasModel):
    """One classification the entity carries by propagation, and the entities it came from (AVS-04).

    ``typeName`` names the classification; ``entities`` holds the entities the instance is attached to, each with
    the name the store answered. A source the store no longer has answers an empty list: the tag stays the
    entity's to show, only its origin is unknown.
    """

    type_name: str
    entities: list[RelationEntity] = Field(default_factory=list)


class EntityCard(AtlasModel):
    """One catalogue entity as a search result, a chip and a badge need it (AVS-01, ADR 064).

    The derived fields — ``breadcrumb``, ``relations``, ``quality``, ``governed``, ``stale`` — come from the
    entity's stored App Search document; an entity without one has them empty and ``governed`` absent (AVS-02).
    ``displayText`` is the name, or the qualified name when there is no name (AVS-03, DD-582). ``typeAlias``
    is the entity's ``typeAlias`` attribute as a non-empty string, or none (AVS-01, MMS-09): the type name a
    badge shows in place of ``typeName``. ``definition`` is the description text: the entity's ``description``
    attribute (DD-614, narrowed by 18.8/SPA-05 when the m4i dictionary retired its own ``definition``).
    ``stale`` is the stored document's mark and
    ``updateTime`` the entity's: the shape's whole freshness claim (AVS-06, DD-583).
    ``propagatedClassifications`` names the classifications propagation brought with the entities each came
    from: every door that reads them fills it, and a door that answers none leaves it empty (VDR-12, DD-836).
    ``verdicts`` holds the refused governance verdicts the door joined from the verdicts index, in rule-name
    order and capped (AVS-11, VDR-13, DD-838); ``governed`` stays the store's judged mark (ASG-06).
    """

    guid: str
    type_name: str
    super_type_names: list[str] = Field(default_factory=list)
    name: str | None = None
    qualified_name: str | None = None
    display_text: str = ""
    type_alias: str | None = None
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
    verdicts: list[CardVerdict] = Field(default_factory=list)
    """The refused governance verdicts the door joined (AVS-11, VDR-13); empty for an entity with none."""
    governed: bool | None = None
    stale: bool = False
    has_parent: bool = False
    """Whether the entity holds any parent, from its document (RPS-06, DD-758); false without a document."""
    propagated_classifications: list[ClassificationSource] = Field(default_factory=list)

    @classmethod
    def of(cls, view: EntityView) -> EntityCard:
        """The card of a view: its shared fields, its own values and sections left out (AVS-04, DD-581)."""
        return cls(**view.model_dump(include=set(cls.model_fields), by_alias=False))


class EntityView(EntityCard):
    """One entity as a screen needs it: a card plus its own values, sections and business metadata (AVS-04, ADR 064).

    ``attributes`` are the entity's own attribute values as the store holds them; ``sections`` merge the entity's
    own relationship ends with its document's stored pairs, each end listed once under its attribute (AVS-04).
    ``ruleScores`` holds the quality results that reach the entity — the field page's rule scores — which only
    the read door's join fills, for an ``m4i_field`` (AVS-13, VDR-16). Like ``sections`` it is the view's own:
    a card never carries it (DD-581's pair).
    """

    attributes: dict[str, Any] = Field(default_factory=dict)
    business_metadata: dict[str, dict[str, Any]] | None = None
    sections: list[EntityRelation] = Field(default_factory=list)
    rule_scores: list[RuleScore] = Field(default_factory=list)
