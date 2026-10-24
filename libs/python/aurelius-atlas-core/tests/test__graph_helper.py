"""``graph_helper``: ``GraphHelper``'s edge lookups over stored relationships (REL-12, REL-14, REL-17, DD-065).

Read from ``GraphHelper`` (``getEdgeForLabel``, ``getEdgesForLabel``, ``getCollectionElementsUsingRelationship``,
``sortCollectionElements``, ``getRelationshipTypeName``) and ``EntityGraphRetriever#getReferencedEntityVertex`` of
Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.graph_helper import (
    collection_elements,
    edge_for_label,
    edges_for_label,
    other_end,
    referenced_end,
    relationship_type_name,
)
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.instance import RelationshipStatus
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.edge_direction import EdgeDirection

H = "aurelius_atlas_core.graph_helper"
REGISTRY = sample_registry(relationships=True)


def edge(guid: str, end1: str, end2: str, label: str = "l", **more: Any) -> StoredRelationship:  # noqa: ANN401
    """A relationship from ``end1`` to ``end2``."""
    return StoredRelationship(guid=guid, type_name="t", label=label, end1_guid=end1, end2_guid=end2, **more)


DELETED = RelationshipStatus.DELETED


@pytest.mark.covers(f"{H}.edges_for_label", f"{H}.edge_for_label", rules=["REL-12"])
def test__edges_are_found_by_label_and_direction_the_active_one_first() -> None:
    """``OUT`` from end 1, ``IN`` to end 2, ``BOTH`` either; else the latest updated deleted one, ties to the last."""
    edges = [
        edge("a", "x", "y", state=DELETED, update_time=5),
        edge("b", "y", "x"),
        edge("c", "x", "z", label="other"),
        edge("d", "x", "w", state=DELETED, update_time=5),
    ]

    assert [found.guid for found in edges_for_label("x", edges, "l", EdgeDirection.OUT)] == ["a", "d"]
    assert [found.guid for found in edges_for_label("x", edges, "l", EdgeDirection.IN)] == ["b"]
    assert [found.guid for found in edges_for_label("x", edges, "l", EdgeDirection.BOTH)] == ["a", "b", "d"]
    assert edge_for_label("x", edges, "l", EdgeDirection.BOTH) == edges[1]
    assert edge_for_label("x", edges, "l", EdgeDirection.OUT) == edges[3]
    assert edge_for_label("x", edges, "none", EdgeDirection.OUT) is None


@pytest.mark.covers(f"{H}.collection_elements", rules=["REL-14"])
def test__an_arrays_relationships_are_sorted_by_index_only_when_the_first_has_one() -> None:
    """A missing index counts as 0; a single attribute's are never sorted (DD-065)."""
    node = REGISTRY.entity_type("r_node")
    assert node is not None
    members = node.attribute("members")
    keeper = node.attribute("keeper")
    assert members is not None
    assert keeper is not None
    label = members.relationship_edge_label
    indexed = [edge("a", "n", "1", label, index=2), edge("b", "n", "2", label), edge("c", "n", "3", label, index=1)]
    unindexed = [edge("a", "n", "1", label), edge("b", "n", "2", label, index=0)]
    single = [
        edge("a", "n", "1", keeper.relationship_edge_label, index=2),
        edge("b", "n", "2", keeper.relationship_edge_label, index=1),
    ]

    assert [found.guid for found in collection_elements("n", indexed, members)] == ["b", "c", "a"]
    assert [found.guid for found in collection_elements("n", unindexed, members)] == ["a", "b"]
    assert [found.guid for found in collection_elements("n", single, keeper)] == ["a", "b"]


@pytest.mark.covers(f"{H}.relationship_type_name", rules=["REL-17"])
def test__an_attribute_of_several_relationship_types_takes_that_of_an_incoming_relationship() -> None:
    """The only type; else of the first relationship the entity is end 2 of; else the first."""
    registry = sample_registry(relationships=True)
    with registry.update() as transient:
        transient.add_types(
            AtlasTypesDef.model_validate(
                {
                    "relationshipDefs": [
                        {
                            "name": "r_keeper2",
                            "relationshipCategory": "ASSOCIATION",
                            "endDef1": {"type": "s_database", "name": "kept", "cardinality": "SET"},
                            "endDef2": {"type": "r_part", "name": "keeper", "cardinality": "SINGLE"},
                        }
                    ]
                }
            )
        )
    database = registry.entity_type("s_database")
    node = registry.entity_type("r_node")
    assert database is not None
    assert node is not None
    incoming = [edge("a", "d", "x"), StoredRelationship(guid="b", type_name="r_keeper2", end1_guid="p", end2_guid="d")]

    assert relationship_type_name("d", incoming, database, "kept") == "r_keeper2"
    assert relationship_type_name("d", [], database, "kept") == "r_keeper"
    assert relationship_type_name("n", [], node, "keeper") == "r_keeper"
    assert relationship_type_name("n", [], node, "nothing") is None


@pytest.mark.covers(f"{H}.referenced_end", f"{H}.other_end", rules=["REL-15", "REL-17"])
def test__the_referenced_end_follows_the_direction_and_the_other_end_is_end_2_unless_that_is_the_entity() -> None:
    """``getReferencedEntityVertex`` and ``mapVertexToObjectId``'s choice of vertex."""
    found = edge("a", "x", "y")

    assert referenced_end(found, EdgeDirection.OUT, "x") == "y"
    assert referenced_end(found, EdgeDirection.IN, "y") == "x"
    assert referenced_end(found, EdgeDirection.BOTH, "x") == "y"
    assert referenced_end(found, EdgeDirection.BOTH, "y") == "x"
    assert other_end(found, "x") == "y"
    assert other_end(found, "y") == "x"
    assert other_end(edge("s", "x", "x"), "x") == "x"
