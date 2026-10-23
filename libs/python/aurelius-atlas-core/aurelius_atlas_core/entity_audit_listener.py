"""``EntityAuditListener``: an audit event for each entity a mutation changed (AUD-03 to AUD-05).

Atlas's ``EntityAuditListenerV2`` for entity changes (``onEntitiesAdded``, ``onEntitiesUpdated``,
``onEntitiesDeleted``, ``onEntitiesPurged``, ``getAuditEventDetail``); classification events follow in 3.5b.
"""

from collections.abc import Callable, Sequence

from aurelius_atlas_model import codec
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from aurelius_atlas_model.instance import AtlasEntity

from aurelius_atlas_core.entity_audit_repository import EntityAuditRepository

MAX_DETAILS_BYTES = 1024 * 1024
"""``atlas.hbase.client.keyvalue.maxsize``'s default: details above it lose attributes (AUD-04)."""

DELETED_ENTITY = "Deleted entity"

_PREFIXES = {
    EntityAuditActionV2.ENTITY_CREATE: "Created: ",
    EntityAuditActionV2.ENTITY_UPDATE: "Updated: ",
    EntityAuditActionV2.CUSTOM_ATTRIBUTE_UPDATE: "Updated custom attribute: ",
    EntityAuditActionV2.BUSINESS_ATTRIBUTE_UPDATE: "Updated business attribute: ",
    EntityAuditActionV2.ENTITY_DELETE: "Deleted: ",
    EntityAuditActionV2.ENTITY_PURGE: "Purged: ",
    EntityAuditActionV2.CLASSIFICATION_ADD: "Added classification: ",
    EntityAuditActionV2.CLASSIFICATION_DELETE: "Deleted classification: ",
    EntityAuditActionV2.CLASSIFICATION_UPDATE: "Updated classification: ",
    EntityAuditActionV2.ENTITY_IMPORT_CREATE: "Created by import: ",
    EntityAuditActionV2.ENTITY_IMPORT_UPDATE: "Updated by import: ",
    EntityAuditActionV2.ENTITY_IMPORT_DELETE: "Deleted by import: ",
    EntityAuditActionV2.TERM_ADD: "Added term: ",
    EntityAuditActionV2.TERM_DELETE: "Deleted term: ",
}
"""``getV2AuditPrefix``; ``Unknown: `` for the others."""


class EntityAuditListener:
    """Records audit events in ``repository``, timed by ``clock`` (epoch milliseconds)."""

    def __init__(self, repository: EntityAuditRepository, clock: Callable[[], int]) -> None:
        self._repository = repository
        self._clock = clock

    async def on_entities_added(self, entities: Sequence[AtlasEntity], *, user: str | None) -> None:
        """``onEntitiesAdded``: ``ENTITY_CREATE`` with the entity (AUD-03)."""
        await self._put([(entity, EntityAuditActionV2.ENTITY_CREATE, None) for entity in entities], user)

    async def on_entities_updated(self, entities: Sequence[AtlasEntity], *, user: str | None) -> None:
        """``onEntitiesUpdated``: ``ENTITY_UPDATE``, or ``ENTITY_CREATE`` for a shell entity (AUD-03)."""
        await self._put([(entity, _update_action(entity), None) for entity in entities], user)

    async def on_entities_deleted(self, entities: Sequence[AtlasEntity], *, user: str | None) -> None:
        """``onEntitiesDeleted``: ``ENTITY_DELETE``, ``Deleted entity`` (AUD-03)."""
        await self._put([(entity, EntityAuditActionV2.ENTITY_DELETE, DELETED_ENTITY) for entity in entities], user)

    async def on_entities_purged(self, entities: Sequence[AtlasEntity], *, user: str | None) -> None:
        """``onEntitiesPurged``: ``ENTITY_PURGE`` with the entity made from its header (AUD-03)."""
        await self._put([(entity, EntityAuditActionV2.ENTITY_PURGE, None) for entity in entities], user)

    async def _put(
        self, items: Sequence[tuple[AtlasEntity, EntityAuditActionV2, str | None]], user: str | None
    ) -> None:
        """``putEventsV2`` of one batch: each event keyed by its position in the batch (AUD-05)."""
        events = []
        for index, (entity, action, details) in enumerate(items):
            timestamp = self._clock()
            events.append(
                EntityAuditEventV2(
                    entity_id=entity.guid,
                    timestamp=timestamp,
                    user=user,
                    action=action,
                    details=audit_detail(entity, action) if details is None else details,
                    event_key=f"{entity.guid}:{timestamp}:{index}:{self._clock()}",
                    entity=entity,
                )
            )
        await self._repository.put_events(events)


def _update_action(entity: AtlasEntity) -> EntityAuditActionV2:
    """``ENTITY_CREATE`` for an incomplete entity whose create and update times are the same (``isShellEntity``)."""
    shell = (
        bool(entity.is_incomplete)
        and entity.create_time is not None
        and entity.update_time is not None
        and entity.create_time == entity.update_time
    )
    return EntityAuditActionV2.ENTITY_CREATE if shell else EntityAuditActionV2.ENTITY_UPDATE


def audit_detail(entity: AtlasEntity, action: EntityAuditActionV2) -> str:
    """``getAuditEventDetail``: the action's prefix and the entity's JSON, cut down when too long (AUD-04)."""
    prefix = _PREFIXES.get(action, "Unknown: ")
    detail = prefix + _json(entity)
    if len(detail.encode()) <= MAX_DETAILS_BYTES:
        return detail
    detail = prefix + _json(entity.model_copy(update={"attributes": None, "relationship_attributes": None}))
    if len(detail.encode()) <= MAX_DETAILS_BYTES:
        return detail
    shallow = AtlasEntity(
        guid=entity.guid,
        type_name=entity.type_name,
        create_time=entity.create_time,
        update_time=entity.update_time,
        created_by=entity.created_by,
        updated_by=entity.updated_by,
        status=entity.status,
        version=entity.version,
    )
    return prefix + _json(shallow)


def _json(entity: AtlasEntity) -> str:
    return codec.dumps(entity.to_json()).decode()
