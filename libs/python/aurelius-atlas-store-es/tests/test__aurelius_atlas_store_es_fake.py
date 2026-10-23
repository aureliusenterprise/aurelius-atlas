"""The fake client's documents behave as Elasticsearch's do for the calls the stores make (DD-007)."""

import pytest
from aurelius_atlas_store_es.testing.fake import FakeClient
from elasticsearch import ConflictError, NotFoundError


async def test__an_index_is_reached_through_its_alias() -> None:
    """``indices.create`` with aliases, then ``indices.exists_alias``."""
    fake = FakeClient()

    assert not await fake.indices.exists_alias(name="docs")
    assert (await fake.indices.create(index="docs-000001", aliases={"docs": {}}, mappings={}))["acknowledged"]
    assert await fake.indices.exists_alias(name="docs")
    assert fake.aliases == {"docs": "docs-000001"}


async def test__documents_are_read_with_their_sequence_number() -> None:
    """``index`` then ``get``; a missing document raises ``NotFoundError``; ``source=False`` leaves out the body."""
    fake = FakeClient()
    await fake.indices.create(index="docs-000001", aliases={"docs": {}})

    with pytest.raises(NotFoundError):
        await fake.get(index="docs", id="d")
    written = await fake.index(index="docs", id="d", document={"a": 1}, refresh=True)
    read = await fake.get(index="docs", id="d")
    bare = await fake.get(index="docs-000001", id="d", source=False)

    assert (written["_seq_no"], written["_primary_term"]) == (0, 1)
    assert read["_source"] == {"a": 1}
    assert read["_seq_no"] == bare["_seq_no"] == 0
    assert "_source" not in bare


async def test__conditional_writes_conflict_as_elasticsearch_does() -> None:
    """``op_type=create`` on an existing document, or a stale ``if_seq_no``, raises ``ConflictError``."""
    fake = FakeClient()
    first = await fake.index(index="docs", id="d", document={"v": 1}, op_type="create")

    with pytest.raises(ConflictError):
        await fake.index(index="docs", id="d", document={"v": 2}, op_type="create")
    second = await fake.index(index="docs", id="d", document={"v": 2}, if_seq_no=first["_seq_no"], if_primary_term=1)
    with pytest.raises(ConflictError):
        await fake.index(index="docs", id="d", document={"v": 3}, if_seq_no=first["_seq_no"], if_primary_term=1)
    with pytest.raises(ConflictError):
        await fake.index(index="docs", id="other", document={}, if_seq_no=0, if_primary_term=1)

    assert second["_seq_no"] == first["_seq_no"] + 1
    assert (await fake.get(index="docs", id="d"))["_source"] == {"v": 2}


async def test__a_bytes_body_is_read_with_decimal_floats() -> None:
    """``index`` with the codec's bytes keeps a float's digits, as the store's client reads them."""
    fake = FakeClient()

    await fake.index(index="docs", id="d", document=b'{"a": 1.10}')

    assert str((await fake.get(index="docs", id="d"))["_source"]["a"]) == "1.10"


async def test__mget_answers_each_id_found_or_not() -> None:
    """``_mget``: one entry per id, in order."""
    fake = FakeClient()
    await fake.index(index="docs", id="a", document={"x": 1})

    docs = (await fake.mget(index="docs", ids=["a", "b"]))["docs"]

    assert [(doc["_id"], doc["found"]) for doc in docs] == [("a", True), ("b", False)]
    assert docs[0]["_source"] == {"x": 1}


async def test__bulk_applies_each_action_with_its_own_outcome() -> None:
    """``create`` of an existing id and ``index`` over a stale version conflict; the others are written."""
    fake = FakeClient()
    first = await fake.index(index="docs", id="a", document={"v": 1})
    body = (
        b'{"create": {"_index": "docs", "_id": "a"}}\n{"v": 2}\n'
        b'{"create": {"_index": "docs", "_id": "b"}}\n{"v": 1.5}\n'
        + b'{"index": {"_index": "docs", "_id": "a", "if_seq_no": %d, "if_primary_term": 1}}\n{"v": 3}\n'
        % first["_seq_no"]
        + b'{"index": {"_index": "docs", "_id": "a", "if_seq_no": 99, "if_primary_term": 1}}\n{"v": 4}\n'
    )

    response = await fake.bulk(operations=body)

    assert [next(iter(item.values()))["status"] for item in response["items"]] == [409, 201, 201, 409]
    assert response["errors"]
    assert (await fake.get(index="docs", id="a"))["_source"] == {"v": 3}


async def test__delete_removes_a_document_guarded_by_its_version() -> None:
    """A missing document raises ``NotFoundError``; a stale ``if_seq_no`` raises ``ConflictError``."""
    fake = FakeClient()
    written = await fake.index(index="docs", id="d", document={})

    with pytest.raises(ConflictError):
        await fake.delete(index="docs", id="d", if_seq_no=written["_seq_no"] + 1, if_primary_term=1)
    assert (await fake.delete(index="docs", id="d", if_seq_no=written["_seq_no"], if_primary_term=1))[
        "result"
    ] == "deleted"
    with pytest.raises(NotFoundError):
        await fake.delete(index="docs", id="d")


async def test__search_and_count_answer_match_all_and_term_queries() -> None:
    """A ``term`` matches a value, or an element of a list value; ``match_all`` or no query matches everything."""
    fake = FakeClient()
    await fake.index(index="docs", id="a", document={"t": "x", "tags": ["p", "q"]})
    await fake.index(index="docs", id="b", document={"t": "y", "tags": []})

    everything = await fake.search(index="docs", size=1, query={"match_all": {}})
    by_tag = await fake.search(index="docs", query={"term": {"tags": "q"}})

    assert (everything["hits"]["total"]["value"], len(everything["hits"]["hits"])) == (2, 1)
    assert [hit["_id"] for hit in by_tag["hits"]["hits"]] == ["a"]
    assert (await fake.count(index="docs", query={"term": {"t": "y"}}))["count"] == 1
    assert (await fake.count(index="docs"))["count"] == 2


async def test__refresh_is_recorded() -> None:
    """The fake's documents are always visible; a refresh is only counted."""
    fake = FakeClient()

    await fake.indices.refresh(index="docs")

    assert fake.refreshes == ["docs"]


async def test__bulk_deletes_each_document_with_its_own_outcome() -> None:
    """A ``delete`` action has no source line; a stale version conflicts, a missing document is not found."""
    fake = FakeClient()
    written = await fake.index(index="docs", id="a", document={"v": 1})
    await fake.index(index="docs", id="b", document={"v": 1})
    body = (
        b'{"delete": {"_index": "docs", "_id": "a", "if_seq_no": %d, "if_primary_term": 1}}\n' % written["_seq_no"]
        + b'{"delete": {"_index": "docs", "_id": "b", "if_seq_no": 99, "if_primary_term": 1}}\n'
        + b'{"delete": {"_index": "docs", "_id": "c"}}\n'
        + b'{"create": {"_index": "docs", "_id": "d"}}\n{"v": 2}\n'
    )

    response = await fake.bulk(operations=body)

    assert [next(iter(item.values()))["status"] for item in response["items"]] == [200, 409, 404, 201]
    assert [doc["found"] for doc in (await fake.mget(index="docs", ids=["a", "b", "d"]))["docs"]] == [
        False,
        True,
        True,
    ]


async def test__search_pages_by_id_with_versions_and_matches_terms() -> None:
    """``terms`` matches any value; with ``sort``, hits come by id after ``search_after``, with their sort value."""
    fake = FakeClient()
    for document_id, tags in (("c", ["x"]), ("a", ["y", "x"]), ("b", ["z"]), ("d", "x")):
        await fake.index(index="docs", id=document_id, document={"tags": tags})

    first = await fake.search(
        index="docs", size=1, query={"terms": {"tags": ["x"]}}, sort=[{"guid": "asc"}], seq_no_primary_term=True
    )
    rest = await fake.search(
        index="docs", size=10, query={"terms": {"tags": ["x", "q"]}}, sort=[{"guid": "asc"}], search_after=["a"]
    )

    hit = first["hits"]["hits"][0]
    assert (hit["_id"], hit["sort"], hit["_primary_term"]) == ("a", ["a"], 1)
    assert "_seq_no" in hit
    assert [hit["_id"] for hit in rest["hits"]["hits"]] == ["c", "d"]


async def test__a_mapping_update_is_recorded() -> None:
    """The fake keeps no mappings; ``put_mapping`` is only counted."""
    fake = FakeClient()

    assert (await fake.indices.put_mapping(index="docs", properties={}))["acknowledged"]
    assert fake.mapping_updates == ["docs"]


async def test__bool_filters_and_ranges_match() -> None:
    """Every ``filter`` clause of a ``bool`` query must match; a ``range`` bounds a present value."""
    fake = FakeClient()
    for document_id, key in (("a", "k1"), ("b", "k2"), ("c", "k3"), ("d", None)):
        await fake.index(index="docs", id=document_id, document={"tag": "x", "key": key})

    found = await fake.search(
        index="docs",
        query={"bool": {"filter": [{"term": {"tag": "x"}}, {"range": {"key": {"lte": "k2", "gt": "k1"}}}]}},
    )
    above = await fake.search(index="docs", query={"range": {"key": {"gte": "k2", "lt": "k3"}}})

    assert [hit["_id"] for hit in found["hits"]["hits"]] == ["b"]
    assert [hit["_id"] for hit in above["hits"]["hits"]] == ["b"]


async def test__search_sorts_by_fields_in_either_direction() -> None:
    """Hits come by the sort fields, descending where asked, ties by the next field; ``search_after`` continues."""
    fake = FakeClient()
    for document_id, key, tie in (("a", "k1", "x"), ("b", "k3", "y"), ("c", "k2", "z"), ("d", "k3", "w")):
        await fake.index(index="docs", id=document_id, document={"key": key, "tie": tie})
    sort = [{"key": "desc"}, {"tie": "asc"}]

    first = await fake.search(index="docs", size=2, query={"match_all": {}}, sort=sort)
    rest = await fake.search(index="docs", size=5, query={"match_all": {}}, sort=sort, search_after=["k3", "y"])

    assert [hit["_id"] for hit in first["hits"]["hits"]] == ["d", "b"]
    assert first["hits"]["hits"][1]["sort"] == ["k3", "y"]
    assert [hit["_id"] for hit in rest["hits"]["hits"]] == ["c", "a"]
