"""The metrics of ``admin/metrics`` (MET-01 to MET-04) and those stored (MHS-01 to MHS-05), in memory.

Read from Apache Atlas 2.4.0's ``MetricsService``, ``AtlasMetricsStat``, ``AtlasMetricsStatDTO``,
``AtlasMetricsUtil#getStats``, ``AtlasMetricsCounter``,
``AtlasMetricJVMUtil`` and its ``MetricsServiceTest``.
"""

import json

import pytest
from aurelius_atlas_core.authorization import AtlasPrivilege
from aurelius_atlas_core.entity_documents import LinkedKind, TypeCount
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.metrics_service import MetricsService
from aurelius_atlas_core.metrics_util import (
    AtlasMetricsUtil,
    memory_details,
    millis_to_time_diff,
    runtime_info,
    system_info,
)
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_model.metrics import AtlasMetricsStat
from aurelius_atlas_model.typedef import AtlasEntityDef, AtlasTypesDef, TypeCategory
from aurelius_atlas_typesystem.registry import TypeRegistry

HOUR = 3_600_000
DAY = 24 * HOUR
BASE = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json").read_text(encoding="utf-8"))
TYPES = {
    "entityDefs": [
        {"name": "met_table", "superTypes": ["DataSet"]},
        {"name": "met_view", "superTypes": ["met_table"]},
        {"name": "met_unused", "superTypes": ["DataSet"]},
        {"name": "met_internal", "superTypes": ["__internal"]},
    ],
    "classificationDefs": [{"name": "met_pii"}, {"name": "met_unused_tag"}],
}


class DenyTypes:
    """An authorizer that grants everything but ``type-read``."""

    def is_access_allowed(self, privilege: AtlasPrivilege) -> bool:
        """Every privilege but ``type-read``."""
        return privilege is not AtlasPrivilege.TYPE_READ

    def verify_access(self, privilege: AtlasPrivilege, *action: object) -> None:
        """Never refuses."""


async def catalogue() -> tuple[EntityStore, MemoryEntityDocuments, dict[str, str]]:
    """Two tables, a view and an internal entity, a table classified, one table deleted and one view a shell."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    for model in (BASE, TYPES):
        await types.create_types_def(AtlasTypesDef.model_validate(model))
    documents = MemoryEntityDocuments()
    store = EntityStore(types.registry, documents, clock=lambda: 50.5)
    names = [("met_table", "t1"), ("met_table", "t2"), ("met_view", "v1"), ("met_internal", "i1")]
    body = {
        "entities": [
            {
                "typeName": type_name,
                "guid": f"-{n}",
                "attributes": {"qualifiedName": name, "name": name},
                "classifications": [{"typeName": "met_pii"}] if name == "t1" else [],
            }
            for n, (type_name, name) in enumerate(names, start=1)
        ]
    }
    writer = EntityWriter(store)
    created = (await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate(body))).guid_assignments or {}
    guids = {name: created[f"-{n}"] for n, (_, name) in enumerate(names, start=1)}
    await writer.delete_by_id(guids["t2"])
    documents.entities[guids["v1"]][0]["isIncomplete"] = True
    return store, documents, guids


@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsService.get_metrics", rules=["MET-01", "MET-02"])
async def test__the_metrics_count_the_entities_by_type_state_and_sub_types() -> None:
    """Per type not internal: active and deleted, shells, with sub types; the classification instances per type."""
    store, _, _ = await catalogue()
    util = AtlasMetricsUtil(clock=lambda: 40.0)
    util.on_server_start()
    metrics = await MetricsService(store, util).get_metrics(store_connected=True)
    data = metrics.data or {}
    assert sorted(data) == ["entity", "general", "system", "tag"]
    assert data["entity"] == {
        "entityActive": {"met_table": 1, "met_view": 1},
        "entityDeleted": {"met_table": 1},
        "entityShell": {"met_view": 1},
        "entityActive-typeAndSubTypes": {"met_table": 2, "met_view": 1, "DataSet": 2, "Asset": 2, "Referenceable": 2},
        "entityDeleted-typeAndSubTypes": {"met_table": 1, "DataSet": 1, "Asset": 1, "Referenceable": 1},
        "entityShell-typeAndSubTypes": {"met_view": 1, "met_table": 1, "DataSet": 1, "Asset": 1, "Referenceable": 1},
    }
    assert data["tag"] == {"tagEntities": {"met_pii": 1}}
    general = data["general"]
    assert general["collectionTime"] == 50_500
    assert general["entityCount"] == 3
    assert general["tagCount"] == 2
    assert general["typeCount"] == len(store.registry.all_type_names())
    assert general["typeUnusedCount"] > 0
    assert general["stats"]["Server:statusBackendStore"] == "connected"
    assert sorted(data["system"]) == ["memory", "os", "runtime"]


@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsService.get_metrics", rules=["MET-02"])
async def test__the_unused_types_are_the_entity_types_without_entities() -> None:
    """``met_unused`` and the base types never written are unused; the internal type is not counted at all."""
    store, _, _ = await catalogue()
    data = (await MetricsService(store, AtlasMetricsUtil()).get_metrics(store_connected=True)).data or {}
    readable = [
        str(typedef.name)
        for typedef in store.registry.typedefs(TypeCategory.ENTITY)
        if isinstance(typedef, AtlasEntityDef) and "__internal" not in (typedef.super_types or [])
    ]
    used = {"met_table", "met_view"}
    assert data["general"]["typeUnusedCount"] == len([name for name in readable if name not in used])
    assert "met_internal" not in data["entity"]["entityActive"]


@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsService.get_metrics", rules=["MET-02"])
async def test__a_user_who_may_not_read_types_gets_no_counts_of_them() -> None:
    """``filterTypesDef`` leaves no type, so no entity or tag counts; the registry's counts stay."""
    store, _, _ = await catalogue()
    metrics = await MetricsService(store, AtlasMetricsUtil(), authorizer=DenyTypes()).get_metrics(store_connected=False)
    data = metrics.data or {}
    assert data["entity"] == {
        "entityActive": {},
        "entityDeleted": {},
        "entityShell": {},
        "entityActive-typeAndSubTypes": {},
        "entityDeleted-typeAndSubTypes": {},
        "entityShell-typeAndSubTypes": {},
    }
    assert data["tag"] == {"tagEntities": {}}
    assert data["general"]["entityCount"] == 0
    assert data["general"]["typeUnusedCount"] == 0
    assert data["general"]["tagCount"] == 2
    assert data["general"]["stats"]["Server:statusIndexStore"] == "not-connected"


@pytest.mark.covers("aurelius_atlas_core.entity_store.EntityStore.type_counts", rules=["MET-02"])
@pytest.mark.covers("aurelius_atlas_core.entity_store.EntityStore.classification_type_counts", rules=["MET-02"])
@pytest.mark.covers("aurelius_atlas_core.entity_documents.EntityDocuments.type_counts")
@pytest.mark.covers("aurelius_atlas_core.entity_documents.EntityDocuments.linked_type_counts")
@pytest.mark.covers("aurelius_atlas_core.testing.memory.MemoryEntityDocuments.type_counts")
@pytest.mark.covers("aurelius_atlas_core.testing.memory.MemoryEntityDocuments.linked_type_counts")
async def test__the_store_counts_the_entities_and_classifications_by_type() -> None:
    """By type, state and shell flag; the classification instances by type."""
    store, _, _ = await catalogue()
    assert await store.type_counts() == [
        TypeCount("met_internal", "ACTIVE", incomplete=False, count=1),
        TypeCount("met_table", "ACTIVE", incomplete=False, count=1),
        TypeCount("met_table", "DELETED", incomplete=False, count=1),
        TypeCount("met_view", "ACTIVE", incomplete=True, count=1),
    ]
    assert await store.classification_type_counts() == {"met_pii": 1}
    assert await MemoryEntityDocuments().linked_type_counts(LinkedKind.TASK) == {}


@pytest.mark.covers("aurelius_atlas_core.metrics_util.AtlasMetricsUtil.stats", rules=["MET-03"])
@pytest.mark.covers("aurelius_atlas_core.metrics_util.AtlasMetricsUtil.on_server_start", rules=["MET-03"])
@pytest.mark.covers("aurelius_atlas_core.metrics_util.AtlasMetricsUtil.on_server_activation", rules=["MET-03"])
def test__the_stats_are_the_servers_times_and_no_notifications() -> None:
    """The start and activation times, the up time, the stores' status; notifications of counters never counted."""
    now = [10 * DAY + 5 * HOUR + 1234.567]
    util = AtlasMetricsUtil(clock=lambda: now[0] / 1000)
    assert util.stats(backend_connected=True, index_connected=True)["Server:startTimeStamp"] == 0
    util.on_server_start()
    now[0] += 1000
    util.on_server_activation()
    now[0] += DAY + 2 * HOUR + 3 * 60_000 + 4000
    stats = util.stats(backend_connected=True, index_connected=False)
    assert stats["Server:startTimeStamp"] == 10 * DAY + 5 * HOUR + 1234
    assert stats["Server:activeTimeStamp"] == 10 * DAY + 5 * HOUR + 2234
    assert stats["Server:upTime"] == "1 day 2 hour 3 min 5 sec"
    assert stats["Server:statusBackendStore"] == "connected"
    assert stats["Server:statusIndexStore"] == "not-connected"
    assert stats["Notification:topicDetails"] == {}
    assert stats["Notification:lastMessageProcessedTime"] == 0
    assert stats["Notification:currentDayStartTime"] == 11 * DAY
    assert stats["Notification:currentHourStartTime"] == 11 * DAY + 7 * HOUR
    counts = {key: value for key, value in stats.items() if key.startswith("Notification:")}
    assert len(counts) == 34
    assert {
        value for key, value in counts.items() if "StartTime" not in key and key != "Notification:topicDetails"
    } == {0}


@pytest.mark.covers("aurelius_atlas_core.metrics_util.millis_to_time_diff", rules=["MET-03"])
def test__the_up_time_names_each_unit_above_zero() -> None:
    """``millisToTimeDiff``: days, hours, minutes and seconds, those of zero left out."""
    assert millis_to_time_diff(0) == ""
    assert millis_to_time_diff(59_999) == "59 sec"
    assert millis_to_time_diff(HOUR) == "1 hour "
    assert millis_to_time_diff(2 * DAY + 60_000) == "2 day 1 min "


@pytest.mark.covers("aurelius_atlas_core.metrics_util.runtime_info", rules=["MET-04"])
@pytest.mark.covers("aurelius_atlas_core.metrics_util.memory_details", rules=["MET-04"])
@pytest.mark.covers("aurelius_atlas_core.metrics_util.system_info", rules=["MET-04"])
def test__the_system_details_are_the_python_process() -> None:
    """The Python runtime, the process's largest resident set, the operating system and its processors (DV-135)."""
    assert sorted(runtime_info()) == ["name", "version"]
    assert int(memory_details()["maxResidentSetSize"]) > 0
    info = system_info()
    assert len(info["os.spec"].split(", ")) == 3
    assert int(info["os.vcpus"]) >= 1


async def stored_metrics() -> tuple[MetricsService, list[float], dict[str, str]]:
    """The catalogue's metrics stored at 1, 2 and 3 hours, kept 2 hours; the clock settable."""
    store, _, guids = await catalogue()
    now = [HOUR / 1000]
    store = EntityStore(store.registry, store._documents, clock=lambda: now[0])  # noqa: SLF001 - the same documents
    service = MetricsService(store, AtlasMetricsUtil(), namespace="cl1", ttl_hours=2)
    for hour in (1, 2, 3):
        now[0] = hour * HOUR / 1000
        await service.save_metrics(store_connected=True)
    return service, now, guids


@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsService.save_metrics_stat", rules=["MHS-01"])
@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsService.save_metrics", rules=["MHS-01", "MHS-05"])
@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsService.metrics_stat", rules=["MHS-01"])
@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsStatDTO.to_entities", rules=["MHS-01"])
@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsStatDTO.from_entity", rules=["MHS-01"])
@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsStatDTO.unique_attributes", rules=["MHS-01"])
async def test__the_metrics_are_stored_once_per_collection_time() -> None:
    """An id of the time and namespace, kept the configured hours; the same time again, or no id, is refused."""
    service, _, _ = await stored_metrics()
    [latest, *_] = await service.get_all_metrics_stats(min_info=False)
    assert (latest.metrics_id, latest.collection_time, latest.time_to_live_millis) == (
        f"atlas_metrics_{3 * HOUR}@cl1",
        3 * HOUR,
        2 * HOUR,
    )
    assert latest.metrics is not None
    assert latest.metrics.metric("general", "entityCount") == 3
    assert not latest.guid.startswith("-")
    with pytest.raises(AtlasError) as again:
        await service.save_metrics(store_connected=True)
    with pytest.raises(AtlasError) as missing:
        await service.save_metrics_stat(AtlasMetricsStat())
    assert again.value.code is AtlasErrorCode.METRICSSTAT_ALREADY_EXISTS
    assert again.value.message == f"Metric Statistics already collected at {3 * HOUR}"
    assert (missing.value.code, missing.value.message) == (
        AtlasErrorCode.BAD_REQUEST,
        "MetricsStat definition missing.",
    )


@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsService.get_all_metrics_stats", rules=["MHS-02"])
@pytest.mark.covers(
    "aurelius_atlas_core.metrics_service.MetricsService.get_metrics_stat_by_collection_time", rules=["MHS-02"]
)
@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsService.metrics_stat_id", rules=["MHS-02"])
async def test__the_stored_metrics_are_listed_latest_first_and_read_by_time() -> None:
    """With ``min_info`` without their metrics; by a time stored, else not found."""
    service, _, _ = await stored_metrics()
    brief = await service.get_all_metrics_stats(min_info=True)
    found = await service.get_metrics_stat_by_collection_time(2 * HOUR)
    with pytest.raises(AtlasError) as unknown:
        await service.get_metrics_stat_by_collection_time(5)
    assert [stat.collection_time for stat in brief] == [3 * HOUR, 2 * HOUR, HOUR]
    assert {stat.metrics is None for stat in brief} == {True}
    assert (found.collection_time, found.metrics is not None) == (2 * HOUR, True)
    assert unknown.value.code is AtlasErrorCode.INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND
    assert service.metrics_stat_id(7) == "atlas_metrics_7@cl1"


@pytest.mark.covers(
    "aurelius_atlas_core.metrics_service.MetricsService.get_metrics_in_range_by_type_names", rules=["MHS-03"]
)
@pytest.mark.covers("aurelius_atlas_model.metrics.AtlasMetricsStat.of", rules=["MHS-03"])
async def test__a_range_answers_new_stats_with_the_type_data_of_its_type_names() -> None:
    """Both ends included, the latest first; each a new object: a negative GUID, no metrics, the asked types' counts."""
    service, _, _ = await stored_metrics()
    ranged = await service.get_metrics_in_range_by_type_names(2 * HOUR, 3 * HOUR, ["met_table", "nope"])
    plain = await service.get_metrics_in_range_by_type_names(0, 2 * HOUR, [])
    with pytest.raises(AtlasError) as reversed_range:
        await service.get_metrics_in_range_by_type_names(5, 5, [])
    assert [stat.collection_time for stat in ranged] == [3 * HOUR, 2 * HOUR]
    first = ranged[0].to_json()
    assert first["guid"].startswith("-")
    assert "metrics" not in first
    assert first["typeData"] == {
        "met_table": {"Active": 1, "Deleted": 1, "Shell": 0},
        "nope": {"Active": 0, "Deleted": 0, "Shell": 0},
    }
    assert [stat.collection_time for stat in plain] == [2 * HOUR, HOUR]
    assert {stat.type_data is None for stat in plain} == {True}
    assert reversed_range.value.code is AtlasErrorCode.INVALID_PARAMETERS
    assert reversed_range.value.message == "invalid parameters: startTime: '5', should be less than, endTime: '5'"


@pytest.mark.covers(
    "aurelius_atlas_core.metrics_service.MetricsService.get_metrics_for_chart_by_type_names", rules=["MHS-04"]
)
async def test__a_chart_pairs_each_states_counts_with_their_times_earliest_first() -> None:
    """Active, Deleted and Shell series per type; a range with no metrics has none."""
    service, _, _ = await stored_metrics()
    charts = await service.get_metrics_for_chart_by_type_names(HOUR, 2 * HOUR, ["met_view"])
    empty = await service.get_metrics_for_chart_by_type_names(10 * HOUR, 11 * HOUR, ["met_view"])
    assert [chart.to_json() for chart in charts["met_view"]] == [
        {"key": "Active", "values": [[HOUR, 1], [2 * HOUR, 1]]},
        {"key": "Deleted", "values": [[HOUR, 0], [2 * HOUR, 0]]},
        {"key": "Shell", "values": [[HOUR, 1], [2 * HOUR, 1]]},
    ]
    assert empty == {"met_view": []}
    assert await service.get_metrics_for_chart_by_type_names(HOUR, 2 * HOUR, []) == {}


@pytest.mark.covers("aurelius_atlas_core.metrics_service.MetricsService.purge_metrics_stats", rules=["MHS-05"])
async def test__the_metrics_past_their_time_to_live_are_purged() -> None:
    """Those collected more than the TTL ago are deleted, and so no longer listed; one of exactly the TTL stays."""
    service, now, _ = await stored_metrics()
    now[0] = 4 * HOUR / 1000
    purged = await service.purge_metrics_stats()
    assert [stat.collection_time for stat in purged] == [HOUR]
    assert [stat.collection_time for stat in await service.get_all_metrics_stats(min_info=True)] == [3 * HOUR, 2 * HOUR]
    assert await service.purge_metrics_stats() == []
