"""``WriteStore``: the store contract the write path is typed against (WRS-01, WRS-02, DD-773, DD-774).

``EntityWriter`` and the internals it drives take the contract, not ``EntityStore``, so a test can drive a write
against a store that carries nothing past the contract's members. ``EntityStore`` is the contract's only
production implementation, and it satisfies it unchanged.
"""

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from aurelius_atlas_core.entity_store import (
    ClassificationChange,
    EntityChange,
    EntityStore,
    RelationshipChange,
    TaskChange,
    WriteStore,
)
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.search_query import SearchHits, SearchQuery
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.typedef_document import DocumentVersion
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, EntityStatus
from aurelius_atlas_typesystem.entity_type import EntityType

W = "aurelius_atlas_core.entity_store.WriteStore"
NOW = 5000


class OnlyContract:
    """A store exposing exactly the ``WriteStore`` members, each delegated to ``real``.

    Nothing more: the writer and its internals cannot read past the contract through this store, because this
    store has nothing past it.
    """

    def __init__(self, real: EntityStore) -> None:
        self.registry = real.registry
        self.task_listeners = real.task_listeners
        self.write_listeners = real.write_listeners
        self._real = real

    def new_guid(self) -> Any:  # noqa: ANN401 - the store's AssignedGuid
        """The real store's minted GUID."""
        return self._real.new_guid()

    def now(self) -> int:
        """The real store's time."""
        return self._real.now()

    async def get(self, guid: str) -> Any:  # noqa: ANN401 - the store's VersionedEntity
        """The real store's entity."""
        return await self._real.get(guid)

    async def get_many(self, guids: Sequence[str]) -> dict[str, Any]:
        """The real store's entities."""
        return await self._real.get_many(guids)

    async def find_by_unique_attributes(self, entity_type: EntityType, values: Mapping[str, Any]) -> Any:  # noqa: ANN401 - the store's VersionedEntity
        """The real store's holder."""
        return await self._real.find_by_unique_attributes(entity_type, values)

    async def referring(self, guids: Sequence[str]) -> list[Any]:
        """The real store's referrers."""
        return await self._real.referring(guids)

    async def classified(self, guids: Sequence[str]) -> list[Any]:
        """The real store's classified entities."""
        return await self._real.classified(guids)

    async def get_relationships(self, guids: Sequence[str]) -> dict[str, Any]:
        """The real store's relationships."""
        return await self._real.get_relationships(guids)

    async def get_classifications(self, guids: Sequence[str]) -> dict[str, Any]:
        """The real store's classification instances."""
        return await self._real.get_classifications(guids)

    async def list_tasks(self, *, open_only: bool = False) -> list[tuple[StoredTask, DocumentVersion]]:
        """The real store's tasks."""
        return await self._real.list_tasks(open_only=open_only)

    async def search(self, query: SearchQuery) -> SearchHits:
        """The real store's search."""
        return await self._real.search(query)

    async def write(
        self,
        changes: Sequence[EntityChange],
        relationship_changes: Sequence[RelationshipChange] = (),
        classification_changes: Sequence[ClassificationChange] = (),
        task_changes: Sequence[TaskChange] = (),
    ) -> None:
        """The real store's write."""
        await self._real.write(changes, relationship_changes, classification_changes, task_changes)


def store() -> EntityStore:
    """A store of the sample write types over the in-memory documents (WRS-02: no server)."""
    return EntityStore(sample_registry(writes=True), MemoryEntityDocuments(), clock=lambda: NOW / 1000)


def as_json(value: Any) -> Any:  # noqa: ANN401 - Atlas JSON
    """A model's JSON as a client reads it."""
    return codec.loads(codec.dumps(value.to_json()))


def one(qualified_name: str) -> AtlasEntitiesWithExtInfo:
    """A create request of one database as Atlas JSON."""
    return AtlasEntitiesWithExtInfo.model_validate(
        {
            "entities": [
                {
                    "typeName": "s_database",
                    "guid": "-1",
                    "attributes": {"qualifiedName": qualified_name, "title": "First"},
                }
            ]
        }
    )


@pytest.mark.covers(f"{W}.write", rules=["WRS-01", "WRS-02"])
async def test__the_concrete_store_and_a_contract_only_store_satisfy_the_contract() -> None:
    """``EntityStore`` satisfies ``WriteStore`` unchanged, and a hand-built contract store does too (DD-773)."""
    real = store()
    assert isinstance(real, WriteStore)
    assert isinstance(OnlyContract(real), WriteStore)


@pytest.mark.covers(f"{W}.write", rules=["WRS-01"])
async def test__the_writer_creates_through_the_contract_alone() -> None:
    """A create runs against a store that carries nothing past the contract, and lands in the store behind it."""
    real = store()
    answer = as_json(await EntityWriter(OnlyContract(real), user="u").create_or_update(one("db@contract")))
    guid = answer["guidAssignments"]["-1"]
    assert [header["guid"] for header in answer["mutatedEntities"]["CREATE"]] == [guid]
    stored = await real.get(guid)
    assert stored is not None
    assert stored.entity.type_name == "s_database"


@pytest.mark.covers(f"{W}.write", rules=["WRS-01"])
async def test__the_writer_deletes_through_the_contract_alone() -> None:
    """The delete path reaches the store's ``referring`` and its listeners, all of which the contract names."""
    real = store()
    contract = OnlyContract(real)
    answer = as_json(await EntityWriter(contract).create_or_update(one("db@contract-del")))
    guid = answer["guidAssignments"]["-1"]
    heard: list[str] = []
    real.write_listeners.append(lambda: heard.append("write"))
    deleted = as_json(await EntityWriter(contract, user="u").delete_by_id(guid))
    assert len(deleted["mutatedEntities"]["DELETE"]) == 1
    assert heard
    found = await real.get(guid)
    assert found is not None
    assert found.entity.state is EntityStatus.DELETED
