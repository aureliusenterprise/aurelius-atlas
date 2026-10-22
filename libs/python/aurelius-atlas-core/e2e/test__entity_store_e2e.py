"""The entity store against the dev Elasticsearch (ENS-01, ENS-05, ENS-07, ENS-08, ENS-09)."""

import asyncio
from collections.abc import Sequence
from decimal import Decimal

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments, WriteResult
from aurelius_atlas_core.entity_store import (
    LEASE_MILLISECONDS,
    EntityChange,
    EntityStore,
    UniqueValueTakenError,
)
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.typedef_document import DocumentVersion
from aurelius_atlas_model.instance import AtlasEntity
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
        relationships: Sequence[tuple[StoredRelationship, DocumentVersion | None]] = (),
        removed_relationships: Sequence[tuple[str, DocumentVersion]] = (),
    ) -> list[WriteResult]:
        """Write, then crash."""
        await super().write(items, removed, relationships, removed_relationships)
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

    assert await survivor.recover() == 1

    restored = await survivor.get(kept.guid)
    assert restored is not None
    assert restored.entity.attributes == {"table.qualifiedName": "kept@e2e"}
    await survivor.write([EntityChange(table(survivor, qualifiedName="new@e2e"))])
    await survivor.write([EntityChange(table(survivor, qualifiedName="renamed@e2e"))])
