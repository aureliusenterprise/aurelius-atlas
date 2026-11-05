"""The aging of the entity audits (AGE-01 to AGE-04), on the in-memory documents.

Read from Apache Atlas 2.4.0's ``AtlasAuditReductionService``, ``AuditReductionEntityRetrievalTask``,
``AuditReductionTask``, ``HBaseBasedAuditRepository#deleteEventsV2`` and its ``AtlasAuditReductionServiceTest`` and
``AuditReductionTaskTest``.
"""

import json
from typing import Any

import pytest
from aurelius_atlas_core.audit_reduction_service import AtlasAuditReductionService, AuditAgingConfig
from aurelius_atlas_core.audit_reduction_task import AUDIT_REDUCTION_ENTITY_RETRIEVAL, AuditReductionTask
from aurelius_atlas_core.entity_audit_repository import DAY_MILLISECONDS, delete_events_v2, events_to_age_out
from aurelius_atlas_core.entity_store import EntityStore, TaskChange
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.request_context import RequestContext, bound
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.testing.memory import (
    InMemoryEntityAuditRepository,
    MemoryEntityDocuments,
    MemoryTypedefDocument,
)
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from aurelius_atlas_model.audit_reduction import AtlasAuditAgingType, AuditReductionCriteria
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

A = EntityAuditActionV2
T = AtlasAuditAgingType
NOW = 100 * DAY_MILLISECONDS
BASE = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json").read_text(encoding="utf-8"))
TYPES = {
    "entityDefs": [
        {"name": "age_table", "superTypes": ["DataSet"]},
        {"name": "age_view", "superTypes": ["age_table"]},
        {"name": "age_file", "superTypes": ["DataSet"]},
    ]
}


def event(action: EntityAuditActionV2, days_ago: int, key: str, entity: str = "e") -> EntityAuditEventV2:
    """An event of the entity, ``days_ago`` before now."""
    return EntityAuditEventV2(
        entity_id=entity, action=action, timestamp=NOW - days_ago * DAY_MILLISECONDS, event_key=key
    )


EVENTS = [
    event(A.ENTITY_CREATE, 50, "c"),
    event(A.ENTITY_UPDATE, 40, "u1"),
    event(A.ENTITY_UPDATE, 30, "u2"),
    event(A.CLASSIFICATION_ADD, 20, "t1"),
    event(A.ENTITY_UPDATE, 10, "u3"),
    event(A.CLASSIFICATION_ADD, 1, "t2"),
]


def aged(
    actions: list[EntityAuditActionV2], count: int, ttl: int, aging: AtlasAuditAgingType, **more: bool
) -> set[str]:
    """The keys of the events of :data:`EVENTS` an aging removes."""
    found = events_to_age_out(
        EVENTS, actions, count, ttl, create_events_ageout_allowed=more.get("create", False), aging_type=aging, now=NOW
    )
    return {str(found_event.event_key) for found_event in found}


@pytest.mark.covers("aurelius_atlas_core.entity_audit_repository.events_to_age_out", rules=["AGE-04"])
def test__an_aging_removes_past_the_count_and_older_than_the_ttl() -> None:
    """The count of the newest kept, then the TTL; creations kept unless allowed; a sweep removes all it names."""
    assert aged([], 2, 0, T.DEFAULT) == {"u1", "u2", "t1"}
    assert aged([], 0, 25, T.DEFAULT) == {"u1", "u2"}
    assert aged([], 0, 25, T.DEFAULT, create=True) == {"c", "u1", "u2"}
    assert aged([], 0, 0, T.DEFAULT) == set()
    assert aged([A.ENTITY_UPDATE], 1, 0, T.CUSTOM) == {"u1", "u2"}  # by action, not across them
    assert aged([A.ENTITY_UPDATE, A.CLASSIFICATION_ADD], 1, 0, T.DEFAULT) == {"u1", "u2", "t1", "u3"}
    assert aged([A.CLASSIFICATION_ADD], 0, 0, T.SWEEP) == {"t1", "t2"}
    assert aged([A.ENTITY_UPDATE], 0, 35, T.CUSTOM) == {"u1"}


@pytest.mark.covers(
    "aurelius_atlas_core.entity_audit_repository.delete_events_v2",
    "aurelius_atlas_core.entity_audit_repository.EntityAuditRepository.delete_events",
    rules=["AGE-04"],
)
async def test__the_events_an_aging_names_are_deleted() -> None:
    """Only that entity's events, and only those the aging names."""
    repository = InMemoryEntityAuditRepository()
    await repository.put_events([*EVENTS, event(A.ENTITY_UPDATE, 90, "other", entity="f")])

    removed = await delete_events_v2(
        repository, "e", [], 2, 0, create_events_ageout_allowed=False, aging_type=T.DEFAULT, now=NOW
    )

    assert sorted(str(found.event_key) for found in removed) == ["t1", "u1", "u2"]
    assert sorted(str(found.event_key) for found in repository.events) == ["c", "other", "t2", "u3"]


def service(store: EntityStore, **config: Any) -> AtlasAuditReductionService:  # noqa: ANN401 - settings
    """The aging of the store under these settings."""
    return AtlasAuditReductionService(store, AuditAgingConfig(**config))


def by_type(found: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The aging criteria by aging type."""
    return {criteria["auditAgingType"]: criteria for criteria in found}


@pytest.mark.covers(
    "aurelius_atlas_core.audit_reduction_service.AtlasAuditReductionService.build_ageout_criteria",
    "aurelius_atlas_core.audit_reduction_service.AtlasAuditReductionService.criteria_of_config",
    rules=["AGE-01", "AGE-02"],
)
def test__the_criteria_make_a_sweep_a_custom_and_a_default_aging() -> None:
    """Each type and action left out of the agings after the one naming it; minimums kept; bad actions refused."""
    aging = service(EntityStore(TypeRegistry(), MemoryEntityDocuments()))
    criteria = AuditReductionCriteria.model_validate(
        {
            "auditAgingEnabled": True,
            "defaultAgeoutEnabled": True,
            "defaultAgeoutTTLInDays": 3,
            "defaultAgeoutAuditCount": 10,
            "customAgeoutTTLInDays": 30,
            "customAgeoutEntityTypes": "age_table, age_file",
            "auditSweepoutEnabled": True,
            "sweepoutEntityTypes": "age_file",
            "sweepoutActionTypes": "CLASSIFICATION_*",
        }
    )

    found = by_type(aging.build_ageout_criteria(criteria))

    assert found["SWEEP"]["entityTypes"] == ["age_file"]
    assert found["SWEEP"]["actionTypes"] == ["CLASSIFICATION_ADD", "CLASSIFICATION_DELETE", "CLASSIFICATION_UPDATE"]
    assert (found["CUSTOM"]["entityTypes"], found["CUSTOM"]["ttl"]) == (["age_table"], 30)
    assert (found["DEFAULT"]["ttl"], found["DEFAULT"]["auditCount"]) == (7, 50)  # the minimums kept
    assert found["DEFAULT"]["entityTypes"] == ["age_file", "age_table"]
    assert found["DEFAULT"]["actionTypes"] == []  # all actions
    assert aging.build_ageout_criteria(AuditReductionCriteria()) == []
    only_count = criteria.model_copy(update={"ignore_default_ageout_ttl": True, "default_ageout_audit_count": 0})
    assert "DEFAULT" not in by_type(aging.build_ageout_criteria(only_count))
    partial = AuditReductionCriteria.model_validate(
        {"auditAgingEnabled": True, "customAgeoutActionTypes": "ENTITY_UPDATE", "defaultAgeoutEnabled": True}
    )
    default = by_type(aging.build_ageout_criteria(partial))["DEFAULT"]
    assert "ENTITY_UPDATE" not in default["actionTypes"]  # a custom aging of no TTL or count is skipped
    with pytest.raises(AtlasError) as raised:
        aging.build_ageout_criteria(partial.model_copy(update={"custom_ageout_action_types": "NOPE"}))
    assert raised.value.message.endswith("EntityAuditActionV2.NOPE")

    configured = service(
        EntityStore(TypeRegistry(), MemoryEntityDocuments()),
        aging_enabled=True,
        default_ageout_ttl_in_days=1,
        custom_ageout_count=3,
        sweep_out_enabled=True,
        sweep_out_entity_types="x",
    ).criteria_of_config()
    assert (configured.default_ageout_ttl_in_days, configured.custom_ageout_audit_count) == (7, 50)
    assert configured.sweepout_entity_types == "x"


async def catalogue() -> tuple[EntityStore, dict[str, str]]:
    """A store of a table, a view and a file, and their GUIDs by type."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    for model in (BASE, TYPES):
        await types.create_types_def(AtlasTypesDef.model_validate(model))
    store = EntityStore(types.registry, MemoryEntityDocuments())
    body = {
        "entities": [
            {"typeName": name, "guid": f"-{n}", "attributes": {"qualifiedName": name, "name": name}}
            for n, name in enumerate(("age_table", "age_view", "age_file"), start=1)
        ]
    }
    created = (
        await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo.model_validate(body))
    ).guid_assignments
    guids = created or {}
    return store, {"age_table": guids["-1"], "age_view": guids["-2"], "age_file": guids["-3"]}


@pytest.mark.covers(
    "aurelius_atlas_core.audit_reduction_service.AtlasAuditReductionService.start_by_criteria",
    "aurelius_atlas_core.audit_reduction_service.AtlasAuditReductionService.start_by_config",
    rules=["AGE-03"],
)
async def test__each_aging_is_queued_as_a_task_of_the_user() -> None:
    """A pending task per aging, created by the request's user; past the pending limit none more is queued."""
    store, _ = await catalogue()
    aging = service(store, aging_enabled=True, max_pending_tasks=1)
    criteria = aging.build_ageout_criteria(aging.criteria_of_config())

    with bound(RequestContext(user="ann")):
        first = await aging.start_by_criteria(criteria)
    await aging.start_by_config()
    await aging.start_by_config()  # two pending: more than one is allowed no more

    assert [(task.type, task.created_by, task.status) for task in first] == [
        (AUDIT_REDUCTION_ENTITY_RETRIEVAL, "ann", "PENDING")
    ]
    assert first[0].parameters == criteria[0]
    assert len(await store.list_tasks(open_only=True)) == 2
    assert await service(store).start_by_config() == []  # aging off: nothing to queue


@pytest.mark.covers(
    "aurelius_atlas_core.audit_reduction_task.AuditReductionTask.eligible_guids",
    rules=["AGE-04"],
)
async def test__an_aging_finds_the_entities_of_its_types() -> None:
    """Named types with sub types, prefixes, the default aging's other types; unknown types find none."""
    store, guids = await catalogue()
    task = AuditReductionTask(store, InMemoryEntityAuditRepository())

    async def found(aging: AtlasAuditAgingType, types: list[str], *, subtypes: bool = True) -> set[str]:
        return set(await task.eligible_guids(aging, types, subtypes_included=subtypes))

    assert await found(T.CUSTOM, ["age_table"]) == {guids["age_table"], guids["age_view"]}
    assert await found(T.CUSTOM, ["age_table"], subtypes=False) == {guids["age_table"]}
    assert await found(T.SWEEP, ["age_f*"]) == {guids["age_file"]}
    assert await found(T.CUSTOM, ["nope"]) == set()
    assert await found(T.DEFAULT, ["age_table"]) >= {guids["age_file"]}
    assert guids["age_view"] not in await found(T.DEFAULT, ["age_table"])
    assert set(guids.values()) <= await found(T.DEFAULT, ["nope"])
    assert set(guids.values()) <= await found(T.CUSTOM, [])


@pytest.mark.covers(
    "aurelius_atlas_core.audit_reduction_task.AuditReductionTask.run",
    "aurelius_atlas_core.task_management.TaskManagement.run_pending",
    rules=["AGE-04"],
)
async def test__a_pending_aging_task_ages_out_the_audits_and_goes() -> None:
    """Run by the task management: the file's update audits swept, the table's kept; the task removed."""
    store, guids = await catalogue()
    audits = InMemoryEntityAuditRepository()
    now = store.now()
    await audits.put_events(
        [
            EntityAuditEventV2(entity_id=guids[name], action=A.ENTITY_UPDATE, timestamp=now, event_key=f"{name}:1")
            for name in ("age_table", "age_file")
        ]
    )
    sweep = by_type(
        service(store).build_ageout_criteria(
            AuditReductionCriteria.model_validate(
                {"auditAgingEnabled": True, "auditSweepoutEnabled": True, "sweepoutEntityTypes": "age_file"}
            )
        )
    )["SWEEP"]
    with bound(RequestContext(user="ann")):
        [queued] = await service(store).start_by_criteria([sweep])

    assert await TaskManagement(store, audits=audits).run_pending() == 1
    assert [str(found.event_key) for found in audits.events] == ["age_table:1"]
    assert await store.list_tasks() == []
    for broken in (StoredTask(guid="t1", type=queued.type or ""), StoredTask(guid="t2", type="x", parameters={"a": 1})):
        await store.write([], [], [], [TaskChange(broken)])
        with pytest.raises(ValueError, match="Unable to process task"):
            await AuditReductionTask(store, audits).run(broken, (await store.get_tasks([broken.guid]))[broken.guid][1])
    assert AtlasErrorCode.PENDING_TASKS_ALREADY_IN_PROGRESS.message(2) == "There are already 2 pending tasks in queue"
