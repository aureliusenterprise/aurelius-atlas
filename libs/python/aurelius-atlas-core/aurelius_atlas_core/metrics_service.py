"""``MetricsService``: the counts of the catalogue's types, entities and classifications, the server's stats and its
process's system details (MET-01 to MET-04), and those metrics stored, listed, ranged, charted and purged
(MHS-01 to MHS-05).
"""  # noqa: D205 - one sentence

import logging
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo, EntityStatus
from aurelius_atlas_model.metrics import STATUS_CATEGORY, AtlasMetrics, AtlasMetricsMapToChart, AtlasMetricsStat
from aurelius_atlas_model.typedef import AtlasClassificationDef, AtlasEntityDef, TypeCategory
from aurelius_atlas_typesystem.type_names import INTERNAL_TYPE_NAME

from aurelius_atlas_core.authorization import ALLOW_ALL, Authorizer, filter_types_def
from aurelius_atlas_core.data_access import DataAccess
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.metrics_util import AtlasMetricsUtil, memory_details, runtime_info, system_info
from aurelius_atlas_core.typedef_store import types_def_of

TYPE = "type"
TYPE_SUBTYPES = "typeAndSubTypes"
ENTITY = "entity"
TAG = "tag"
GENERAL = "general"
SYSTEM = "system"

METRIC_COLLECTION_TIME = "collectionTime"
METRIC_STATS = "stats"
METRIC_TYPE_COUNT = TYPE + "Count"
METRIC_TYPE_UNUSED_COUNT = TYPE + "UnusedCount"
METRIC_ENTITY_COUNT = ENTITY + "Count"
METRIC_ENTITY_DELETED = ENTITY + "Deleted"
METRIC_ENTITY_ACTIVE = ENTITY + "Active"
METRIC_ENTITY_SHELL = ENTITY + "Shell"
METRIC_TAG_COUNT = TAG + "Count"
METRIC_ENTITIES_PER_TAG = TAG + "Entities"
METRIC_RUNTIME = "runtime"
METRIC_MEMORY = "memory"
METRIC_OS = "os"
METRIC_ENTITY_ACTIVE_INCL_SUBTYPES = f"{METRIC_ENTITY_ACTIVE}-{TYPE_SUBTYPES}"
METRIC_ENTITY_DELETED_INCL_SUBTYPES = f"{METRIC_ENTITY_DELETED}-{TYPE_SUBTYPES}"
METRIC_ENTITY_SHELL_INCL_SUBTYPES = f"{METRIC_ENTITY_SHELL}-{TYPE_SUBTYPES}"
"""The groups and names of the metrics, as ``MetricsService`` names them."""

ACTIVE = "ACTIVE"
DELETED = "DELETED"

LOGGER = logging.getLogger(__name__)

METRICS_ENTITY_TYPE_NAME = "__AtlasMetricsStat"
METRICS_ID_PROPERTY = "metricsId"
HOUR_MILLIS = 3_600_000
DEFAULT_TTL_HOURS = 336
"""``atlas.metrics.ttl.hours``: a stored metric is kept 14 days."""


class MetricsStatDTO:
    """``AtlasMetricsStatDTO``: a stored metric as its ``__AtlasMetricsStat`` entity, found by its ``metricsId``."""

    type_name = METRICS_ENTITY_TYPE_NAME

    def from_entity(self, found: AtlasEntityWithExtInfo) -> AtlasMetricsStat:
        """``from``: the metrics read from their JSON, the id, collection time and time to live."""
        entity = found.entity or AtlasEntity()
        text = entity.get_attribute("metrics")
        metrics = AtlasMetrics.model_validate(codec.loads(text)) if text else None
        return AtlasMetricsStat(
            guid=str(entity.guid),
            metrics_id=entity.get_attribute(METRICS_ID_PROPERTY),
            collection_time=int(entity.get_attribute("collectionTime") or 0),
            time_to_live_millis=int(entity.get_attribute("timeToLiveMillis") or 0),
            metrics=metrics,
        )

    def to_entities(self, obj: AtlasMetricsStat) -> list[AtlasEntity]:
        """``toEntity``: the id, the metrics as JSON, the collection time and time to live."""
        attributes: dict[str, Any] = {
            METRICS_ID_PROPERTY: obj.metrics_id,
            "collectionTime": obj.collection_time,
            "timeToLiveMillis": obj.time_to_live_millis,
        }
        if obj.metrics is not None:
            attributes["metrics"] = codec.dumps(obj.metrics.to_json()).decode()
        return [AtlasEntity(type_name=METRICS_ENTITY_TYPE_NAME, guid=obj.guid, attributes=attributes)]

    def unique_attributes(self, obj: AtlasMetricsStat) -> dict[str, Any]:
        """``getUniqueAttributes``: ``metricsId``."""
        return {METRICS_ID_PROPERTY: obj.metrics_id}


class MetricsService:
    """``MetricsService`` over the entities of ``store``; the types counted are those ``authorizer`` may read."""

    def __init__(
        self,
        store: EntityStore,
        util: AtlasMetricsUtil,
        *,
        authorizer: Authorizer = ALLOW_ALL,
        namespace: str = "default",
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> None:
        self._store = store
        self._util = util
        self._authorizer = authorizer
        self._namespace = namespace
        self._ttl_millis = ttl_hours * HOUR_MILLIS
        self._data_access = DataAccess(store, {AtlasMetricsStat: MetricsStatDTO()}, authorizer=authorizer)

    def metrics_stat(self, metrics: AtlasMetrics, type_names: list[str] | None = None) -> AtlasMetricsStat:
        """``new AtlasMetricsStat(metrics, typeNames)``: kept the configured time, its id of the namespace (MHS-01)."""
        return AtlasMetricsStat.of(metrics, self._ttl_millis, self._namespace, type_names)

    async def save_metrics_stat(self, stat: AtlasMetricsStat) -> AtlasMetricsStat:
        """``saveMetricsStat``: the metric stored as its entity (MHS-01).

        Raises:
            AtlasError: ``BAD_REQUEST`` without an id, ``METRICSSTAT_ALREADY_EXISTS`` for an id stored already.
        """
        if not stat.metrics_id:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "MetricsStat definition missing.")
        entity_type = self._store.registry.entity_type(METRICS_ENTITY_TYPE_NAME)
        if entity_type is not None and await self._store.find_by_unique_attributes(
            entity_type, {METRICS_ID_PROPERTY: stat.metrics_id}
        ):
            raise AtlasError(AtlasErrorCode.METRICSSTAT_ALREADY_EXISTS, str(stat.collection_time))
        return await self._data_access.save(stat)

    async def save_metrics(self, *, store_connected: bool) -> AtlasMetricsStat:
        """``AdminResource#saveMetrics``: the metrics of now, stored (MHS-05)."""
        return await self.save_metrics_stat(self.metrics_stat(await self.get_metrics(store_connected=store_connected)))

    async def purge_metrics_stats(self) -> list[AtlasMetricsStat]:
        """``purgeMetricsStats``: the stored metrics whose time to live has passed, deleted (MHS-05)."""
        now = self._store.now()
        expired = [
            stat
            for stat in await self.get_all_metrics_stats(min_info=True)
            if stat.collection_time + stat.time_to_live_millis < now
        ]
        for stat in expired:
            await self._data_access.delete(stat.guid)
            LOGGER.info("The metrics collected at %s are deleted", stat.collection_time)
        return expired

    async def get_metrics_stat_by_collection_time(self, collection_time: int) -> AtlasMetricsStat:
        """``getMetricsStatByCollectionTime``: the stored metric of the id of that time (MHS-02).

        Raises:
            AtlasError: ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` when none is stored.
        """
        return await self._data_access.load(
            AtlasMetricsStat(metrics_id=self.metrics_stat_id(collection_time), collection_time=collection_time)
        )

    def metrics_stat_id(self, collection_time: int) -> str:
        """The id of the metrics collected at ``collection_time`` in the namespace."""
        return (
            AtlasMetricsStat.of(
                AtlasMetrics(data={GENERAL: {METRIC_COLLECTION_TIME: collection_time}}), 0, self._namespace
            ).metrics_id
            or ""
        )

    async def get_all_metrics_stats(self, *, min_info: bool) -> list[AtlasMetricsStat]:
        """``getAllMetricsStats``: every stored metric not deleted, the latest first; without the metrics for
        ``min_info`` (MHS-02).
        """  # noqa: D205 - one sentence
        stored = [
            AtlasMetricsStat(guid=str(entity.guid))
            for entity in await self._store.of_types([METRICS_ENTITY_TYPE_NAME])
            if entity.state is EntityStatus.ACTIVE
        ]
        found = sorted(await self._data_access.load_all(stored), key=lambda stat: -stat.collection_time)
        if min_info:
            for stat in found:
                stat.metrics = None
        return found

    async def get_metrics_in_range_by_type_names(
        self, start_time: int, end_time: int, type_names: list[str]
    ) -> list[AtlasMetricsStat]:
        """``getMetricsInRangeByTypeNames``: those collected from ``start_time`` to ``end_time``, the latest first,
        each made anew with the type data of ``type_names`` and no metrics (MHS-03).

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` when the start is not before the end.
        """  # noqa: D205 - one sentence
        if start_time >= end_time:
            message = f"startTime: '{start_time}', should be less than, endTime: '{end_time}'"
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, message)
        found = []
        for stat in await self.get_all_metrics_stats(min_info=False):
            if stat.metrics is not None and start_time <= stat.collection_time <= end_time:
                ranged = self.metrics_stat(stat.metrics, type_names)
                ranged.metrics = None
                found.append(ranged)
        return found

    async def get_metrics_for_chart_by_type_names(
        self, start_time: int, end_time: int, type_names: list[str]
    ) -> dict[str, list[AtlasMetricsMapToChart]]:
        """``getMetricsForChartByTypeNames``: per type, its active, deleted and shell counts in the range as
        ``[collectionTime, count]`` pairs, the earliest first; no pairs, no series (MHS-04).
        """  # noqa: D205 - one sentence
        ranged = list(reversed(await self.get_metrics_in_range_by_type_names(start_time, end_time, type_names)))
        charts: dict[str, list[AtlasMetricsMapToChart]] = {}
        for name in type_names:
            charts[name] = (
                [
                    AtlasMetricsMapToChart(
                        key=status,
                        values=[
                            [stat.collection_time, int(((stat.type_data or {}).get(name) or {}).get(status, 0))]
                            for stat in ranged
                        ],
                    )
                    for status in STATUS_CATEGORY
                ]
                if ranged
                else []
            )
        return charts

    async def get_metrics(self, *, store_connected: bool) -> AtlasMetrics:
        """``getMetrics``: the general, entity, tag and system metrics (MET-01).

        The entities are counted per entity type that is not internal, by state and as shells, alone and with their
        sub types; the classification instances per classification type, each count left out when zero (MET-02).
        """
        registry = self._store.registry
        readable = filter_types_def(self._authorizer, types_def_of(self._readable_typedefs()))
        entity_names = [str(typedef.name) for typedef in readable.entity_defs or []]
        active: dict[str, int] = {}
        deleted: dict[str, int] = {}
        shell: dict[str, int] = {}
        for found in await self._store.type_counts():
            if found.state == ACTIVE:
                active[found.type_name] = active.get(found.type_name, 0) + found.count
            elif found.state == DELETED:
                deleted[found.type_name] = deleted.get(found.type_name, 0) + found.count
            if found.incomplete:
                shell[found.type_name] = shell.get(found.type_name, 0) + found.count
        active, deleted, shell = (_counted(counts, entity_names) for counts in (active, deleted, shell))
        unused = sum(1 for name in entity_names if name not in active and name not in deleted)
        with_sub_types: tuple[dict[str, int], ...] = ({}, {}, {})
        for name in entity_names:
            entity_type = registry.entity_type(name)
            names = entity_type.type_and_all_sub_types if entity_type is not None else [name]
            for counts, found in zip((active, deleted, shell), with_sub_types, strict=True):
                count = sum(counts.get(sub_type, 0) for sub_type in names)
                if count > 0:
                    found[name] = count
        classifications = await self._store.classification_type_counts()
        tagged = {
            str(typedef.name): classifications[str(typedef.name)]
            for typedef in readable.classification_defs or []
            if classifications.get(str(typedef.name), 0) > 0
        }
        metrics = AtlasMetrics()
        metrics.add_metric(GENERAL, METRIC_COLLECTION_TIME, self._store.now())
        stats = self._util.stats(backend_connected=store_connected, index_connected=store_connected)
        metrics.add_metric(GENERAL, METRIC_STATS, stats)
        metrics.add_metric(GENERAL, METRIC_TYPE_COUNT, len(registry.all_type_names()))
        metrics.add_metric(GENERAL, METRIC_TAG_COUNT, len(registry.typedef_names(TypeCategory.CLASSIFICATION)))
        metrics.add_metric(GENERAL, METRIC_TYPE_UNUSED_COUNT, unused)
        metrics.add_metric(GENERAL, METRIC_ENTITY_COUNT, sum(active.values()) + sum(deleted.values()))
        metrics.add_metric(ENTITY, METRIC_ENTITY_ACTIVE, active)
        metrics.add_metric(ENTITY, METRIC_ENTITY_DELETED, deleted)
        metrics.add_metric(ENTITY, METRIC_ENTITY_SHELL, shell)
        metrics.add_metric(ENTITY, METRIC_ENTITY_ACTIVE_INCL_SUBTYPES, with_sub_types[0])
        metrics.add_metric(ENTITY, METRIC_ENTITY_DELETED_INCL_SUBTYPES, with_sub_types[1])
        metrics.add_metric(ENTITY, METRIC_ENTITY_SHELL_INCL_SUBTYPES, with_sub_types[2])
        metrics.add_metric(TAG, METRIC_ENTITIES_PER_TAG, tagged)
        metrics.add_metric(SYSTEM, METRIC_MEMORY, memory_details())
        metrics.add_metric(SYSTEM, METRIC_OS, system_info())
        metrics.add_metric(SYSTEM, METRIC_RUNTIME, runtime_info())
        return metrics

    def _readable_typedefs(self) -> list[AtlasEntityDef | AtlasClassificationDef]:
        """``getTypesDef``: the entity definitions not directly under ``__internal``, and the classification ones."""
        registry = self._store.registry
        entity_defs = [
            typedef
            for typedef in registry.typedefs(TypeCategory.ENTITY)
            if isinstance(typedef, AtlasEntityDef) and INTERNAL_TYPE_NAME not in (typedef.super_types or [])
        ]
        classification_defs = [
            typedef
            for typedef in registry.typedefs(TypeCategory.CLASSIFICATION)
            if isinstance(typedef, AtlasClassificationDef)
        ]
        return [*entity_defs, *classification_defs]


def _counted(counts: dict[str, int], names: list[str]) -> dict[str, int]:
    """The counts of the named types that are above zero."""
    return {name: counts[name] for name in names if counts.get(name, 0) > 0}
