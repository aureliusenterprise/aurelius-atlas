"""``AuditsWriter``: an export's or import's audit entry, and its replication (REP-02 to REP-04).

The replication is recorded on the server and on the entities that went.
"""

from aurelius_atlas_model import codec
from aurelius_atlas_model.impexp import (
    OPERATION_EXPORT,
    OPERATION_IMPORT,
    OPTION_KEY_REPLICATED_FROM,
    OPTION_KEY_REPLICATED_TO,
    AtlasExportResult,
    AtlasImportResult,
    OperationStatus,
    replicated,
    skip_update_replication_attr,
)

from aurelius_atlas_core.atlas_server_service import AtlasServerService
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.export_import_audit_service import ExportImportAuditService

DC_SERVER_NAME_SEPARATOR = "$"
REPLICATED_TO = "replicatedTo"
REPLICATED_FROM = "replicatedFrom"


class AuditsWriter:
    """``AuditsWriter`` into ``store`` as ``user``, unchecked (DD-307); ``cluster_name`` is this catalogue's server."""

    def __init__(self, store: EntityStore, *, cluster_name: str, user: str | None = None) -> None:
        self._store = store
        self._cluster = cluster_name
        self._servers = AtlasServerService(store, user=user)
        self._audits = ExportImportAuditService(store, user=user)

    async def write_export(
        self, user_name: str | None, result: AtlasExportResult, start: int, end: int, guids: list[str]
    ) -> None:
        """``ExportAudits.add``: this server saved, the entry written, then the exported entities marked
        ``replicatedTo`` the target when the request replicates (REP-02 to REP-04).
        """  # noqa: D205 - one sentence
        options = result.request.options if result.request is not None else {}
        await self._servers.get_create_atlas_server(self._cluster, self._cluster)
        full_name = replicated(options, OPTION_KEY_REPLICATED_TO)
        target = server_name_of(full_name) or None
        summary = codec.dumps(result.to_json()).decode()
        await self._audits.add(
            user_name, self._cluster, target, OPERATION_EXPORT, summary, start, end, has_data=bool(guids)
        )
        if result.operation_status is OperationStatus.FAIL:
            return
        replicating = OPTION_KEY_REPLICATED_TO in options and not skip_update_replication_attr(options)
        await self._replication(
            replicating=replicating,
            name=target or "",
            full_name=full_name,
            guids=guids,
            attribute=REPLICATED_TO,
            marker=result.change_marker,
        )

    async def write_import(
        self, user_name: str | None, result: AtlasImportResult, start: int, end: int, guids: list[str]
    ) -> None:
        """``ImportAudits.add``: this server saved, the entry written, then the imported entities marked
        ``replicatedFrom`` the source when the request replicates (REP-02 to REP-04).
        """  # noqa: D205 - one sentence
        options = result.request.options if result.request is not None else {}
        await self._servers.get_create_atlas_server(self._cluster, self._cluster)
        full_name = replicated(options, OPTION_KEY_REPLICATED_FROM)
        source = server_name_of(full_name) or None
        summary = codec.dumps(result.to_json()).decode()
        await self._audits.add(
            user_name, source, self._cluster, OPERATION_IMPORT, summary, start, end, has_data=bool(guids)
        )
        if result.operation_status is OperationStatus.FAIL:
            return
        replicating = OPTION_KEY_REPLICATED_FROM in options and not skip_update_replication_attr(options)
        marker = 0 if result.export_result is None else result.export_result.change_marker
        await self._replication(
            replicating=replicating,
            name=source or "",
            full_name=full_name,
            guids=guids,
            attribute=REPLICATED_FROM,
            marker=marker,
        )

    async def _replication(  # noqa: PLR0913 - Atlas's arguments
        self,
        *,
        replicating: bool,
        name: str,
        full_name: str,
        guids: list[str],
        attribute: str,
        marker: int,
    ) -> None:
        """``updateReplicationAttribute``: the server saved with the replication time of the first entity's GUID,
        then named by each entity's attribute (REP-04, MMS-04).
        """  # noqa: D205 - one sentence
        if not replicating or not guids:
            return
        server = await self._servers.get_create_atlas_server(name, full_name)
        server.set_additional_info_repl(repl_key_guid(guids[0]), marker)
        saved = await self._servers.save(server)
        await self._servers.update_entities_with_server(saved, guids, attribute)


def server_name_of(full_name: str) -> str:
    """``getServerNameFromFullName``: the part after ``$``, the full name without one."""
    if not full_name or DC_SERVER_NAME_SEPARATOR not in full_name:
        return full_name
    parts = [part for part in full_name.split(DC_SERVER_NAME_SEPARATOR) if part]
    if not parts:
        return ""
    return parts[1] if len(parts) >= 2 else parts[0]  # noqa: PLR2004 - <data center>$<server>


def repl_key_guid(guid: str) -> str:
    """``ReplKeyGuidFinder.get``: the GUID the replication details key on — the entity's own, for every type.

    Apache Atlas groups a Hive table or column under the GUID of its ``hive_db``; this catalogue bootstraps no
    Hive type, so the grouping went with the domain models (MMS-04, DV-179, DD-716).
    """
    return guid
