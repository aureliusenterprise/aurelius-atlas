"""``ElasticsearchEntityDocuments`` (ENS-01, ENS-04, ENS-05, ENS-07, ENS-08, ENS-09) on the fake client."""

from decimal import Decimal
from typing import cast

import pytest
from aurelius_atlas_core import entity_documents
from aurelius_atlas_core.entity_documents import (
    ElasticsearchEntityDocuments,
    EntityDocuments,
    JournalEntry,
    Linked,
    LinkedKind,
    LinkedWrite,
    Reservation,
)
from aurelius_atlas_core.search_query import Criterion, Filter, Group, SearchQuery, Test, selects
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.typedef_document import DocumentVersion
from aurelius_atlas_model.discovery import Condition
from aurelius_atlas_model.instance import EntityStatus
from aurelius_atlas_model.tasks import TaskStatus
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


@pytest.mark.covers(f"{E}.prepare", f"{E}.aliases", rules=["ENS-01", "REL-05", "CLS-02", "TSK-02"])
async def test__six_aliases_are_created_once(fake: FakeClient) -> None:
    """An index behind each alias; a second prepare changes nothing."""
    documents = ElasticsearchEntityDocuments(cast("AsyncElasticsearch", fake))

    await documents.prepare()
    await documents.prepare()

    assert documents.aliases == (
        "aurelius-atlas-entities",
        "aurelius-atlas-unique-values",
        "aurelius-atlas-entity-journal",
        "aurelius-atlas-relationships",
        "aurelius-atlas-classifications",
        "aurelius-atlas-tasks",
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
            "classified",
            "list_tasks",
            "search",
            "classifications_of_types",
            "get_linked",
            "restore_linked",
            "count_linked_type",
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


@pytest.mark.covers(f"{E}.classified", rules=["PRO-07"])
async def test__classified_entities_are_found_by_their_listed_instances(
    documents: ElasticsearchEntityDocuments,
) -> None:
    """After a refresh, by ``classificationGuids``, as referring entities are found (DD-076)."""
    written = [
        entity("a").model_copy(update={"classification_guids": ["k"]}),
        entity("b").model_copy(update={"classification_guids": ["k", "m"]}),
        entity("c"),
    ]
    await documents.write([(item, None) for item in written])

    assert [item.entity.guid for item in await documents.classified(["k"])] == ["a", "b"]
    assert await documents.classified([]) == []


@pytest.mark.covers(f"{E}.list_tasks", rules=["TSK-04", "TSK-06"])
async def test__tasks_are_listed_oldest_first_all_or_open(
    documents: ElasticsearchEntityDocuments, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Oldest first, page by page; the open ones are ``PENDING`` or ``IN_PROGRESS``."""
    monkeypatch.setattr(entity_documents, "TASK_PAGE", 1)
    tasks = [
        StoredTask(guid="a", type="t", created_time=1, status=TaskStatus.IN_PROGRESS),
        StoredTask(guid="b", type="t", created_time=2),
        StoredTask(guid="c", type="t", created_time=3, status=TaskStatus.FAILED),
    ]
    await documents.write([], [], {LinkedKind.TASK: LinkedWrite([(task, None) for task in tasks])})

    every = [task.guid for task, _ in await documents.list_tasks(open_only=False)]
    waiting = [task.guid for task, _ in await documents.list_tasks(open_only=True)]

    assert (every, waiting) == (["a", "b", "c"], ["a", "b"])


@pytest.mark.covers(
    f"{E}.write",
    f"{E}.get_linked",
    f"{E}.restore_linked",
    f"{E}.count_linked_type",
    rules=["REL-05", "REL-08", "REL-10", "CLS-12"],
)
@pytest.mark.parametrize(
    ("kind", "document"),
    [
        (LinkedKind.RELATIONSHIP, StoredRelationship(guid="r", type_name="link", end1_guid="a", end2_guid="b")),
        (LinkedKind.CLASSIFICATION, StoredClassification(guid="r", type_name="link", entity_guid="a")),
    ],
)
async def test__linked_documents_are_written_with_entities_in_one_bulk_request(
    documents: ElasticsearchEntityDocuments, fake: FakeClient, kind: LinkedKind, document: Linked
) -> None:
    """All indices in one request, each result marked by kind; the documents are read, restored and counted."""
    results = await documents.write([(entity("a"), None)], [], {kind: LinkedWrite([(document, None)])})
    found = await documents.get_linked(kind, ["r", "nope"])
    removed = await documents.write([], [], {kind: LinkedWrite(removed=[("r", found["r"][1])])})
    await documents.restore_linked(kind, "r", document)
    await documents.restore_linked(kind, "s", None)

    assert [(result.guid, result.kind) for result in results] == [("a", None), ("r", kind)]
    assert list(found) == ["r"]
    assert [(result.guid, result.written) for result in removed] == [("r", True)]
    assert await documents.count_linked_type(kind, "link") == 1
    assert await documents.get_linked(kind, []) == {}
    await documents.restore_linked(kind, "r", None)
    assert await documents.count_linked_type(kind, "link") == 0
    assert f"t-{kind.value}" in fake.refreshes


def searchable(guid: str, created: int, **fields: object) -> StoredEntity:
    """A stored ``table`` with search fields."""
    base = {
        "keyword.__typeName": "table",
        "keyword.__state": "ACTIVE",
        "keyword.__guid": guid,
        "long.__timestamp": created,
    }
    return entity(guid).model_copy(update={"search": {**base, **fields}})


SEARCHED = [
    searchable("a", 3, **{"keyword.t.name": "alpha", "long.t.n": 1, "keyword.t.tags": ["x", "y"]}),
    searchable("b", 2, **{"keyword.t.name": "a*b", "long.t.n": 2, "keyword.__state": "DELETED"}),
    searchable("c", 1, **{"keyword.t.name": "", "keyword.t.tags": []}),
    entity("d").model_copy(update={"search": {"keyword.__typeName": "view", "long.__timestamp": 0}}),
]

CRITERIA = [
    Criterion("keyword.t.name", Test.EQ, "alpha"),
    Criterion("keyword.t.name", Test.NEQ, "alpha"),
    Criterion("long.t.n", Test.LT, 2),
    Criterion("long.t.n", Test.LTE, 2),
    Criterion("long.t.n", Test.GT, 1),
    Criterion("long.t.n", Test.GTE, 2),
    Criterion("long.t.n", Test.RANGE, 1, 1),
    Criterion("keyword.t.name", Test.STARTS_WITH, "al"),
    Criterion("keyword.t.name", Test.ENDS_WITH, "*b"),
    Criterion("keyword.t.name", Test.CONTAINS, "*"),
    Criterion("keyword.t.name", Test.NOT_CONTAINS, "lp"),
    Criterion("keyword.t.tags", Test.CONTAINS, "x", array=True),
    Criterion("keyword.t.tags", Test.NOT_CONTAINS, "x", array=True),
    Criterion("keyword.t.name", Test.IS_NULL),
    Criterion("long.t.n", Test.NOT_NULL),
    Criterion("keyword.t.name", Test.NOT_EMPTY),
    Criterion("long.t.n", Test.NOT_EMPTY),
    Criterion("long.t.n", Test.NOTHING),
    Criterion("long.t.n", Test.ANYTHING),
    Group(Condition.OR, (Criterion("long.t.n", Test.EQ, 1), Criterion("keyword.t.name", Test.EQ, ""))),
    Criterion("keyword.t.tags", Test.ANY_OF, frozenset({"y", "q"}), array=True),
    Criterion("long.t.n", Test.ANY_OF, frozenset({2}), array=False),
    Criterion("keyword.t.name", Test.MATCHES, "AL*"),
    Criterion("keyword.t.tags", Test.MATCHES, "X", array=True),
    Group(Condition.AND, (Criterion("long.t.n", Test.NOT_NULL), Criterion("keyword.t.name", Test.CONTAINS, "a"))),
]


@pytest.mark.covers(f"{E}.search", "aurelius_atlas_core.search_query.selects", rules=["SRC-05", "SRC-07"])
@pytest.mark.parametrize("criterion", CRITERIA)
async def test__a_search_query_selects_in_elasticsearch_what_it_selects_in_memory(
    documents: ElasticsearchEntityDocuments, criterion: Filter
) -> None:
    """Each test, translated to a query, finds the entities ``selects`` finds (DD-089)."""
    await documents.write([(item, None) for item in SEARCHED])
    query = SearchQuery(type_names=frozenset({"table"}), filter=criterion)

    found, total = await documents.search(query)

    expected = [
        item.guid
        for item in sorted(SEARCHED, key=lambda e: (e.search or {})["long.__timestamp"])
        if selects(query, item.search or {})
    ]
    assert ([item.guid for item in found], total) == (expected, len(expected))


@pytest.mark.covers(f"{E}.search", f"{E}.prepare", rules=["SRC-07"])
async def test__a_search_sorts_pages_counts_and_keeps_to_active_entities(
    documents: ElasticsearchEntityDocuments, fake: FakeClient
) -> None:
    """By a field descending, missing last; by creation without; a page of it with the total; all types."""
    await documents.write([(item, None) for item in SEARCHED])

    by_name, _ = await documents.search(SearchQuery(type_names=None, sort_field="keyword.t.name", descending=True))
    by_creation, _ = await documents.search(SearchQuery(type_names=frozenset({"table"})))
    page, total = await documents.search(SearchQuery(type_names=None, offset=1, size=2, active_only=True))
    await documents.prepare()

    assert [item.guid for item in by_name] == ["a", "b", "c", "d"]
    assert [item.guid for item in by_creation] == ["c", "b", "a"]
    assert ([item.guid for item in page], total) == (["a"], 2)
    assert "t-entities" in fake.settings_updates


@pytest.mark.covers(f"{E}.classifications_of_types", rules=["CSR-03"])
async def test__classification_instances_are_read_by_type_page_by_page(
    documents: ElasticsearchEntityDocuments, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Of the types given, or of every type (DD-090)."""
    monkeypatch.setattr(entity_documents, "CLASSIFICATION_PAGE", 1)
    instances = [
        StoredClassification(guid="k1", type_name="pii", entity_guid="a"),
        StoredClassification(guid="k2", type_name="secret", entity_guid="a"),
        StoredClassification(guid="k3", type_name="pii", entity_guid="b"),
    ]
    await documents.write([], [], {LinkedKind.CLASSIFICATION: LinkedWrite([(item, None) for item in instances])})

    piis = await documents.classifications_of_types(["pii"])
    every = await documents.classifications_of_types(None)

    assert [item.guid for item in piis] == ["k1", "k3"]
    assert [item.guid for item in every] == ["k1", "k2", "k3"]
