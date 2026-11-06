"""``ImportService``: an export's ZIP imported, types first, then its entities (IMS-01 to IMS-06).

Importing an export of Apache Atlas 2.4 migrates it: the entities keep their GUIDs (6.3b1).
"""

from pathlib import Path

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.impexp import (
    FILE_NAME_KEY,
    OPTION_KEY_MIGRATION,
    START_GUID_KEY,
    START_POSITION_KEY,
    TRANSFORMS_KEY,
    UPDATE_TYPE_DEFINITION_KEY,
    AtlasImportRequest,
    AtlasImportResult,
    OperationStatus,
)

from aurelius_atlas_core.audits_writer import AuditsWriter
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.import_transforms import ImportTransforms, shape
from aurelius_atlas_core.import_type_def_processor import ImportTypeDefProcessor
from aurelius_atlas_core.regular_import import RegularImport
from aurelius_atlas_core.task_hold import TaskHold
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_core.zip_source import ZipSource

NO_FILE_NAME = "FILENAME parameter not found"
FILE_NOT_FOUND = "{}: file not found"


class ImportService:
    """``ImportService`` into ``store`` and ``typedef_store``, entities written by ``writer``.

    ``audits``, when given, records each import but a migration's, and the replication it asks for (REP-02 to REP-04).
    """

    def __init__(
        self,
        store: EntityStore,
        typedef_store: TypedefStore,
        writer: EntityWriter,
        *,
        audits: AuditsWriter | None = None,
    ) -> None:
        self._store = store
        self._typedef_store = typedef_store
        self._writer = writer
        self._audits = audits

    async def run(
        self, content: bytes, request: AtlasImportRequest | None, user_name: str | None, host_name: str, ip: str
    ) -> AtlasImportResult:
        """``run``: the ZIP's types merged unless asked not to, its entities written from the start asked for.

        Raises:
            AtlasError: ``IMPORT_ATTEMPTING_EMPTY_ZIP``; ``INVALID_PARAMETERS`` for no entities; what merging the
                types or writing an entity fails with.
        """
        request = request or AtlasImportRequest()
        source = ZipSource(content)
        result = AtlasImportResult(
            request=request,
            user_name=user_name,
            client_ip_address=ip,
            host_name=host_name,
            time_stamp=self._store.now(),
        )
        start = self._store.now()
        transforms = ImportTransforms.from_json(request.option(TRANSFORMS_KEY))
        if transforms is not None:
            exported = source.export_result()
            await shape(transforms, None if exported is None else exported.request, self._typedef_store, user_name)
            source.import_transform = transforms
        update_types = request.option(UPDATE_TYPE_DEFINITION_KEY)
        if update_types is None or update_types == "true":
            await ImportTypeDefProcessor(self._typedef_store, user_name).process_types(source.types_def(), result)
        start_guid, start_position = request.option(START_GUID_KEY), request.option(START_POSITION_KEY)
        if start_guid is not None:
            source.set_position_using_entity_guid(start_guid)
        elif start_position is not None:
            source.set_position(_position(start_position))
        result.export_result = source.export_result()
        await self._import_entities(source, result)
        end = self._store.now()
        result.increment_metrics_counter("duration", end - start)
        result.operation_status = OperationStatus.SUCCESS
        if self._audits is not None and OPTION_KEY_MIGRATION not in request.options:
            await self._audits.write_import(user_name, result, start, end, source.creation_order)
        return result

    async def _import_entities(self, source: ZipSource, result: AtlasImportResult) -> None:
        """The entities written, the tasks they record held until the last is written or the import fails (IMT-01,
        IMT-02).
        """  # noqa: D205 - one sentence
        hold = TaskHold.start(self._store) if self._writer.defers_tasks else None
        self._writer.hold_tasks(hold)
        try:
            await RegularImport(self._store, self._writer).run(source, result)
        finally:
            self._writer.hold_tasks(None)
            if hold is not None:
                await hold.release(self._store)

    async def run_file(
        self, request: AtlasImportRequest, folder: Path | None, user_name: str | None, host_name: str, ip: str
    ) -> AtlasImportResult:
        """``run`` of a file: the ZIP the ``fileName`` option names, read only from ``folder`` (IMS-06, DV-125).

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` for no file name, or a file not found there; as ``run``.
        """
        file_name = request.option(FILE_NAME_KEY)
        if file_name is None or not file_name.strip():
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_FILE_NAME)
        path = _in_folder(folder, file_name)
        if path is None:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, FILE_NOT_FOUND.format(file_name))
        return await self.run(path.read_bytes(), request, user_name, host_name, ip)


def _in_folder(folder: Path | None, file_name: str) -> Path | None:
    """The file of the name within ``folder``, or None for no folder, a file elsewhere or none there."""
    if folder is None:
        return None
    root = folder.resolve()
    path = (root / file_name).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def _position(text: str) -> int:
    """``Integer.parseInt`` of the start position.

    Raises:
        AtlasError: ``INTERNAL_ERROR`` for one that is no number, as Java's ``NumberFormatException`` answers.
    """
    try:
        return int(text)
    except ValueError as error:
        raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, f'For input string: "{text}"') from error
