"""The entity store against the dev Elasticsearch (ENS-01, ENS-05, ENS-07, ENS-08, ENS-09, MET-02)."""

import asyncio
from collections.abc import Mapping, Sequence
from decimal import Decimal

import pytest
from aurelius_atlas_core import entity_documents
from aurelius_atlas_core.entity_documents import (
    ElasticsearchEntityDocuments,
    LinkedKind,
    LinkedWrite,
    TypeCount,
    WriteResult,
)
from aurelius_atlas_core.entity_store import (
    LEASE_MILLISECONDS,
    EntityChange,
    EntityStore,
    UniqueValueTakenError,
)
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.typedef_document import DocumentVersion
from aurelius_atlas_model.instance import AtlasEntity, EntityStatus
from aurelius_atlas_model.typedef import AtlasAttributeDef, AtlasEntityDef, AtlasTypesDef
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_typesystem.registry import TypeRegistry

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

CRASH = "crash"


class CrashingDocuments(ElasticsearchEntityDocuments):
    """Dies right after its first bulk write, as a process killed part-way would."""

    async def write(
        self,
        items: Sequence[tuple[StoredEntity, DocumentVersion | None]],
        removed: Sequence[tuple[str, DocumentVersion]] = (),
        linked: Mapping[LinkedKind, LinkedWrite] | None = None,
    ) -> list[WriteResult]:
        """Write, then crash."""
        await super().write(items, removed, linked)
        raise RuntimeError(CRASH)


def registry() -> TypeRegistry:
    """``table`` with a unique ``qualifiedName`` and a ``bigdecimal`` size."""
    types = TypeRegistry()
    with types.update() as transient:
        transient.add_types(
            AtlasTypesDef(
                entity_defs=[
                    AtlasEntityDef(
                        name="table",
                        attribute_defs=[
                            AtlasAttributeDef(name="qualifiedName", type_name="string", is_unique=True),
                            AtlasAttributeDef(name="size", type_name="bigdecimal", is_optional=True),
                        ],
                    )
                ]
            )
        )
    return types


def table(store: EntityStore, **attributes: object) -> StoredEntity:
    """A new ``table``."""
    entity_type = store.registry.entity_type("table")
    assert entity_type is not None
    return StoredEntity.of(
        AtlasEntity(type_name="table", attributes=attributes),
        entity_type,
        guid=store.new_guid(),
        now=store.now(),
        user=None,
    )


async def opened(
    dev_store: ElasticsearchStore,
    prefix: str,
    documents: type[ElasticsearchEntityDocuments] = ElasticsearchEntityDocuments,
    **options: object,
) -> EntityStore:
    """A prepared store on the dev Elasticsearch under ``prefix``."""
    store = EntityStore(registry(), documents(dev_store.client, prefix), **options)  # type: ignore[arg-type]
    await store.prepare()
    return store


@pytest.mark.covers(rules=["ENS-01", "ENS-04", "ENS-09"])
async def test__an_entity_is_stored_and_read_back_exactly(dev_store: ElasticsearchStore, entity_prefix: str) -> None:
    """Three aliases; a decimal keeps its digits through Elasticsearch; the type is in use at once."""
    store = await opened(dev_store, entity_prefix)
    written = table(store, qualifiedName="t@e2e", size=Decimal("1.10"))

    await store.write([EntityChange(written)])
    found = await store.get(written.guid)

    assert all(
        [
            await dev_store.client.indices.exists_alias(name=f"{entity_prefix}-{name}")
            for name in ("entities", "unique-values", "entity-journal")
        ]
    )
    assert found is not None
    assert str(found.entity.attributes["table.size"]) == "1.10"
    assert await store.type_in_use("table")


@pytest.mark.covers(rules=["ENS-05"])
async def test__two_stores_racing_for_a_value_let_one_win(dev_store: ElasticsearchStore, entity_prefix: str) -> None:
    """The create-only reservation admits one writer of a unique value; the loser wrote nothing."""
    one, two = await opened(dev_store, entity_prefix), await opened(dev_store, entity_prefix)
    first, second = table(one, qualifiedName="race@e2e"), table(two, qualifiedName="race@e2e")

    outcomes = await asyncio.gather(
        one.write([EntityChange(first)]), two.write([EntityChange(second)]), return_exceptions=True
    )

    assert sorted(type(outcome).__name__ for outcome in outcomes) == ["NoneType", "UniqueValueTakenError"]
    assert sum([await one.get(first.guid) is not None, await one.get(second.guid) is not None]) == 1
    with pytest.raises(UniqueValueTakenError):
        await one.write([EntityChange(table(one, qualifiedName="race@e2e"))])


async def recovered(store: EntityStore, seconds: float = 5.0) -> int:
    """What ``recover`` undoes once the journal shows the entry: journal writes do not wait for a refresh (DD-247).

    The test moves its clock past the lease at once; a real lease outlasts the index's refresh by far.
    """
    deadline = asyncio.get_running_loop().time() + seconds
    found = await store.recover()
    while found == 0 and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.25)
        found = await store.recover()
    return found


@pytest.mark.covers(rules=["ENS-07", "ENS-08"])
async def test__a_write_cut_short_is_undone_by_another_process(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """A store dies after its bulk write; another, after the lease, restores the entity and frees the value."""
    clock = [1_000_000.0]
    crashing = await opened(dev_store, entity_prefix, CrashingDocuments, clock=lambda: clock[0])
    survivor = await opened(dev_store, entity_prefix, clock=lambda: clock[0])
    kept = table(survivor, qualifiedName="kept@e2e")
    await survivor.write([EntityChange(kept)])
    current = await survivor.get(kept.guid)
    assert current is not None
    renamed = current.entity.model_copy(update={"attributes": {"table.qualifiedName": "renamed@e2e"}})

    with pytest.raises(RuntimeError, match="crash"):
        await crashing.write(
            [EntityChange(renamed, current.version), EntityChange(table(crashing, qualifiedName="new@e2e"))]
        )
    clock[0] += LEASE_MILLISECONDS / 1000 + 1

    assert await recovered(survivor) == 1

    restored = await survivor.get(kept.guid)
    assert restored is not None
    assert restored.entity.attributes == {"table.qualifiedName": "kept@e2e"}
    await survivor.write([EntityChange(table(survivor, qualifiedName="new@e2e"))])
    await survivor.write([EntityChange(table(survivor, qualifiedName="renamed@e2e"))])


@pytest.mark.covers("aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.type_counts", rules=["MET-02"])
@pytest.mark.covers(
    "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.linked_type_counts", rules=["MET-02"]
)
async def test__the_entities_and_classifications_are_counted_by_type(
    dev_store: ElasticsearchStore, entity_prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A composite aggregation by type, state and shell flag, read page by page; classifications by type."""
    monkeypatch.setattr(entity_documents, "COUNT_PAGE", 1)
    store = await opened(dev_store, entity_prefix)
    active = table(store, qualifiedName="a@e2e")
    deleted = table(store, qualifiedName="d@e2e").model_copy(update={"state": EntityStatus.DELETED})
    shell = table(store, qualifiedName="s@e2e").model_copy(update={"is_incomplete": True})
    await store.write([EntityChange(active), EntityChange(deleted), EntityChange(shell)])
    await dev_store.client.index(
        index=f"{entity_prefix}-classifications", document={"guid": "c1", "typeName": "pii"}, refresh=True
    )

    assert sorted(await store.type_counts(), key=lambda found: (found.state, found.incomplete)) == [
        TypeCount("table", "ACTIVE", incomplete=False, count=1),
        TypeCount("table", "ACTIVE", incomplete=True, count=1),
        TypeCount("table", "DELETED", incomplete=False, count=1),
    ]
    assert await store.classification_type_counts() == {"pii": 1}
