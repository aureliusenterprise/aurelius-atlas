"""Lineage (LIN-02 to LIN-07) on the in-memory documents.

Read from ``EntityLineageService`` of Apache Atlas 2.4.0 (``getLineageInfoV2``, ``getLineageInfoOnDemand``) on the
lineage of its ``EntityLineageJerseyResourceIT``: ``sales_fact`` and ``time_dim`` load ``sales_daily``, which
loads ``sales_monthly``; on the base model's ``Process``, ``DataSet`` and their ``__Process.inputs`` and
``__Process.outputs`` relationships.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_core.entity_lineage_service import EntityLineageService
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_model.lineage import LineageDirection, LineageOnDemandConstraints
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

L = "aurelius_atlas_core.entity_lineage_service.EntityLineageService"
BASE_MODEL = Path(__file__).parent / "fixtures" / "0010-base_model.json"
GUIDS: dict[str, str] = {}
TYPES = {
    "entityDefs": [
        {"name": "hive_table", "superTypes": ["DataSet"]},
        {"name": "hive_process", "superTypes": ["Process"]},
        {"name": "hive_db", "superTypes": ["Asset"]},
    ]
}


def _ref(name: str) -> dict[str, str]:
    return {"typeName": "hive_table", "guid": f"-{name}"}


def _process(name: str, inputs: list[str], outputs: list[str]) -> dict[str, Any]:
    return {
        "typeName": "hive_process",
        "guid": f"-{name}",
        "attributes": {
            "qualifiedName": name,
            "name": name,
            "inputs": [_ref(table) for table in inputs],
            "outputs": [_ref(table) for table in outputs],
        },
    }


@pytest.fixture
async def store() -> EntityStore:
    """``sales_fact``, ``time_dim`` -> ``load_daily`` -> ``sales_daily`` -> ``load_monthly`` -> ``sales_monthly``."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(AtlasTypesDef.model_validate(json.loads(BASE_MODEL.read_text(encoding="utf-8"))))
        transient.add_types(AtlasTypesDef.model_validate(TYPES))
    found = EntityStore(registry, MemoryEntityDocuments())
    tables = ["sales_fact", "time_dim", "sales_daily", "sales_monthly"]
    entities = [
        *[{"typeName": "hive_table", "guid": f"-{t}", "attributes": {"qualifiedName": t, "name": t}} for t in tables],
        {"typeName": "hive_db", "guid": "-sales", "attributes": {"qualifiedName": "sales", "name": "sales"}},
        _process("load_daily", ["sales_fact", "time_dim"], ["sales_daily"]),
        _process("load_monthly", ["sales_daily"], ["sales_monthly"]),
    ]
    created = await EntityWriter(found).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": entities})
    )
    GUIDS.clear()
    GUIDS.update({key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()})
    return found


def names(info: dict[str, Any]) -> list[str]:
    """The names of the lineage's entities, sorted."""
    return sorted(header["attributes"]["name"] for header in info.get("guidEntityMap", {}).values())


def edges(info: dict[str, Any]) -> list[tuple[str, str]]:
    """The lineage's relations as name pairs, sorted."""
    by_guid = {guid: name for name, guid in GUIDS.items()}
    return sorted((by_guid[r["fromEntityId"]], by_guid[r["toEntityId"]]) for r in info.get("relations", []))


async def lineage(store: EntityStore, name: str, direction: LineageDirection, depth: int = 5) -> dict[str, Any]:
    """The lineage of the entity named ``name``, as JSON."""
    return (await EntityLineageService(store).get_atlas_lineage_info(GUIDS[name], direction, depth)).to_json()


@pytest.mark.covers(f"{L}.get_atlas_lineage_info", rules=["LIN-03", "LIN-04", "LIN-05"])
async def test__input_lineage_of_a_data_set(store: EntityStore) -> None:
    """``testInputLineageInfo``: 6 entities and 5 relations back from ``sales_monthly``."""
    info = await lineage(store, "sales_monthly", LineageDirection.INPUT)
    assert (info["baseEntityGuid"], info["lineageDirection"], info["lineageDepth"]) == (
        GUIDS["sales_monthly"],
        "INPUT",
        5,
    )
    assert names(info) == ["load_daily", "load_monthly", "sales_daily", "sales_fact", "sales_monthly", "time_dim"]
    assert edges(info) == [
        ("load_daily", "sales_daily"),
        ("load_monthly", "sales_monthly"),
        ("sales_daily", "load_monthly"),
        ("sales_fact", "load_daily"),
        ("time_dim", "load_daily"),
    ]
    assert info["relationsOnDemand"] == {}
    assert "visitedEdges" not in info
    assert "lineageOnDemandPayload" not in info


@pytest.mark.covers(f"{L}.get_atlas_lineage_info", rules=["LIN-03", "LIN-04"])
async def test__output_and_both_lineage(store: EntityStore) -> None:
    """``testOutputLineageInfo`` (5 entities, 4 relations from ``sales_fact``) and ``testLineageInfo`` (6, 5)."""
    output = await lineage(store, "sales_fact", LineageDirection.OUTPUT)
    both = await lineage(store, "sales_monthly", LineageDirection.BOTH)
    assert (len(names(output)), len(edges(output))) == (5, 4)
    assert (len(names(both)), len(edges(both))) == (6, 5)
    assert all(header.get("classifications") is None for header in output["guidEntityMap"].values())
    relation = output["relations"][0]
    assert relation["relationshipId"]


@pytest.mark.covers(f"{L}.get_atlas_lineage_info", rules=["LIN-03"])
@pytest.mark.parametrize(
    ("name", "direction", "depth", "expected"),
    [
        ("sales_monthly", LineageDirection.INPUT, 1, ["load_monthly", "sales_daily", "sales_monthly"]),
        (
            "sales_monthly",
            LineageDirection.INPUT,
            0,
            ["load_daily", "load_monthly", "sales_daily", "sales_fact", "sales_monthly", "time_dim"],
        ),
        (
            "sales_daily",
            LineageDirection.BOTH,
            1,
            ["load_daily", "load_monthly", "sales_daily", "sales_fact", "sales_monthly", "time_dim"],
        ),
        ("load_daily", LineageDirection.INPUT, 1, ["load_daily", "sales_fact", "time_dim"]),
        ("load_daily", LineageDirection.OUTPUT, 2, ["load_daily", "load_monthly", "sales_daily", "sales_monthly"]),
        ("load_daily", LineageDirection.OUTPUT, 1, ["load_daily", "sales_daily"]),
        ("sales_fact", LineageDirection.INPUT, 3, []),
    ],
)
async def test__depth_and_processes(
    store: EntityStore, name: str, direction: LineageDirection, depth: int, expected: list[str]
) -> None:
    """Each data set ``depth`` times (0 for all); a process starts one step on, with ``depth - 1``."""
    assert names(await lineage(store, name, direction, depth)) == expected


@pytest.mark.covers(f"{L}.get_atlas_lineage_info", rules=["LIN-04"])
async def test__no_edge_is_added_past_the_cap(store: EntityStore) -> None:
    """``lineageMaxNodeCountReached``: none once there are more relations than the cap."""
    service = EntityLineageService(store, max_node_count=1)
    info = (await service.get_atlas_lineage_info(GUIDS["sales_monthly"], LineageDirection.INPUT, 0)).to_json()
    assert len(info["relations"]) == 2


@pytest.mark.covers(f"{L}.get_atlas_lineage_info", rules=["LIN-02"])
async def test__lineage_is_of_data_sets_and_processes(store: EntityStore) -> None:
    """An unknown GUID, and an entity that is neither, fail."""
    with pytest.raises(AtlasError) as unknown:
        await EntityLineageService(store).get_atlas_lineage_info("nope", LineageDirection.BOTH, 3)
    with pytest.raises(AtlasError) as invalid:
        await lineage(store, "sales", LineageDirection.BOTH)
    assert unknown.value.code is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND
    assert invalid.value.code is AtlasErrorCode.INVALID_LINEAGE_ENTITY_TYPE
    assert str(invalid.value) == (
        f"Given instance guid {GUIDS['sales']} with type hive_db is not a valid lineage entity type."
    )


@pytest.mark.covers(f"{L}.get_atlas_lineage_info_on_demand", rules=["LIN-06"])
async def test__lineage_on_demand_must_be_enabled(store: EntityStore) -> None:
    """``LINEAGE_ON_DEMAND_NOT_ENABLED`` naming the property."""
    with pytest.raises(AtlasError) as raised:
        await EntityLineageService(store).get_atlas_lineage_info_on_demand(GUIDS["sales_daily"], None)
    assert raised.value.code is AtlasErrorCode.LINEAGE_ON_DEMAND_NOT_ENABLED
    assert str(raised.value) == "Lineage on demand config: atlas.lineage.on.demand.enabled is not enabled"


@pytest.mark.covers(f"{L}.get_atlas_lineage_info_on_demand", rules=["LIN-06", "LIN-07"])
async def test__lineage_on_demand_within_the_defaults(store: EntityStore) -> None:
    """Without constraints, the defaults: both ways, depth 3, the default count of relations each way."""
    service = EntityLineageService(store, on_demand_enabled=True)
    info = (await service.get_atlas_lineage_info_on_demand(GUIDS["sales_daily"], None)).to_json()
    assert names(info) == ["load_daily", "load_monthly", "sales_daily", "sales_fact", "sales_monthly", "time_dim"]
    assert info["relationsOnDemand"] == {}
    assert info["lineageOnDemandPayload"] == {
        GUIDS["sales_daily"]: {"direction": "BOTH", "inputRelationsLimit": 3, "outputRelationsLimit": 3, "depth": 3}
    }
    assert (info["lineageDirection"], info["lineageDepth"]) == ("BOTH", 3)


@pytest.mark.covers(f"{L}.get_atlas_lineage_info_on_demand", rules=["LIN-06", "LIN-07"])
async def test__lineage_on_demand_marks_entities_with_more(store: EntityStore) -> None:
    """A limit of one input relation at ``load_daily``: ``time_dim`` is left out and the process has more; its
    output to ``sales_daily`` counts as one of its outputs.
    """  # noqa: D205 - one sentence
    service = EntityLineageService(store, on_demand_enabled=True)
    constraints = {
        GUIDS["sales_monthly"]: LineageOnDemandConstraints(direction=LineageDirection.INPUT),
        GUIDS["load_daily"]: LineageOnDemandConstraints(input_relations_limit=1),
    }
    info = (await service.get_atlas_lineage_info_on_demand(GUIDS["sales_monthly"], constraints)).to_json()
    assert names(info) == ["load_daily", "load_monthly", "sales_daily", "sales_fact", "sales_monthly"]
    assert info["relationsOnDemand"] == {
        GUIDS["load_daily"]: {
            "hasMoreInputs": True,
            "hasMoreOutputs": False,
            "inputRelationsCount": 1,
            "outputRelationsCount": 1,
        }
    }
    payload = info["lineageOnDemandPayload"]
    assert payload[GUIDS["sales_monthly"]] == {
        "direction": "INPUT",
        "inputRelationsLimit": 3,
        "outputRelationsLimit": 3,
        "depth": 3,
    }


@pytest.mark.covers(f"{L}.get_atlas_lineage_info_on_demand", rules=["LIN-07"])
async def test__lineage_on_demand_from_a_process(store: EntityStore) -> None:
    """From ``load_daily`` outwards, its output first, then on; known by the two GUIDs of each edge."""
    service = EntityLineageService(store, on_demand_enabled=True)
    constraints = {GUIDS["load_daily"]: LineageOnDemandConstraints(direction=LineageDirection.OUTPUT, depth=2)}
    info = (await service.get_atlas_lineage_info_on_demand(GUIDS["load_daily"], constraints)).to_json()
    assert names(info) == ["load_daily", "load_monthly", "sales_daily", "sales_monthly"]
    assert edges(info) == [
        ("load_daily", "sales_daily"),
        ("load_monthly", "sales_monthly"),
        ("sales_daily", "load_monthly"),
    ]
