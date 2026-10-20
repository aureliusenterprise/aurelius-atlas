"""``EntityMutationResponse``: what an entity write did, by operation (ENT-17)."""

from pydantic import computed_field

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance.entity_header import AtlasEntityHeader
from aurelius_atlas_model.instance.entity_operation import EntityOperation


class EntityMutationResponse(AtlasModel):
    """The headers of the created, updated, deleted and purged entities, and the GUIDs given to new ones."""

    mutated_entities: dict[EntityOperation, list[AtlasEntityHeader]] | None = None
    guid_assignments: dict[str, str] | None = None

    @computed_field
    @property
    def partial_updated_entities(self) -> list[AtlasEntityHeader] | None:
        """The partially updated entities, also written as ``partialUpdatedEntities`` (ENT-17).

        Java's ``getPartialUpdatedEntities`` lacks the ``@JsonIgnore`` its other lookups have.
        """
        return self.get_entities_by_operation(EntityOperation.PARTIAL_UPDATE)

    def get_entities_by_operation(self, operation: EntityOperation) -> list[AtlasEntityHeader] | None:
        """The headers of the entities ``operation`` was applied to, or None."""
        return None if self.mutated_entities is None else self.mutated_entities.get(operation)

    def get_created_entities(self) -> list[AtlasEntityHeader] | None:
        """The created entities, or None."""
        return self.get_entities_by_operation(EntityOperation.CREATE)

    def get_updated_entities(self) -> list[AtlasEntityHeader] | None:
        """The updated entities, or None."""
        return self.get_entities_by_operation(EntityOperation.UPDATE)

    def get_deleted_entities(self) -> list[AtlasEntityHeader] | None:
        """The deleted entities, or None."""
        return self.get_entities_by_operation(EntityOperation.DELETE)

    def get_purged_entities(self) -> list[AtlasEntityHeader] | None:
        """The purged entities, or None."""
        return self.get_entities_by_operation(EntityOperation.PURGE)

    def get_purged_entities_ids(self) -> str | None:
        """The GUIDs of the purged entities joined by commas, or None when there are none."""
        purged = self.get_purged_entities()
        return ",".join(str(header.guid) for header in purged) if purged else None

    def get_first_entity_by_operation(self, operation: EntityOperation) -> AtlasEntityHeader | None:
        """The first entity ``operation`` was applied to (``getFirstEntityCreated``, …), or None."""
        headers = self.get_entities_by_operation(operation)
        return headers[0] if headers else None

    def get_first_entity_by_type_name(self, operation: EntityOperation, type_name: str) -> AtlasEntityHeader | None:
        """The first entity of ``type_name`` ``operation`` was applied to (``getFirstCreatedEntityByTypeName``, …)."""
        return next(iter(self.get_entities_by_type_name(operation, type_name)), None)

    def get_entities_by_type_name(self, operation: EntityOperation, type_name: str) -> list[AtlasEntityHeader]:
        """The entities of ``type_name`` that ``operation`` was applied to (``getCreatedEntitiesByTypeName``, …)."""
        return [header for header in self.get_entities_by_operation(operation) or [] if header.type_name == type_name]

    def get_entity_by_type_name_and_attribute(
        self, operation: EntityOperation, type_name: str, name: str, value: str | None
    ) -> AtlasEntityHeader | None:
        """The first entity of ``type_name`` whose attribute ``name`` is ``value``.

        ``getCreatedEntityByTypeNameAndAttribute`` and ``getUpdatedEntityByTypeNameAndAttribute``.
        """
        if value is None:
            return None
        return next(
            (
                header
                for header in self.get_entities_by_type_name(operation, type_name)
                if header.get_attribute(name) == value
            ),
            None,
        )

    def add_entity(self, operation: EntityOperation, header: AtlasEntityHeader) -> None:
        """Record ``operation`` on an entity, once per GUID; an update of an entity created here counts as created."""
        if operation in (EntityOperation.UPDATE, EntityOperation.PARTIAL_UPDATE) and _has_guid(
            self.get_created_entities(), header.guid
        ):
            operation = EntityOperation.CREATE
        if self.mutated_entities is None:
            self.mutated_entities = {}
        headers = self.mutated_entities.setdefault(operation, [])
        if not _has_guid(headers, header.guid):
            headers.append(header)


def _has_guid(headers: list[AtlasEntityHeader] | None, guid: str | None) -> bool:
    return guid is not None and any(header.guid == guid for header in headers or [])
