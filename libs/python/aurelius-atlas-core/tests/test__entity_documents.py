"""``ElasticsearchEntityDocuments`` (ENS-01, ENS-04, ENS-05, ENS-07, ENS-08, ENS-09) on the fake client."""

from decimal import Decimal
from typing import cast

import pytest
from aurelius_atlas_core import entity_documents
from aurelius_atlas_core.entity_documents import (
    ElasticsearchEntityDocuments,
    EntityDocuments,
    JournalEntry,
    Reservation,
)
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.typedef_document import DocumentVersion
from aurelius_atlas_model.instance import EntityStatus
from aurelius_atlas_store_es.testing.fake import FakeClient
from elasticsearch import AsyncElasticsearch

D = "aurelius_atlas_core.entity_documents"
E = f"{D}.ElasticsearchEntityDocuments"


@pytest.fixture
def fake() -> FakeClient:
    """An empty fake client."""
    return FakeClient()


@pytest.fixture
async def documents(fake: FakeClient) -> ElasticsearchEntityDocuments:
    """Prepared documents under the prefix ``t``."""
    documents = ElasticsearchEntityDocuments(cast("AsyncElasticsearch", fake), prefix="t")
    await documents.prepare()
    return documents


def entity(guid: str, **attributes: object) -> StoredEntity:
    """A stored ``table``."""
    return StoredEntity(guid=guid, type_name="table", attributes=attributes)


@pytest.mark.covers(f"{E}.prepare", f"{E}.aliases", rules=["ENS-01"])
async def test__three_aliases_are_created_once(fake: FakeClient) -> None:
    """An index behind each alias; a second prepare changes nothing."""
    documents = ElasticsearchEntityDocuments(cast("AsyncElasticsearch", fake))

    await documents.prepare()
    await documents.prepare()

    assert documents.aliases == (
        "aurelius-atlas-entities",
        "aurelius-atlas-unique-values",
        "aurelius-atlas-entity-journal",
    )
    assert fake.aliases == {alias: f"{alias}-000001" for alias in documents.aliases}


@pytest.mark.covers(f"{E}.write", f"{E}.get", rules=["ENS-04", "ENS-08"])
async def test__bulk_writes_create_or_replace_conditionally(documents: ElasticsearchEntityDocuments) -> None:
    """``create`` fails for an existing GUID, ``index`` for a stale version; decimals keep their digits."""
    first = await documents.write([(entity("a", **{"t.size": Decimal("1.10")}), None), (entity("b"), None)])
    read = await documents.get(["a", "b", "missing"])
    stale = DocumentVersion(read["a"].version.seq_no - 1, read["a"].version.primary_term)

    second = await documents.write(
        [(entity("a"), None), (entity("b", x=1), read["b"].version), (entity("a", y=2), stale)]
    )

    assert [(result.guid, result.written) for result in first] == [("a", True), ("b", True)]
    assert set(read) == {"a", "b"}
    assert str(read["a"].entity.attributes["t.size"]) == "1.10"
    assert [(result.written, result.conflict) for result in second] == [(False, True), (True, False), (False, True)]
    assert await documents.get([]) == {}


@pytest.mark.covers(f"{E}.restore", rules=["ENS-07"])
async def test__restore_puts_back_or_removes(documents: ElasticsearchEntityDocuments) -> None:
    """A state before is indexed again; an entity that did not exist is deleted, twice without error."""
    await documents.write([(entity("a", x=2), None), (entity("b"), None)])

    await documents.restore("a", entity("a", x=1))
    await documents.restore("b", None)
    await documents.restore("b", None)

    read = await documents.get(["a", "b"])
    assert set(read) == {"a"}
    assert read["a"].entity.attributes == {"x": 1}


@pytest.mark.covers(f"{E}.reserve", f"{E}.reservations", f"{E}.release", rules=["ENS-05"])
async def test__a_reservation_is_create_only_and_released_by_its_holder(
    documents: ElasticsearchEntityDocuments,
) -> None:
    """The second reservation of a key answers the holder; only the holder's GUID releases it."""
    first = Reservation("k", "a", "w1")

    assert await documents.reserve(first) is None
    assert await documents.reserve(Reservation("k", "b", "w2")) == first
    assert await documents.reservations(["k", "missing"]) == {"k": first}
    await documents.release("k", "b")
    assert await documents.reservations(["k"]) == {"k": first}
    await documents.release("k", "a")
    await documents.release("k", "a")
    assert await documents.reservations(["k"]) == {}
    assert await documents.reservations([]) == {}


@pytest.mark.covers(f"{E}.put_journal", f"{E}.journal", f"{E}.delete_journal", rules=["ENS-07"])
async def test__the_journal_holds_writes_in_flight(documents: ElasticsearchEntityDocuments, fake: FakeClient) -> None:
    """Entries are listed after a refresh and deleted by write id, twice without error."""
    entry = JournalEntry(write_id="w", lease_until=5, before={"a": None}, reserved=["k"])

    await documents.put_journal(entry)
    listed = await documents.journal()
    await documents.delete_journal("w")
    await documents.delete_journal("w")

    assert listed == [entry]
    assert listed[0].before_entity("a") is None
    assert await documents.journal() == []
    assert "t-entity-journal" in fake.refreshes


@pytest.mark.covers(f"{D}.JournalEntry.before_entity", rules=["ENS-07"])
def test__a_journal_entry_keeps_the_state_before() -> None:
    """``before`` holds an entity's JSON, or null for one the write created."""
    entry = JournalEntry(write_id="w", lease_until=0, before={"a": entity("a", x=1).to_json(), "b": None})

    assert entry.before_entity("a") == entity("a", x=1)
    assert entry.before_entity("b") is None


@pytest.mark.covers(f"{E}.count_type", rules=["ENS-09"])
async def test__entities_of_a_type_are_counted_after_a_refresh(
    documents: ElasticsearchEntityDocuments, fake: FakeClient
) -> None:
    """Exactly the type, any state (DD-048)."""
    deleted = entity("b").model_copy(update={"state": EntityStatus.DELETED})
    await documents.write([(entity("a"), None), (deleted, None)])

    assert await documents.count_type("table") == 2
    assert await documents.count_type("view") == 0
    assert fake.refreshes == ["t-entities", "t-entities"]


@pytest.mark.covers(
    *(
        f"{D}.EntityDocuments.{name}"
        for name in (
            "prepare",
            "get",
            "write",
            "restore",
            "reserve",
            "reservations",
            "release",
            "put_journal",
            "delete_journal",
            "journal",
            "count_type",
            "referring",
        )
    ),
    rules=["ENS-07"],
)
def test__both_implementations_are_entity_documents(documents: ElasticsearchEntityDocuments) -> None:
    """The store takes any ``EntityDocuments``: Elasticsearch in the server, memory in tests."""
    assert isinstance(documents, EntityDocuments)
    assert isinstance(MemoryEntityDocuments(), EntityDocuments)


@pytest.mark.covers(f"{E}.referring", f"{E}.write", f"{E}.prepare", rules=["EDL-09", "EDL-10"])
async def test__referring_entities_are_found_page_by_page_and_removals_are_bulk_deletes(
    documents: ElasticsearchEntityDocuments, fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a refresh, by ``references``, in pages; a removal is conditional; prepare maps new fields."""
    monkeypatch.setattr(entity_documents, "REFERRING_PAGE", 1)
    written = [
        entity("a").model_copy(update={"references": ["x"]}),
        entity("b").model_copy(update={"references": ["x", "y"]}),
        entity("c"),
    ]
    await documents.write([(item, None) for item in written])
    found = await documents.get(["c"])

    referring = await documents.referring(["x", "z"])
    removed = await documents.write([], [("c", found["c"].version), ("a", DocumentVersion(99, 1))])
    await documents.prepare()

    assert [item.entity.guid for item in referring] == ["a", "b"]
    assert await documents.referring([]) == []
    assert [(result.guid, result.written, result.conflict) for result in removed] == [
        ("c", True, False),
        ("a", False, True),
    ]
    assert set(await documents.get(["a", "c"])) == {"a"}
    assert "t-entities" in fake.refreshes
    assert fake.mapping_updates == ["t-entities"]
