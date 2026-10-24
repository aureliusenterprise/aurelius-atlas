"""``AtlasEntityHeader``: an entity's identity and summary, as lists and mutation responses show it (ENT-14)."""

from typing import Self

from aurelius_atlas_model.base import OptionalNameSet
from aurelius_atlas_model.instance.classification import AtlasClassification
from aurelius_atlas_model.instance.entity import AtlasEntity
from aurelius_atlas_model.instance.entity_status import EntityStatus
from aurelius_atlas_model.instance.struct import AtlasStruct
from aurelius_atlas_model.instance.term_assignment_header import AtlasTermAssignmentHeader


class AtlasEntityHeader(AtlasStruct):
    """An entity's type, GUID, status, display text, classifications, meanings and labels."""

    guid: str | None = None
    status: EntityStatus | None = EntityStatus.ACTIVE
    display_text: str | None = None
    classification_names: list[str] | None = None
    classifications: list[AtlasClassification] | None = None
    meaning_names: list[str] | None = None
    meanings: list[AtlasTermAssignmentHeader] | None = None
    is_incomplete: bool | None = False
    labels: OptionalNameSet = None

    @classmethod
    def of(cls, entity: AtlasEntity) -> Self:
        """The header of ``entity`` (``AtlasEntityHeader(AtlasEntity)``); its meanings are not carried over."""
        header = cls(
            type_name=entity.type_name,
            attributes=entity.attributes,
            guid=entity.guid,
            status=entity.status,
            classifications=entity.classifications,
            is_incomplete=entity.is_incomplete,
        )
        if entity.classifications:
            header.classification_names = [str(classification.type_name) for classification in entity.classifications]
        if entity.labels:
            header.labels = entity.labels
        return header
