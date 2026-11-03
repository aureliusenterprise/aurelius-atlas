"""``AtlasAuditEntry`` and ``AuditSearchParameters``: the admin audits and their search (ADA-01, ADA-04).

Ported from Apache Atlas 2.4.0 ``org.apache.atlas.model.audit.AtlasAuditEntry`` and ``AuditSearchParameters``.
"""

from enum import StrEnum

from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.base import AtlasModel, JavaInt
from aurelius_atlas_model.discovery import FilterCriteria, SortOrder


class AuditOperation(StrEnum):
    """``AuditOperation``: what an admin audit records."""

    PURGE = "PURGE"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    IMPORT_DELETE_REPL = "IMPORT_DELETE_REPL"
    TYPE_DEF_CREATE = "TYPE_DEF_CREATE"
    TYPE_DEF_UPDATE = "TYPE_DEF_UPDATE"
    TYPE_DEF_DELETE = "TYPE_DEF_DELETE"
    SERVER_START = "SERVER_START"
    SERVER_STATE_ACTIVE = "SERVER_STATE_ACTIVE"

    def to_entity_audit_action_v2(self) -> EntityAuditActionV2:
        """``toEntityAuditActionV2``: ``ENTITY_PURGE`` for a purge, else the entity action of the same name.

        Raises:
            ValueError: ``Invalid operation for Entity Audit Event V2: <operation>`` for any other (ADA-05).
        """
        if self is AuditOperation.PURGE:
            return EntityAuditActionV2.ENTITY_PURGE
        try:
            return EntityAuditActionV2.from_string(self.value)
        except ValueError as error:
            message = f"Invalid operation for Entity Audit Event V2: {self.value}"
            raise ValueError(message) from error


class AtlasAuditEntry(AtlasModel):
    """``AtlasAuditEntry``: one admin operation, its user, client, times, parameters and result (ADA-01)."""

    guid: str = "-1"
    user_name: str | None = None
    operation: AuditOperation | None = None
    params: str | None = None
    start_time: int | None = None
    end_time: int | None = None
    client_id: str | None = None
    result: str | None = None
    result_count: int = 0


class AuditSearchParameters(AtlasModel):
    """``AuditSearchParameters``: the filters, page and order of an admin audit search (ADA-04)."""

    audit_filters: FilterCriteria | None = None
    limit: JavaInt = 0
    offset: JavaInt = 0
    sort_by: str | None = None
    sort_order: SortOrder | None = None
