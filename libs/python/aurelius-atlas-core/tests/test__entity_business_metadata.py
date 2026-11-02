"""Business attributes (BMD-02 to BMD-06, AUZ-17) on the in-memory documents.

Read from ``addOrUpdateBusinessAttributes``, ``removeBusinessAttributes`` and ``validateBusinessAttributes`` of
Apache Atlas 2.4.0's ``AtlasEntityStoreV2``, ``EntityGraphMapper``'s ``setBusinessAttributes``,
``addOrUpdateBusinessAttributes`` and ``removeBusinessAttributes``, ``EntityGraphRetriever#getBusinessMetadata`` and
``EntityAuditListenerV2#onBusinessAttributesUpdated``.
"""

import itertools
import json
from typing import Any

import pytest
from aurelius_atlas_core.authorization import AtlasPrivilege, Granted
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_business_metadata import EntityBusinessMetadata, business_metadata_headers
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.memory import InMemoryEntityAuditRepository, MemoryEntityDocuments
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

B = "aurelius_atlas_core.entity_business_metadata"
E = f"{B}.EntityBusinessMetadata"
UPDATE = EntityAuditActionV2.BUSINESS_ATTRIBUTE_UPDATE
ON_T = '["t"]'
TYPES = {
    "enumDefs": [{"name": "e", "elementDefs": [{"value": "A", "ordinal": 0}, {"value": "B", "ordinal": 1}]}],
    "entityDefs": [
        {"name": "t", "attributeDefs": [{"name": "qualifiedName", "typeName": "string", "isUnique": True}]},
        {"name": "u", "attributeDefs": []},
    ],
    "classificationDefs": [{"name": "c"}],
    "businessMetadataDefs": [
        {
            "name": "bm",
            "attributeDefs": [
                {
                    "name": "s",
                    "typeName": "string",
                    "isOptional": True,
                    "options": {"applicableEntityTypes": ON_T, "maxStrLength": "5"},
                },
                {"name": "n", "typeName": "int", "isOptional": True, "options": {"applicableEntityTypes": ON_T}},
                {
                    "name": "ns",
                    "typeName": "array<int>",
                    "isOptional": True,
                    "options": {"applicableEntityTypes": ON_T},
                },
                {"name": "es", "typeName": "array<e>", "isOptional": True, "options": {"applicableEntityTypes": ON_T}},
            ],
        },
        {
            "name": "req",
            "attributeDefs": [
                {"name": "m", "typeName": "int", "isOptional": False, "options": {"applicableEntityTypes": ON_T}}
            ],
        },
        {
            "name": "elsewhere",
            "attributeDefs": [
                {"name": "x", "typeName": "int", "isOptional": True, "options": {"applicableEntityTypes": '["u"]'}}
            ],
        },
    ],
}


@pytest.fixture
def audits() -> InMemoryEntityAuditRepository:
    """The events recorded."""
    return InMemoryEntityAuditRepository()


@pytest.fixture
def store() -> EntityStore:
    """A store of ``t`` with business metadata ``bm`` and ``req``, whose clock ticks a millisecond per reading."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(AtlasTypesDef.model_validate(TYPES))
    ticks = itertools.count(1000)
    return EntityStore(registry, MemoryEntityDocuments(), clock=lambda: next(ticks) / 1000)


def notifier(store: EntityStore, audits: InMemoryEntityAuditRepository) -> EntityChangeNotifier:
    """A notifier recording audit events."""
    return EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)])


def service(store: EntityStore, audits: InMemoryEntityAuditRepository, **more: Any) -> EntityBusinessMetadata:  # noqa: ANN401
    """Business attribute changes as ``u``, audited."""
    return EntityBusinessMetadata(store, user="u", notifier=notifier(store, audits), **more)


async def entity(store: EntityStore, audits: InMemoryEntityAuditRepository, **business: Any) -> str:  # noqa: ANN401
    """The GUID of a new ``t`` of these business attributes, created as ``c``."""
    body = {"typeName": "t", "guid": "-1", "attributes": {"qualifiedName": "q"}, "businessAttributes": business}
    writer = EntityWriter(store, user="c", notifier=notifier(store, audits))
    created = await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": [body]}))
    return (created.guid_assignments or {})["-1"]


async def read(store: EntityStore, guid: str) -> dict[str, Any] | None:
    """The entity's business attributes as a read answers them."""
    found = (await EntityRetriever(store).entity_with_ext_info(guid)).entity
    assert found is not None
    return found.to_json().get("businessAttributes")


def events(audits: InMemoryEntityAuditRepository) -> list[Any]:
    """The business attribute events' details, as JSON, in order."""
    prefix = "Updated business attributes: "
    return [json.loads((e.details or "").removeprefix(prefix)) for e in audits.events if e.action is UPDATE]


async def failure(call: Any) -> tuple[AtlasErrorCode, str]:  # noqa: ANN401 - a coroutine
    """The error code and message the call fails with."""
    with pytest.raises(AtlasError) as raised:
        await call
    return raised.value.code, raised.value.message


@pytest.mark.covers(
    "aurelius_atlas_core.entity_writer.EntityWriter.create_or_update",
    "aurelius_atlas_core.entity_retriever.EntityRetriever.business_attributes",
    f"{B}.add_or_update_business_attributes",
    "aurelius_atlas_core.entity_mapper.EntityMapper.set_value",
    "aurelius_atlas_core.entity_audit_listener.EntityAuditListener.on_business_attributes_updated",
    "aurelius_atlas_core.entity_change_notifier.EntityChangeListener.on_business_attributes_updated",
    "aurelius_atlas_core.entity_change_notifier.EntityChangeNotifier.on_business_attributes_updated",
    rules=["BMD-02", "BMD-06"],
)
async def test__an_entity_is_created_and_read_with_its_business_attributes(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """Those of its type with a value are kept, others left out; each business metadata audited before the create."""
    guid = await entity(store, audits, bm={"s": "a", "n": None, "z": 1}, elsewhere={"x": 1}, nope={"y": 2})

    assert await read(store, guid) == {"bm": {"s": "a"}}
    assert events(audits) == [{"typeName": "bm", "attributes": {"s": "a"}}]
    assert [event.action for event in audits.events] == [UPDATE, EntityAuditActionV2.ENTITY_CREATE]
    assert await read(store, await entity_without(store)) is None


async def entity_without(store: EntityStore) -> str:
    """A ``t`` without business attributes."""
    body = {"typeName": "t", "guid": "-1", "attributes": {"qualifiedName": "w"}}
    created = await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": [body]}))
    return (created.guid_assignments or {})["-1"]


@pytest.mark.covers(f"{E}.add_or_update_business_attributes", rules=["BMD-03", "BMD-06"])
async def test__business_attributes_are_added_and_updated(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """Given values set, others kept; a null sets the optional default; an unchanged value is not told."""
    guid = await entity(store, audits, bm={"s": "a"})
    changes = service(store, audits)
    audits.events.clear()

    await changes.add_or_update_business_attributes(guid, {"bm": {"n": 2}, "req": {"m": 1}})
    await changes.add_or_update_business_attributes(guid, {"bm": {"n": 2}})
    await changes.add_or_update_business_attributes(guid, {"bm": {"s": None}})

    assert await read(store, guid) == {"bm": {"n": 2}, "req": {"m": 1}}
    assert events(audits) == [
        {"typeName": "bm", "attributes": {"n": 2}},
        {"typeName": "req", "attributes": {"m": 1}},
        {"typeName": "bm", "attributes": {"s": None}},
    ]


@pytest.mark.covers(f"{E}.add_or_update_business_attributes", f"{B}.set_business_attributes", rules=["BMD-04"])
async def test__overwriting_replaces_every_business_attribute(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """Those not given are removed; the entity is written, at the request's time, even when nothing changes."""
    guid = await entity(store, audits, bm={"s": "a", "n": 1}, req={"m": 1})
    changes = service(store, audits)
    audits.events.clear()

    await changes.add_or_update_business_attributes(guid, {"bm": {"n": 3}, "req": {"m": 1}}, is_overwrite=True)
    before = await store.get(guid)
    await changes.add_or_update_business_attributes(guid, {"bm": {"n": 3}, "req": {"m": 1}}, is_overwrite=True)
    after = await store.get(guid)

    assert await read(store, guid) == {"bm": {"n": 3}, "req": {"m": 1}}
    assert events(audits) == [{"typeName": "bm", "attributes": {"s": None, "n": 3}}]
    assert before is not None
    assert after is not None
    assert after.entity.update_time > before.entity.update_time


@pytest.mark.covers(f"{E}.remove_business_attributes", rules=["BMD-05", "BMD-06"])
async def test__business_attributes_are_removed(store: EntityStore, audits: InMemoryEntityAuditRepository) -> None:
    """Those named, or every one of a business metadata named with none; each told as null."""
    guid = await entity(store, audits, bm={"s": "a", "n": 1}, req={"m": 1})
    changes = service(store, audits)
    audits.events.clear()

    await changes.remove_business_attributes(guid, {"bm": {"s": "ignored"}})
    assert await read(store, guid) == {"bm": {"n": 1}, "req": {"m": 1}}
    await changes.remove_business_attributes(guid, {"req": None, "nope": {}})

    assert await read(store, guid) == {"bm": {"n": 1}}
    assert events(audits) == [
        {"typeName": "bm", "attributes": {"s": None}},
        {"typeName": "req", "attributes": {"m": None}},
    ]


@pytest.mark.covers(
    f"{E}.add_or_update_business_attributes",
    f"{E}.remove_business_attributes",
    f"{B}.validate_business_attributes",
    rules=["BMD-03", "BMD-05"],
)
async def test__business_attributes_are_validated(store: EntityStore, audits: InMemoryEntityAuditRepository) -> None:
    """Every message at once; a missing GUID, body or entity fails first; nothing is written."""
    guid = await entity(store, audits)
    changes = service(store, audits)

    assert await failure(changes.add_or_update_business_attributes(guid, {})) == (
        AtlasErrorCode.INVALID_PARAMETERS,
        "invalid parameters: businessAttributes is null/empty",
    )
    assert (await failure(changes.remove_business_attributes("", {"bm": {}})))[0] is AtlasErrorCode.INVALID_PARAMETERS
    assert (await failure(changes.remove_business_attributes(guid, None)))[0] is AtlasErrorCode.INVALID_PARAMETERS
    assert (await failure(changes.add_or_update_business_attributes("x", {"bm": {}})))[0] is (
        AtlasErrorCode.INSTANCE_GUID_NOT_FOUND
    )
    code, message = await failure(
        changes.add_or_update_business_attributes(guid, {"bm": {"s": "toolong", "n": "x"}, "req": {}, "nope": {}})
    )
    assert code is AtlasErrorCode.INSTANCE_CRUD_INVALID_PARAMS
    assert "t.bm.s:  Business attribute-value exceeds maximum length limit" in message
    assert "t.bm.n" in message
    assert "t.req.m: mandatory business-metadata attribute value missing in type t" in message
    assert "nope: invalid business-metadata for entity type t" in message
    assert await read(store, guid) is None
    await changes.add_or_update_business_attributes(guid, {"req": {"m": 1}})
    await changes.add_or_update_business_attributes(guid, {"req": {}})
    overwrite = changes.add_or_update_business_attributes(guid, {"req": {}}, is_overwrite=True)
    assert (await failure(overwrite))[0] is AtlasErrorCode.INSTANCE_CRUD_INVALID_PARAMS


@pytest.mark.covers(f"{E}.add_or_update_business_attributes", f"{E}.remove_business_attributes", rules=["AUZ-17"])
async def test__each_business_metadata_changed_is_checked(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """Those whose values change, before validation; a removal checks each named; nothing is written when refused."""
    guid = await entity(store, audits, bm={"n": 1})
    reader = service(store, audits, authorizer=Granted("r", frozenset({AtlasPrivilege.ENTITY_READ})))
    refused = "r is not authorized to perform "

    assert await failure(reader.add_or_update_business_attributes(guid, {"bm": {"n": 1}, "req": {"m": "x"}})) == (
        AtlasErrorCode.UNAUTHORIZED_ACCESS,
        f"{refused}add/update business-metadata: guid={guid}, business-metadata-name=req",
    )
    assert (await failure(reader.remove_business_attributes(guid, {"nope": None})))[1] == (
        f"{refused}remove business-metadata: guid={guid}, business-metadata=nope"
    )
    await reader.add_or_update_business_attributes(guid, {"bm": {"n": 1}})
    assert await read(store, guid) == {"bm": {"n": 1}}


@pytest.mark.covers("aurelius_atlas_core.entity_writer.EntityWriter.create_or_update", rules=["BMD-06"])
async def test__each_created_entity_tells_its_classifications_then_its_business_attributes(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """As ``mapAttributesAndClassifications`` maps one created entity after the other, before their creates."""
    bodies = [
        {
            "typeName": "t",
            "guid": f"-{n}",
            "attributes": {"qualifiedName": f"q{n}"},
            "classifications": [{"typeName": "c"}],
            "businessAttributes": {"bm": {"n": n}},
        }
        for n in (1, 2)
    ]
    writer = EntityWriter(store, notifier=notifier(store, audits))
    created = await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": bodies}))
    first, second = ((created.guid_assignments or {})[f"-{n}"] for n in (1, 2))

    add, create = EntityAuditActionV2.CLASSIFICATION_ADD, EntityAuditActionV2.ENTITY_CREATE
    assert [(event.entity_id, event.action) for event in audits.events] == [
        (first, add),
        (first, UPDATE),
        (second, add),
        (second, UPDATE),
        (first, create),
        (second, create),
    ]


CSV = b"""EntityType,EntityUniqueAttributeValue,BusinessAttributeName,BusinessAttributeValue
t,q,bm.s,hello
t,q,bm.ns,1|x|3
t,q,bm.es,A|C
t,missing,bm.s,x
nope,q,bm.s,x
t,q,bm.zz,x
t,q,,x
t,q,bm.s,x,nope
t,w,req.m,abc
"""


@pytest.mark.covers(
    f"{E}.bulk_create_or_update_business_attributes",
    f"{B}.business_metadata_headers",
    rules=["BMI-01", "BMI-02", "BMI-03", "BMI-04", "BMI-05"],
)
async def test__business_attributes_are_imported_from_a_file(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """The rows that fail first, in order; then each entity overwritten with its stored and imported values."""
    guid = await entity(store, audits, bm={"n": 1})
    other = await entity_without(store)

    found = (await service(store, audits).bulk_create_or_update_business_attributes("bm.csv", CSV)).to_json()

    assert business_metadata_headers().startswith("EntityType,EntityUniqueAttributeValue,")
    *rows, failed = found["failedImportInfoList"]
    assert [(row["parentObjectName"], row["remarks"]) for row in rows] == [
        ("", "Provided value x is Integer of Long type at line #2"),
        ("", "Provided value C is Enumeration of Long type at line #3"),
        ("", "Line #5: no t entity found with qualifiedName=missing"),
        ("", "Line #6: invalid entity-type 'nope'"),
        ("", "Line #7: invalid business-metadata 'bm.zz' for entity type 't'"),
        ("", "Line #8: missing fields. [t, q, , x]"),
        ("", "Line #9: attribute 'nope' not found in entity-type 't'"),
    ]
    assert (failed["parentObjectName"], failed["childObjectName"], failed["importStatus"]) == (
        other,
        "{req={m=abc}}",
        "FAILED",
    )
    assert failed["remarks"].startswith("Invalid instance creation/updation parameters passed : [t.req.m")
    assert found["successImportInfoList"] == [
        {
            "parentObjectName": guid,
            "childObjectName": "{bm={n=1, s=hello, ns=[1, 3], es=[A]}}",
            "importStatus": "SUCCESS",
            "remarks": "",
        }
    ]
    assert await read(store, guid) == {"bm": {"s": "hello", "n": 1, "ns": [1, 3], "es": ["A"]}}
    with pytest.raises(AtlasError) as blank:
        await service(store, audits).bulk_create_or_update_business_attributes(" ", CSV)
    assert blank.value.code is AtlasErrorCode.FILE_NAME_NOT_FOUND
