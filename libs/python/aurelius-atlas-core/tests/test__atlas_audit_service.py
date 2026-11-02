"""The admin audits (ADA-01 to ADA-05), on the in-memory documents.

Read from Apache Atlas 2.4.0's ``AtlasAuditService``, ``AtlasAuditEntryDTO``, ``TypeDefAuditListener``,
``AdminResource#getAtlasAudits`` and ``#getAuditDetails``, and its ``AtlasAuditServiceTest`` and ``AdminResourceTest``.
"""

import json
import logging

import pytest
from aurelius_atlas_core.atlas_audit_service import AtlasAuditEntryDTO, AtlasAuditService, entry_of
from aurelius_atlas_core.authorization import AtlasPrivilege, Granted
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.request_context import RequestContext, bound, current, current_user
from aurelius_atlas_core.testing.memory import (
    InMemoryEntityAuditRepository,
    MemoryEntityDocuments,
    MemoryTypedefDocument,
)
from aurelius_atlas_core.typedef_audit_listener import TypeDefAuditListener
from aurelius_atlas_core.typedef_change_listener import ChangedTypeDefs
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.atlas_audit import AtlasAuditEntry, AuditOperation, AuditSearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntityWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

S = "aurelius_atlas_core.atlas_audit_service"
BASE = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json").read_text(encoding="utf-8"))
TABLE = {
    "entityDefs": [{"name": "ada_table", "superTypes": ["DataSet"]}],
    "enumDefs": [{"name": "ada_enum", "elementDefs": [{"value": "A", "ordinal": 1}]}],
}


async def catalogue(*, audited: bool = False) -> tuple[EntityStore, TypedefStore]:
    """An entity store of the base model; with ``audited``, the type changes after it audited."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    await types.create_types_def(AtlasTypesDef.model_validate(BASE))
    store = EntityStore(types.registry, MemoryEntityDocuments())
    if audited:
        types.change_listeners.append(TypeDefAuditListener(AtlasAuditService(store)))
    return store, types


async def search(store: EntityStore, **parameters: object) -> list[AtlasAuditEntry]:
    """The entries the search parameters find."""
    return await AtlasAuditService(store).get(AuditSearchParameters.model_validate(parameters))


def criterion(name: str, value: str, operator: str = "eq") -> dict[str, str]:
    """A filter criterion."""
    return {"attributeName": name, "operator": operator, "attributeValue": value}


@pytest.mark.covers(
    f"{S}.AtlasAuditService.add",
    f"{S}.AtlasAuditService.get",
    f"{S}.AtlasAuditEntryDTO.from_entity",
    f"{S}.AtlasAuditEntryDTO.to_entities",
    f"{S}.AtlasAuditEntryDTO.unique_attributes",
    f"{S}.entry_of",
    "aurelius_atlas_core.request_context.current",
    "aurelius_atlas_core.request_context.bound",
    "aurelius_atlas_core.request_context.current_user",
    rules=["ADA-01", "ADA-02", "ADA-04"],
)
async def test__an_entry_names_the_request_and_is_found_by_its_filters() -> None:
    """The bound request's user, client and start; this host without one; filters, order and page as asked."""
    store, _ = await catalogue()
    service = AtlasAuditService(store)
    with bound(RequestContext(user="ann", client_ip_address="10.0.0.1", request_time=1000)):
        assert current().user == "ann"
        await service.add(AuditOperation.PURGE, "[g]", "g", 1)
    await service.add(AuditOperation.SERVER_START, None, None, 0, start_time=5, end_time=6)
    assert current().user is None
    assert current_user()  # the process's login name, or atlas

    every = await search(store, sortBy="startTime", sortOrder="ASCENDING", limit=10)
    purges = await search(
        store, auditFilters={"condition": "AND", "criterion": [criterion("userName", "ann"), criterion("params", "")]}
    )

    assert [(e.operation, e.start_time) for e in every] == [
        (AuditOperation.SERVER_START, 5),
        (AuditOperation.PURGE, 1000),
    ]
    [purge] = purges
    assert (purge.user_name, purge.client_id, purge.params, purge.result, purge.result_count) == (
        "ann",
        "10.0.0.1",
        "[g]",
        "g",
        1,
    )
    assert (purge.end_time or 0) >= 1000
    assert ":" in str(every[0].client_id) or every[0].client_id == "unknown"
    assert purge.to_json()["operation"] == "PURGE"
    dto = AtlasAuditEntryDTO()
    [entity] = dto.to_entities(purge)
    assert dto.from_entity(AtlasEntityWithExtInfo(entity=entity)).result == "g"
    assert dto.unique_attributes(purge) == {}
    assert entry_of("g", {}).result_count == 0


@pytest.mark.covers(f"{S}.AtlasAuditService.get", f"{S}.AtlasAuditService.add", rules=["ADA-04"])
async def test__a_search_refuses_what_an_entry_lacks() -> None:
    """No parameters, a filter or an order on an attribute an entry lacks; a catalogue without the type keeps none."""
    store, _ = await catalogue()
    service = AtlasAuditService(store)
    for parameters, code in (
        (None, AtlasErrorCode.INVALID_PARAMETERS),
        (AuditSearchParameters(sort_by="nope"), AtlasErrorCode.UNKNOWN_ATTRIBUTE),
        (
            AuditSearchParameters.model_validate(
                {"auditFilters": {"condition": "OR", "criterion": [criterion("x", "1")]}}
            ),
            AtlasErrorCode.UNKNOWN_ATTRIBUTE,
        ),
    ):
        with pytest.raises(AtlasError) as raised:
            await service.get(parameters)
        assert raised.value.code is code
    assert raised.value.message == "Attribute x not found for type Atlas Audit Entry"
    await service.add(AuditOperation.PURGE, None, None, 0)
    hidden = AtlasAuditService(store, authorizer=Granted("u", frozenset()))
    assert await hidden.get(AuditSearchParameters()) == []  # scrubbed, so left out

    bare = EntityStore(TypeRegistry(), MemoryEntityDocuments())
    await AtlasAuditService(bare).add(AuditOperation.PURGE, None, None, 0)  # nothing to write into


@pytest.mark.covers(
    f"{S}.AtlasAuditService.details",
    "aurelius_atlas_model.atlas_audit.AuditOperation.to_entity_audit_action_v2",
    rules=["ADA-05"],
)
async def test__a_purge_audit_details_the_entities_it_purged() -> None:
    """Each purged GUID's purge event header, a page of them; any other operation is an internal error."""
    store, types = await catalogue()
    await types.create_types_def(AtlasTypesDef.model_validate(TABLE))
    repository = InMemoryEntityAuditRepository()
    writer = EntityWriter(store, notifier=EntityChangeNotifier(store, [EntityAuditListener(repository, store.now)]))
    body = {
        "entities": [
            {"typeName": "ada_table", "guid": f"-{n}", "attributes": {"qualifiedName": f"t{n}", "name": "t"}}
            for n in (1, 2, 3)
        ]
    }
    guids = list(
        ((await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate(body))).guid_assignments or {}).values()
    )
    await writer.delete_by_ids(guids)
    purged = await writer.purge_by_ids(guids)
    service = AtlasAuditService(store)
    await service.add(AuditOperation.PURGE, str(guids), purged.get_purged_entities_ids(), len(guids))
    await service.add(AuditOperation.EXPORT, None, "a,b", 2)
    await service.add(AuditOperation.SERVER_START, None, None, 0)
    entries = {entry.operation: entry for entry in await search(store)}

    page = await service.details(entries[AuditOperation.PURGE].guid, repository, 2, 1)
    beyond = await service.details(entries[AuditOperation.PURGE].guid, repository, 10, 9)
    empty = await service.details(entries[AuditOperation.SERVER_START].guid, repository, 10, 0)

    order = str(purged.get_purged_entities_ids()).split(",")
    assert [header.guid for header in page] == order[1:3]
    assert (beyond, empty) == ([], [])
    with pytest.raises(AtlasError) as raised:
        await service.details(entries[AuditOperation.EXPORT].guid, repository, 10, 0)
    assert (raised.value.code, raised.value.message) == (
        AtlasErrorCode.INTERNAL_ERROR,
        "Invalid operation for Entity Audit Event V2: EXPORT",
    )
    with pytest.raises(AtlasError) as refused:
        await AtlasAuditService(store, authorizer=Granted("u", frozenset())).details(
            entries[AuditOperation.PURGE].guid, repository, 1, 0
        )
    assert refused.value.code is AtlasErrorCode.UNAUTHORIZED_ACCESS
    reader = AtlasAuditService(store, authorizer=Granted("u", frozenset({AtlasPrivilege.ENTITY_READ})))
    assert len(await reader.details(entries[AuditOperation.PURGE].guid, repository, 10, 0)) == 3


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_audit_listener.TypeDefAuditListener.on_change",
    "aurelius_atlas_core.typedef_change_listener.ChangedTypeDefs.is_empty",
    "aurelius_atlas_core.typedef_store.TypedefStore.create_types_def",
    "aurelius_atlas_core.typedef_store.TypedefStore.update_types_def",
    "aurelius_atlas_core.typedef_store.TypedefStore.create_update_types_def",
    "aurelius_atlas_core.typedef_store.TypedefStore.delete_types_def",
    rules=["ADA-03"],
)
async def test__each_typedef_change_is_audited_by_kind() -> None:
    """Created, updated and deleted definitions, by kind; an update of a type created alongside is not one."""
    store, types = await catalogue(audited=True)

    await types.create_types_def(AtlasTypesDef.model_validate(TABLE))
    await types.update_types_def(
        AtlasTypesDef.model_validate(
            {"entityDefs": [{"name": "ada_table", "superTypes": ["DataSet"], "description": "d"}]}
        )
    )
    await types.create_update_types_def(AtlasTypesDef.model_validate({"entityDefs": [{"name": "ada_other"}]}))
    await types.create_update_types_def(AtlasTypesDef.model_validate({"entityDefs": [{"name": "ada_other"}]}))
    await types.delete_type_by_name("ada_enum")
    entries = await search(store, sortBy="startTime", limit=50)

    found = [(e.operation, e.params, e.result_count) for e in entries]
    assert (AuditOperation.TYPE_DEF_CREATE, "ENUM,ENTITY", 2) in found  # the kinds in the order they come
    assert (AuditOperation.TYPE_DEF_UPDATE, "ENTITY", 1) in found
    assert (AuditOperation.TYPE_DEF_CREATE, "ENTITY", 1) in found
    assert (AuditOperation.TYPE_DEF_DELETE, "ENUM", 1) in found
    assert len(found) == 5  # the second create-or-update of ada_other updates it
    created = next(e for e in entries if e.operation is AuditOperation.TYPE_DEF_CREATE and e.result_count == 2)
    assert {d["name"] for d in json.loads(created.result or "{}")["ENTITY"]} == {"ada_table"}
    listener = TypeDefAuditListener(AtlasAuditService(store))
    table = types.registry.typedef_by_name("ada_table")
    assert table is not None
    await listener.on_change(ChangedTypeDefs(created=[table], updated=[table, table]))
    assert len(await search(store, limit=50)) == 6  # only the creation


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_store.TypedefStore.apply_patch",
    "aurelius_atlas_core.typedef_change_listener.TypeDefChangeListener.on_change",
    rules=["ADA-03"],
)
async def test__a_failing_listener_does_not_fail_the_change(caplog: pytest.LogCaptureFixture) -> None:
    """Atlas logs a listener's failure; the change stands."""

    class Failing:
        async def on_change(self, changed: ChangedTypeDefs) -> None:
            raise RuntimeError(changed)

    _, types = await catalogue()
    types.change_listeners.append(Failing())
    with caplog.at_level(logging.ERROR):
        await types.create_types_def(AtlasTypesDef.model_validate(TABLE))
    assert types.registry.typedef_by_name("ada_table") is not None
    assert "OnChange failed for listener Failing" in caplog.text
