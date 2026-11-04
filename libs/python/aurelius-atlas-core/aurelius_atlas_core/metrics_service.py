"""``MetricsService#getMetrics``: the counts of the catalogue's types, entities and classifications, the server's stats
and its process's system details (MET-01 to MET-04).
"""  # noqa: D205 - one sentence

from aurelius_atlas_model.metrics import AtlasMetrics
from aurelius_atlas_model.typedef import AtlasClassificationDef, AtlasEntityDef, TypeCategory
from aurelius_atlas_typesystem.type_names import INTERNAL_TYPE_NAME

from aurelius_atlas_core.authorization import ALLOW_ALL, Authorizer, filter_types_def
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


class MetricsService:
    """``MetricsService`` over the entities of ``store``; the types counted are those ``authorizer`` may read."""

    def __init__(self, store: EntityStore, util: AtlasMetricsUtil, *, authorizer: Authorizer = ALLOW_ALL) -> None:
        self._store = store
        self._util = util
        self._authorizer = authorizer

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
