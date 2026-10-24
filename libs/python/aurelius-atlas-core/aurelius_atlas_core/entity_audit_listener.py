"""``EntityAuditListener``: an audit event for each entity and classification change (AUD-03 to AUD-05, CAU-01).

Atlas's ``EntityAuditListenerV2``: ``onEntitiesAdded``, ``onEntitiesUpdated``, ``onEntitiesDeleted``,
``onEntitiesPurged``, ``getAuditEventDetail``, and the classification methods.
"""

from collections.abc import Callable, Mapping, Sequence

from aurelius_atlas_model import codec
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntity

from aurelius_atlas_core.entity_audit_repository import EntityAuditRepository
from aurelius_atlas_core.entity_change_notifier import Propagations

MAX_DETAILS_BYTES = 1024 * 1024
"""``atlas.hbase.client.keyvalue.maxsize``'s default: details above it lose attributes (AUD-04)."""

DELETED_ENTITY = "Deleted entity"

ADDED = {True: "Added classification: ", False: "Added propagated classification: "}
DELETED = {True: "Deleted classification: ", False: "Deleted propagated classification: "}
UPDATED_OWN = "Updated classification: "
UPDATED_PROPAGATED = "Updated propagated classification: "
"""The details' prefixes of classification events, by whether the entity is the classification's own (CAU-01)."""

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

    async def on_classifications_added(
        self, guids: Sequence[str], classifications: Sequence[AtlasClassification], *, user: str | None
    ) -> None:
        """``onClassificationsAdded``: ``CLASSIFICATION_ADD`` on its entity, else ``PROPAGATED_`` (CAU-01)."""
        items = []
        for classification in classifications:
            text = _json(classification)
            for guid in guids:
                own = guid == classification.entity_guid
                action = (
                    EntityAuditActionV2.CLASSIFICATION_ADD if own else EntityAuditActionV2.PROPAGATED_CLASSIFICATION_ADD
                )
                items.append((guid, action, ADDED[own] + text))
        await self._put_events(items, user)

    async def on_classifications_updated(
        self, guids: Sequence[str], classifications: Sequence[AtlasClassification], context: Propagations
    ) -> None:
        """``onClassificationsUpdated``: on another entity an add or delete when the request propagated or removed it
        there, else an update (CAU-01, CAU-03).
        """  # noqa: D205 - one sentence
        items = []
        for guid in guids:
            for classification in classifications:
                text = _json(classification)
                if guid == classification.entity_guid:
                    items.append((guid, EntityAuditActionV2.CLASSIFICATION_UPDATE, UPDATED_OWN + text))
                elif _listed(context.added, guid, classification):
                    items.append((guid, EntityAuditActionV2.PROPAGATED_CLASSIFICATION_ADD, ADDED[False] + text))
                elif _listed(context.removed, guid, classification):
                    name = java_string(classification.type_name)
                    items.append((guid, EntityAuditActionV2.PROPAGATED_CLASSIFICATION_DELETE, DELETED[False] + name))
                else:
                    items.append(
                        (guid, EntityAuditActionV2.PROPAGATED_CLASSIFICATION_UPDATE, UPDATED_PROPAGATED + text)
                    )
        await self._put_events(items, context.user)

    async def on_classifications_deleted(
        self, guids: Sequence[str], classifications: Sequence[AtlasClassification], *, user: str | None
    ) -> None:
        """``onClassificationsDeleted``: ``CLASSIFICATION_DELETE`` on its entity, else ``PROPAGATED_`` (CAU-01)."""
        items = []
        for classification in classifications:
            name = java_string(classification.type_name)
            for guid in guids:
                own = guid == classification.entity_guid
                action = (
                    EntityAuditActionV2.CLASSIFICATION_DELETE
                    if own
                    else EntityAuditActionV2.PROPAGATED_CLASSIFICATION_DELETE
                )
                items.append((guid, action, DELETED[own] + name))
        await self._put_events(items, user)

    async def _put(
        self, items: Sequence[tuple[AtlasEntity, EntityAuditActionV2, str | None]], user: str | None
    ) -> None:
        """``putEventsV2`` of entity events, the details made from the entity unless given (AUD-03)."""
        await self._put_events(
            [
                (str(entity.guid), action, audit_detail(entity, action) if details is None else details)
                for entity, action, details in items
            ],
            user,
        )

    async def _put_events(self, items: Sequence[tuple[str, EntityAuditActionV2, str]], user: str | None) -> None:
        """``putEventsV2`` of one batch: each event keyed by its position in the batch (AUD-05)."""
        if not items:
            return
        events = []
        for index, (guid, action, details) in enumerate(items):
            timestamp = self._clock()
            events.append(
                EntityAuditEventV2(
                    entity_id=guid,
                    timestamp=timestamp,
                    user=user,
                    action=action,
                    details=details,
                    event_key=f"{guid}:{timestamp}:{index}:{self._clock()}",
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


def _json(value: AtlasEntity | AtlasClassification) -> str:
    return codec.dumps(value.to_json()).decode()


def _listed(
    propagations: Mapping[str, Sequence[AtlasClassification]], guid: str, classification: AtlasClassification
) -> bool:
    """``hasPropagatedEntry``: the entity has one of the classification's type and entity in the map."""
    return any(
        found.type_name == classification.type_name and found.entity_guid == classification.entity_guid
        for found in propagations.get(guid, [])
    )
