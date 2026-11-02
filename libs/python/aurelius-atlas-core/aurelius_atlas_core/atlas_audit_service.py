"""``AtlasAuditService`` and ``AtlasAuditEntryDTO``: the admin audits, as ``__AtlasAuditEntry`` entities, and their
search and details (ADA-01 to ADA-05).
"""  # noqa: D205 - one sentence

import socket
import time
from typing import Any

from aurelius_atlas_model.atlas_audit import AtlasAuditEntry, AuditOperation, AuditSearchParameters
from aurelius_atlas_model.discovery import FilterCriteria, SearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityHeader, AtlasEntityWithExtInfo

from aurelius_atlas_core.authorization import ALLOW_ALL, SCRUBBED_GUID, AtlasPrivilege, Authorizer
from aurelius_atlas_core.data_access import DataAccess
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_audit_repository import EntityAuditRepository
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.request_context import current, current_user

AUDIT_ENTRY_TYPE = "__AtlasAuditEntry"
ATTRIBUTES = {
    "userName": "user_name",
    "operation": "operation",
    "params": "params",
    "startTime": "start_time",
    "endTime": "end_time",
    "clientId": "client_id",
    "result": "result",
    "resultCount": "result_count",
}
"""``AtlasAuditEntryDTO``'s attributes, and the entry's fields they hold."""
AUDIT_ENTRY = "Atlas Audit Entry"
"""What ``UNKNOWN_ATTRIBUTE`` names as the type of an attribute a search names but an entry lacks."""
NO_PARAMETERS = "Audit Search Parameters not specified"


class AtlasAuditEntryDTO:
    """``AtlasAuditEntryDTO``: an entry as its entity."""

    type_name = AUDIT_ENTRY_TYPE

    def from_entity(self, found: AtlasEntityWithExtInfo) -> AtlasAuditEntry:
        """``from``: the entry of the entity's attributes."""
        entity = found.entity or AtlasEntity()
        return entry_of(str(entity.guid), entity.attributes or {})

    def to_entities(self, obj: AtlasAuditEntry) -> list[AtlasEntity]:
        """``toEntity``: the entry's entity."""
        attributes = {name: getattr(obj, field) for name, field in ATTRIBUTES.items()}
        return [AtlasEntity(type_name=AUDIT_ENTRY_TYPE, guid=obj.guid, attributes=attributes)]

    def unique_attributes(self, obj: AtlasAuditEntry) -> dict[str, Any]:  # noqa: ARG002 - the protocol's
        """None: an entry is found by its GUID."""
        return {}


def entry_of(guid: str, attributes: dict[str, Any]) -> AtlasAuditEntry:
    """``AtlasAuditEntryDTO.from``: the entry of the GUID and attributes."""
    values = {field: attributes.get(name) for name, field in ATTRIBUTES.items()}
    return AtlasAuditEntry.model_validate({**values, "guid": guid, "result_count": values["result_count"] or 0})


class AtlasAuditService:
    """``AtlasAuditService`` over ``store``: written unchecked, read as ``authorizer`` allows (DD-308)."""

    def __init__(self, store: EntityStore, *, authorizer: Authorizer = ALLOW_ALL) -> None:
        self._store = store
        self._authorizer = authorizer

    async def add(  # noqa: PLR0913 - Atlas's arguments
        self,
        operation: AuditOperation,
        params: str | None,
        result: str | None,
        result_count: int,
        *,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> None:
        """``add``: an entry of the request's user (``getCurrentUser``) and client, from the request's start (or
        ``start_time``) to now (or ``end_time``); a request with no client is this host's ``<name>:<address>``
        (ADA-02).
        A catalogue without the base model, which defines the entries' type, keeps none (DD-308).
        """  # noqa: D205 - one sentence
        if self._store.registry.entity_type(AUDIT_ENTRY_TYPE) is None:
            return
        context, user = current(), current_user()
        entry = AtlasAuditEntry(
            user_name=user,
            operation=operation,
            client_id=context.client_ip_address or _this_host(),
            start_time=context.request_time if start_time is None else start_time,
            end_time=int(time.time() * 1000) if end_time is None else end_time,
            params=params,
            result=result,
            result_count=result_count,
        )
        await DataAccess(self._store, {AtlasAuditEntry: AtlasAuditEntryDTO()}, user=user).save(entry)

    async def get(self, parameters: AuditSearchParameters | None) -> list[AtlasAuditEntry]:
        """``get``: the entries the filters find, a page in the order asked; those scrubbed left out (ADA-04).

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` for no parameters; ``UNKNOWN_ATTRIBUTE`` for a filter or order on an
                attribute an entry lacks.
        """
        if parameters is None:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_PARAMETERS)
        if parameters.sort_by and parameters.sort_by not in ATTRIBUTES:
            raise AtlasError(AtlasErrorCode.UNKNOWN_ATTRIBUTE, parameters.sort_by, AUDIT_ENTRY)
        search = SearchParameters(
            type_name=AUDIT_ENTRY_TYPE,
            entity_filters=_non_empty_filter(parameters.audit_filters),
            limit=parameters.limit,
            offset=parameters.offset,
            sort_by=parameters.sort_by,
            sort_order=parameters.sort_order,
            attributes=list(ATTRIBUTES),
        )
        result = await EntityDiscoveryService(self._store, authorizer=self._authorizer).search_with_parameters(search)
        readable = [header for header in result.entities or [] if header.guid != SCRUBBED_GUID]
        return [entry_of(str(header.guid), header.attributes or {}) for header in readable]

    async def details(
        self, guid: str, repository: EntityAuditRepository, limit: int, offset: int
    ) -> list[AtlasEntityHeader]:
        """``AdminResource.getAuditDetails``: for the page of the entry's result GUIDs, each one's latest entity
        audit of the entry's action, as its entity header (ADA-05).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND``; ``UNAUTHORIZED_ACCESS``; ``INTERNAL_ERROR`` for an operation
                that is no entity action (only a purge is one).
        """  # noqa: D205 - one sentence
        found = (await EntityRetriever(self._store).entity_with_ext_info(guid)).entity
        self._authorizer.verify_access(AtlasPrivilege.ENTITY_READ, "read entity: guid=", guid)
        entry = None if found is None else entry_of(str(found.guid), found.attributes or {})
        if entry is None or entry.operation is None or not entry.result:
            return []
        guids = entry.result.split(",")
        try:
            action = entry.operation.to_entity_audit_action_v2()
        except ValueError as error:
            raise AtlasError.of_message(AtlasErrorCode.INTERNAL_ERROR, str(error)) from error
        headers: list[AtlasEntityHeader] = []
        for entity_guid in guids[offset : offset + limit] if 0 <= offset <= len(guids) else []:
            for event in await repository.list_events(entity_guid, action, None, 1):
                header = event.entity_header()
                if header is not None:
                    headers.append(header)
        return headers


def _non_empty_filter(criteria: FilterCriteria | None) -> FilterCriteria:
    """``getNonEmptyFilter``: the top-level criteria that have a value, under the given condition.

    Raises:
        AtlasError: ``UNKNOWN_ATTRIBUTE`` for a criterion on an attribute an entry lacks.
    """
    kept: list[FilterCriteria] = []
    for each in [] if criteria is None else criteria.criterion or []:
        if each.attribute_name and each.attribute_name not in ATTRIBUTES:
            raise AtlasError(AtlasErrorCode.UNKNOWN_ATTRIBUTE, each.attribute_name, AUDIT_ENTRY)
        if each.attribute_value:
            kept.append(
                FilterCriteria(
                    attribute_name=each.attribute_name, operator=each.operator, attribute_value=each.attribute_value
                )
            )
    return FilterCriteria(condition=None if criteria is None else criteria.condition, criterion=kept)


def _this_host() -> str:
    """``InetAddress.getLocalHost``: ``<host name>:<address>``, or ``unknown``."""
    try:
        name = socket.gethostname()
        return f"{name}:{socket.gethostbyname(name)}"
    except OSError:
        return "unknown"
