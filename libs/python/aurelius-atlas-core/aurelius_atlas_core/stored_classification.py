"""``StoredClassification``: a classification instance as stored, what Atlas keeps on its vertex (CLS-02, DD-070)."""

from typing import Any

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance import AtlasClassification, EntityStatus, TimeBoundary
from pydantic import Field


class StoredClassification(AtlasModel):
    """One document of the classification index: its type, the entity it is attached to, and its values.

    Attribute values are stored by attribute name (DD-049); ``write_id`` names the write that last wrote it (DD-046).
    A flag not stored reads as Atlas's vertex reads it: ``true``.
    """

    guid: str
    type_name: str
    super_type_names: list[str] = Field(default_factory=list)
    entity_guid: str | None = None
    entity_status: EntityStatus | None = None
    propagate: bool | None = None
    remove_propagations_on_entity_delete: bool | None = None
    validity_periods: list[TimeBoundary | None] | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    write_id: str | None = None

    def to_classification(self) -> AtlasClassification:
        """``toAtlasClassification``: the system fields; ``EntityRetriever`` reads the attribute values."""
        return AtlasClassification(
            type_name=self.type_name,
            entity_guid=self.entity_guid,
            entity_status=self.entity_status,
            propagate=True if self.propagate is None else self.propagate,
            remove_propagations_on_entity_delete=(
                True if self.remove_propagations_on_entity_delete is None else self.remove_propagations_on_entity_delete
            ),
            validity_periods=self.validity_periods,
        )
