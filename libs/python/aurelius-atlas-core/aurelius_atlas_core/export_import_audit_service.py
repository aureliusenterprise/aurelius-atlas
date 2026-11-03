"""``ExportImportAuditService`` and ``ExportImportAuditEntryDTO``: the audit trail of exports and imports.

Each that had entities is an ``__ExportImportAuditEntry``, found by basic search (REP-02, REP-05).
"""

from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.discovery import Condition, FilterCriteria, Operator, SearchParameters
from aurelius_atlas_model.impexp import OPERATION_IMPORT, AtlasImportResult, ExportImportAuditEntry
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo

from aurelius_atlas_core.authorization import ALLOW_ALL, SCRUBBED_GUID, Authorizer
from aurelius_atlas_core.data_access import DataAccess
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_audit_listener import MAX_DETAILS_BYTES
from aurelius_atlas_core.entity_store import EntityStore

AUDIT_TYPE = "__ExportImportAuditEntry"
ATTRIBUTES = {
    "userName": "user_name",
    "operation": "operation",
    "operationParams": "operation_params",
    "operationStartTime": "start_time",
    "operationEndTime": "end_time",
    "sourceServerName": "source_server_name",
    "targetServerName": "target_server_name",
    "resultSummary": "result_summary",
}
"""``ExportImportAuditEntryDTO``'s attributes, and the entry's fields they hold."""


class ExportImportAuditEntryDTO:
    """``ExportImportAuditEntryDTO``: an entry as its entity."""

    type_name = AUDIT_TYPE

    def from_entity(self, found: AtlasEntityWithExtInfo) -> ExportImportAuditEntry:
        """``from``: the entry of the entity's attributes."""
        entity = found.entity or AtlasEntity()
        return entry_of(str(entity.guid), entity.attributes or {})

    def to_entities(self, obj: ExportImportAuditEntry) -> list[AtlasEntity]:
        """``toEntity``: the entry's entity."""
        attributes = {name: getattr(obj, field) for name, field in ATTRIBUTES.items()}
        return [AtlasEntity(type_name=AUDIT_TYPE, guid=obj.guid, attributes=attributes)]

    def unique_attributes(self, obj: ExportImportAuditEntry) -> dict[str, Any]:  # noqa: ARG002 - the protocol's
        """None: an entry is found by its GUID."""
        return {}


def entry_of(guid: str, attributes: dict[str, Any]) -> ExportImportAuditEntry:
    """``ExportImportAuditEntryDTO.from``: the entry of the GUID and attributes."""
    values = {field: attributes.get(name) for name, field in ATTRIBUTES.items()}
    return ExportImportAuditEntry.model_validate(
        {**values, "guid": guid, "start_time": values["start_time"] or 0, "end_time": values["end_time"] or 0}
    )


class ExportImportAuditService:
    """``ExportImportAuditService`` over the entities of ``store``, written as ``user``, read and written as
    ``authorizer`` allows (DD-307).
    """  # noqa: D205 - one sentence

    def __init__(self, store: EntityStore, *, user: str | None = None, authorizer: Authorizer = ALLOW_ALL) -> None:
        self._store = store
        self._authorizer = authorizer
        self._data_access = DataAccess(
            store, {ExportImportAuditEntry: ExportImportAuditEntryDTO()}, user=user, authorizer=authorizer
        )

    async def add(  # noqa: PLR0913, PLR0917 - Atlas's arguments
        self,
        user_name: str | None,
        source: str | None,
        target: str | None,
        operation: str,
        result: str,
        start: int,
        end: int,
        *,
        has_data: bool,
    ) -> None:
        """``add``: an entry of the operation, unless it had no entities; an import's summary trimmed of its entity
        list when too large (REP-02).
        """  # noqa: D205 - one sentence
        if not has_data:
            return
        entry = ExportImportAuditEntry(
            user_name=user_name,
            source_server_name=source,
            target_server_name=target,
            operation=operation,
            result_summary=result,
            start_time=start,
            end_time=end,
        )
        if operation == OPERATION_IMPORT and len(codec.dumps(entry.to_json())) > MAX_DETAILS_BYTES:
            imported = AtlasImportResult.model_validate_json(result)
            if imported.processed_entities:
                imported.processed_entities = []
                entry.result_summary = codec.dumps(imported.to_json()).decode()
        await self._data_access.save(entry)

    async def get(  # noqa: PLR0913, PLR0917 - the query parameters
        self,
        user_name: str | None,
        operation: str | None,
        cluster: str | None,
        start_time: str | None,
        end_time: str | None,
        limit: int,
        offset: int,
    ) -> list[ExportImportAuditEntry]:
        """``get``: the entries each given value equals, the server either end; ``limit`` and ``offset`` as basic
        search takes them; those the authorizer scrubbed left out (REP-05, DV-130).
        """  # noqa: D205 - one sentence
        criteria: list[FilterCriteria] = [
            _equals(name, value)
            for name, value in (
                ("userName", user_name),
                ("operation", operation),
                ("operationStartTime", start_time),
                ("operationEndTime", end_time),
            )
            if value
        ]
        if cluster:
            servers = [_equals("sourceServerName", cluster), _equals("targetServerName", cluster)]
            criteria.append(FilterCriteria(condition=Condition.OR, criterion=servers))
        parameters = SearchParameters(
            type_name=AUDIT_TYPE,
            entity_filters=FilterCriteria(condition=Condition.AND, criterion=criteria),
            limit=limit,
            offset=offset,
            attributes=list(ATTRIBUTES),
        )
        result = await EntityDiscoveryService(self._store, authorizer=self._authorizer).search_with_parameters(
            parameters
        )
        readable = [header for header in result.entities or [] if header.guid != SCRUBBED_GUID]
        return [entry_of(str(header.guid), header.attributes or {}) for header in readable]


def _equals(name: str, value: str) -> FilterCriteria:
    return FilterCriteria(attribute_name=name, operator=Operator.EQ, attribute_value=value)
