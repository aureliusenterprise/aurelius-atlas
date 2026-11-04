"""The metrics of ``admin/metrics`` (MET-01 to MET-04), on the in-memory documents.

Read from Apache Atlas 2.4.0's ``MetricsService#getMetrics``, ``AtlasMetricsUtil#getStats``, ``AtlasMetricsCounter``,
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
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
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
