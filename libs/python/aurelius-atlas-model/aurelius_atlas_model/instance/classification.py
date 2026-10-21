"""``AtlasClassification``: a classification of an entity, with its propagation and validity (ENT-13)."""

from aurelius_atlas_model.instance.entity_status import EntityStatus
from aurelius_atlas_model.instance.struct import AtlasStruct
from aurelius_atlas_model.instance.time_boundary import TimeBoundary


class AtlasClassification(AtlasStruct):
    """An instance of a classification type attached to an entity.

    ``propagate`` is written once: Java's ``getPropagate`` and ``isPropagate`` name the same property.
    """

    entity_guid: str | None = None
    entity_status: EntityStatus | None = EntityStatus.ACTIVE
    propagate: bool | None = None
    validity_periods: list[TimeBoundary | None] | None = None
    remove_propagations_on_entity_delete: bool | None = None

    def add_validity_period(self, validity_period: TimeBoundary) -> None:
        """Append a validity period, creating the list (``addValityPeriod``)."""
        self.validity_periods = [*(self.validity_periods or []), validity_period]
