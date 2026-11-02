"""``ExportService``: the entities an export request reaches, their types and its result, into a ZIP (EXP-03 to EXP-06).

Atlas's ``ExportService`` with its ``ExportContext``: each item's starting entities, then the entities they reach,
lineage after the rest, each added once with the entities it owns; then the types they use, the order they were
added in and the result (DD-303).
"""

from dataclasses import dataclass, field
from enum import Enum

from aurelius_atlas_model.errors import AtlasError
from aurelius_atlas_model.impexp import (
    FETCH_TYPE_CONNECTED,
    FETCH_TYPE_FULL,
    FETCH_TYPE_INCREMENTAL,
    AtlasExportRequest,
    AtlasExportResult,
    OperationStatus,
)
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo, AtlasObjectId

from aurelius_atlas_core.entities_extractor import EntitiesExtractor, TraversalDirection
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.export_type_processor import ExportTypeProcessor
from aurelius_atlas_core.start_entity_fetch_by_export_request import StartEntityFetchByExportRequest
from aurelius_atlas_core.typedef_store import types_def_of
from aurelius_atlas_core.zip_sink import ZipSink

CLUSTER_NAME_DEFAULT = "default"
"""``AuditsWriter.CLUSTER_NAME_DEFAULT``: the cluster an export comes from unless named (EXP-06)."""
WITH_EXT_INFO = "entity:withExtInfo"


class ExportFetchType(Enum):
    """``ExportFetchType``: how far an export reaches from its starting entities (EXP-02, EXP-04)."""

    FULL = FETCH_TYPE_FULL
    CONNECTED = FETCH_TYPE_CONNECTED
    INCREMENTAL = FETCH_TYPE_INCREMENTAL

    @classmethod
    def of(cls, text: str) -> ExportFetchType:
        """``from``: the type named in any case, else ``FULL``."""
        return next((fetch for fetch in cls if fetch.value.lower() == text.lower()), cls.FULL)


@dataclass
class ExportContext:
    """``ExportContext``: what an export has reached and added so far."""

    result: AtlasExportResult
    sink: ZipSink
    fetch_type: ExportFetchType
    skip_lineage: bool
    change_marker: int
    entity_creation_order: list[str] = field(default_factory=list)
    guids_processed: set[str] = field(default_factory=set)
    guids_to_process: list[str] = field(default_factory=list)
    lineage_to_process: list[str] = field(default_factory=list)
    guid_direction: dict[str, TraversalDirection] = field(default_factory=dict)
    entity_types: list[str] = field(default_factory=list)
    classification_types: list[str] = field(default_factory=list)
    struct_types: list[str] = field(default_factory=list)
    enum_types: list[str] = field(default_factory=list)
    relationship_types: list[str] = field(default_factory=list)
    business_metadata_types: list[str] = field(default_factory=list)
    terms_glossary: dict[str, str] = field(default_factory=dict)

    def add_to_be_processed(self, is_process: bool, guid: str, direction: TraversalDirection) -> None:  # noqa: FBT001 - Atlas's signature
        """``addToBeProcessed``: lineage entities wait for the rest; each remembers the direction it was reached in."""
        queue = self.lineage_to_process if is_process else self.guids_to_process
        if guid not in queue:
            queue.append(guid)
        self.guid_direction[guid] = direction

    def does_timestamp_qualify(self, entity: AtlasEntity) -> bool:
        """``doesTimestampQualify``: any entity, or for an incremental export one updated since its marker."""
        if self.fetch_type is not ExportFetchType.INCREMENTAL:
            return True
        return self.change_marker <= _update_time(entity)

    def entities_with_modified_timestamp(self, found: AtlasEntityWithExtInfo) -> list[AtlasEntity]:
        """``getEntitiesWithModifiedTimestamp``: of an incremental export, the entity or its updated owned ones."""
        if self.fetch_type is not ExportFetchType.INCREMENTAL:
            return []
        if found.entity is not None and self.does_timestamp_qualify(found.entity):
            return [found.entity]
        return [entity for entity in (found.referred_entities or {}).values() if self.does_timestamp_qualify(entity)]

    def add_to_sink(self, found: AtlasEntityWithExtInfo) -> None:
        """``addToSink``: the entity's GUID appended to the export order, the entity written."""
        guid = str(found.entity.guid) if found.entity is not None else ""
        if guid not in self.entity_creation_order:
            self.entity_creation_order.append(guid)
        self.sink.add(found)


class ExportService:
    """Exports the entities of ``store`` as Atlas does; ``cluster_name`` names where they come from (EXP-06)."""

    def __init__(self, store: EntityStore, *, cluster_name: str = CLUSTER_NAME_DEFAULT) -> None:
        self._store = store
        self._cluster_name = cluster_name
        self._retriever = EntityRetriever(store)
        self._extractor = EntitiesExtractor(store)
        self._types = ExportTypeProcessor(store)
        self._start = StartEntityFetchByExportRequest(store)

    async def run(
        self, sink: ZipSink, request: AtlasExportRequest, user_name: str | None, host_name: str, requesting_ip: str
    ) -> AtlasExportResult:
        """``run``: each item exported into ``sink``, then its order, types and result (EXP-03 to EXP-06).

        A failure of an item is that item's ``FAIL``; the result says the overall status.
        """
        start = self._store.now()
        result = AtlasExportResult(
            request=request,
            user_name=user_name,
            client_ip_address=requesting_ip,
            host_name=host_name,
            time_stamp=start,
            change_marker=start,
        )
        context = ExportContext(
            result=result,
            sink=sink,
            fetch_type=ExportFetchType.of(request.fetch_type()),
            skip_lineage=request.skip_lineage(),
            change_marker=request.change_marker(),
        )
        statuses = [await self._process_object_id(item, context) for item in request.items_to_export]
        self._process_types_def(context)
        result.source_cluster_name = self._cluster_name
        sink.set_export_order(context.entity_creation_order)
        sink.set_types_def(result.data.types_def if result.data is not None else None)
        result.operation_status = overall_operation_status(statuses)
        result.increment_metrics_counter("duration", self._store.now() - start)
        result.data = None
        sink.set_result(result)
        return result

    def _process_types_def(self, context: ExportContext) -> None:
        """``processTypesDef``: the definitions of the types the export collected, by kind (EXP-06)."""
        names = [
            *context.entity_types,
            *context.classification_types,
            *context.struct_types,
            *context.enum_types,
            *context.relationship_types,
            *context.business_metadata_types,
        ]
        registry = self._store.registry
        found = [typedef for name in names if (typedef := registry.typedef_by_name(name)) is not None]
        if context.result.data is not None:
            context.result.data.types_def = types_def_of(found)

    async def _process_object_id(self, item: AtlasObjectId, context: ExportContext) -> OperationStatus:
        """``processObjectId``: the item's starting entities, then what they reach, lineage last (EXP-03, EXP-04)."""
        try:
            guids = await self._start.get(context.result.request or AtlasExportRequest(), item)
            if not guids:
                return OperationStatus.FAIL
            self._extractor.set_extractor(self._store.registry.entity_type(item.type_name))
            for guid in guids:
                await self._process_entity_guid(guid, context)
            while context.guids_to_process:
                while context.guids_to_process:
                    await self._process_entity_guid(context.guids_to_process.pop(0), context)
                for guid in context.lineage_to_process:
                    if guid not in context.guids_to_process:
                        context.guids_to_process.append(guid)
                context.lineage_to_process.clear()
        except AtlasError:
            return OperationStatus.FAIL
        return OperationStatus.SUCCESS

    async def _process_entity_guid(self, guid: str, context: ExportContext) -> None:
        """``processEntityGuid``: the entity with what it owns, unless already processed.

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND``.
        """
        if guid not in context.guids_processed:
            await self.process_entity(await self._retriever.entity_with_ext_info(guid), context)

    async def process_entity(self, found: AtlasEntityWithExtInfo, context: ExportContext) -> None:
        """``processEntity``: its types collected, its terms' glossaries added, it added, and what it reaches queued.

        The entities it owns have their types collected and what they reach queued too (EXP-04 to EXP-06).
        """
        entity = found.entity
        if entity is None:  # pragma: no cover - a read entity is there
            return
        await self._types.add_types(entity, context)
        if context.terms_glossary:
            await self._add_glossary_entities(context)
        self._add_entity(found, context)
        context.guids_processed.add(str(entity.guid))
        await self._extractor.get(entity, context)
        for owned in (found.referred_entities or {}).values():
            await self._types.add_types(owned, context)
            await self._extractor.get(owned, context)
        context.guids_processed.update(found.referred_entities or {})

    async def _add_glossary_entities(self, context: ExportContext) -> None:
        """``addGlossaryEntities``: the glossary and the term of each term assigned, alone, unless added (EXP-05)."""
        try:
            for term_guid, glossary_guid in context.terms_glossary.items():
                try:
                    for guid in (glossary_guid, term_guid):
                        if not context.sink.has_entity(guid):
                            read = (await self._retriever.entity_with_ext_info(guid)).entity
                            self._add_entity(AtlasEntityWithExtInfo(entity=read), context)
                except AtlasError:
                    continue
        finally:
            context.terms_glossary.clear()

    def _add_entity(self, found: AtlasEntityWithExtInfo, context: ExportContext) -> None:
        """``addEntity``: the entity once, counted by type with each it owns; of an incremental export only when
        updated since its marker, else each owned entity that was, alone (EXP-05, EXP-06).
        """  # noqa: D205 - one sentence
        entity = found.entity
        if entity is None or context.sink.has_entity(str(entity.guid)):
            return
        if context.does_timestamp_qualify(entity):
            context.add_to_sink(found)
            context.result.increment_metrics_counter(f"entity:{entity.type_name}")
            for owned in (found.referred_entities or {}).values():
                context.result.increment_metrics_counter(f"entity:{owned.type_name}")
            context.result.increment_metrics_counter(WITH_EXT_INFO)
            return
        for updated in context.entities_with_modified_timestamp(found):
            context.add_to_sink(AtlasEntityWithExtInfo(entity=updated))
            context.result.increment_metrics_counter(f"entity:{updated.type_name}")


def overall_operation_status(statuses: list[OperationStatus]) -> OperationStatus:
    """``getOverallOperationStatus``: the items' one status, ``PARTIAL_SUCCESS`` for mixed, ``FAIL`` for none."""
    if not statuses:
        return OperationStatus.FAIL
    return statuses[0] if all(status is statuses[0] for status in statuses) else OperationStatus.PARTIAL_SUCCESS


def _update_time(entity: AtlasEntity) -> int:
    """The entity's ``updateTime`` in epoch milliseconds."""
    value = entity.update_time
    if value is None:
        return 0
    return value if isinstance(value, int) else int(value.timestamp() * 1000)
