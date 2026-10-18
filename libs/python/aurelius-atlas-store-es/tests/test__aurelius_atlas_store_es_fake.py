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
