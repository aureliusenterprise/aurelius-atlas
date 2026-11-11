"""The tree: the legacy qualified-name rule and the entity graph (KSC-03, KSC-07).

The qualified-name pairs are fidelity tests: each expected name is what the legacy job wrote, so
a topic it registered is updated by this scanner rather than duplicated (KSC-07). The graph pairs
check the shape the one bulk request carries — temp guids and `relationshipAttributes` ends.
"""

import pytest
from aurelius_atlas_kafka_scanner.fields import FieldSpec
from aurelius_atlas_kafka_scanner.graph import (
    DEFAULT_CLUSTER,
    TopicTree,
    build_graph,
    dataset_qualified_name,
    default_cluster,
    entity_line,
    join_qualified,
    qualified_component,
)


@pytest.mark.covers("aurelius_atlas_kafka_scanner.graph.qualified_component", rules=["KSC-03"])
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Kafka Broker", "kafka-broker"),
        ("orders", "orders"),
        ("Orders.Event", "orders.event"),
        ("orders events", "orders-events"),
        ("orders  events", "orders-events"),
        ("orders&events", "ordersevents"),
        ("order-events", "orderevents"),
        ("orders*events", "orders*events"),
        ("orders/events", "orders/events"),
        ("ORDERS", "orders"),
        ("  both  sides  ", "-both-sides-"),
    ],
)
def test_the_qualified_name_rule_is_the_legacy_one(name: str, expected: str) -> None:
    """Lower, '&' and '-' removed, whitespace runs to a single '-' — in that order (KSC-03)."""
    assert qualified_component(name) == expected


@pytest.mark.covers("aurelius_atlas_kafka_scanner.graph.join_qualified", rules=["KSC-03"])
def test_components_join_on_a_double_hyphen_and_empty_ones_drop() -> None:
    """The legacy concatenation joins with '--' and skips an empty component (KSC-03)."""
    assert join_qualified("kafka-broker", "cluster-1", "orders") == "kafka-broker--cluster-1--orders"
    assert join_qualified("kafka-broker", "", "orders") == "kafka-broker--orders"
    assert join_qualified("solo") == "solo"


@pytest.mark.covers("aurelius_atlas_kafka_scanner.graph.default_cluster", rules=["KSC-03"])
def test_a_broker_with_no_cluster_id_becomes_the_named_fallback() -> None:
    """KSC-03: no cluster id is the collection named 'default-cluster', not an empty name."""
    assert default_cluster("Ur6ciV-TSa2kMg") == "Ur6ciV-TSa2kMg"
    assert default_cluster(None) == DEFAULT_CLUSTER
    assert default_cluster("") == DEFAULT_CLUSTER


@pytest.mark.covers("aurelius_atlas_kafka_scanner.graph.dataset_qualified_name", rules=["KSC-03"])
def test_a_dataset_name_hangs_under_the_system_and_collection() -> None:
    """The legacy shape: <system>--<collection>--<topic>, each part sanitized once (KSC-03)."""
    assert dataset_qualified_name("kafka-broker", "abc123", "orders") == "kafka-broker--abc123--orders"
    assert dataset_qualified_name("kafka-broker", None, "My Topic") == "kafka-broker--defaultcluster--my-topic"
    # the legacy rule eats a cluster id's own hyphens in the name it hangs, and keeps them nowhere else
    assert dataset_qualified_name("kafka-broker", "Ur6ciV-TSa2kMg", "orders") == "kafka-broker--ur6civtsa2kmg--orders"


@pytest.mark.covers("aurelius_atlas_kafka_scanner.graph.build_graph", rules=["KSC-03", "KSC-07"])
def test_the_graph_hangs_system_collection_datasets_and_fields() -> None:
    """One build: the System, one Collection, a Dataset per topic, the fields under their dataset (KSC-03)."""
    address = FieldSpec("address", "Address", children=(FieldSpec("city", "string"),))
    trees = [TopicTree("orders", (FieldSpec("id", "string"), address)), TopicTree("payments")]
    entities = build_graph(system_name="Kafka Broker", cluster_id="abc123", trees=trees)
    by_type: dict[str, list[str]] = {}
    for entity in entities:
        name = (entity.attributes or {})["qualifiedName"]
        by_type.setdefault(entity.type_name or "?", []).append(name)
    assert by_type["m4i_system"] == ["kafka-broker"]
    assert by_type["m4i_collection"] == ["kafka-broker--abc123"]
    assert by_type["m4i_dataset"] == ["kafka-broker--abc123--orders", "kafka-broker--abc123--payments"]
    assert by_type["m4i_field"] == [
        "kafka-broker--abc123--orders--id",
        "kafka-broker--abc123--orders--address",
        "kafka-broker--abc123--orders--address--city",
    ]


@pytest.mark.covers("aurelius_atlas_kafka_scanner.graph.build_graph", rules=["KSC-07"])
def test_every_entity_carries_a_distinct_temp_guid_and_ends_through_them() -> None:
    """DD-466: request-local temp guids, ends by guid — the webapp suite's idiom, one bulk request (KSC-07)."""
    entities = build_graph(
        system_name="Kafka Broker",
        cluster_id="abc123",
        trees=[TopicTree("orders", (FieldSpec("id", "string"),))],
    )
    guids = [entity.guid for entity in entities]
    assert len(set(guids)) == len(guids)
    assert all(guid and guid.startswith("-") for guid in guids)
    system, collection, dataset, field = entities
    assert collection.relationship_attributes == {
        "systems": [{"guid": system.guid, "typeName": "m4i_system"}],
        "datasets": [{"guid": dataset.guid, "typeName": "m4i_dataset"}],
    }
    assert dataset.relationship_attributes == {
        "collections": [{"guid": collection.guid, "typeName": "m4i_collection"}],
        "fields": [{"guid": field.guid, "typeName": "m4i_field"}],
    }
    assert field.relationship_attributes == {
        "datasets": [{"guid": dataset.guid, "typeName": "m4i_dataset"}],
    }


@pytest.mark.covers("aurelius_atlas_kafka_scanner.graph.build_graph", rules=["KSC-06", "KSC-07"])
def test_a_nested_field_names_its_parent_end_and_keeps_its_rendered_type() -> None:
    """A child field hangs parentField toward its parent and carries the rendered type (KSC-06, KSC-07)."""
    city = FieldSpec("city", "string")
    address = FieldSpec("address", "Address", definition="where", children=(city,))
    entities = build_graph(
        system_name="Kafka Broker",
        cluster_id="abc123",
        trees=[TopicTree("orders", (address,))],
    )
    parent, child = entities[3], entities[4]
    assert (parent.attributes or {})["fieldType"] == "Address"
    assert (parent.attributes or {})["definition"] == "where"
    assert (child.attributes or {})["qualifiedName"].endswith("--address--city")
    assert child.relationship_attributes == {
        "datasets": [{"guid": entities[2].guid, "typeName": "m4i_dataset"}],
        "parentField": [{"guid": parent.guid, "typeName": "m4i_field"}],
    }


@pytest.mark.covers("aurelius_atlas_kafka_scanner.graph.build_graph", rules=["KSC-05", "KSC-07"])
def test_a_topic_with_no_fields_still_becomes_a_dataset() -> None:
    """The field-less case registers the dataset alone — KSC-05's notice, never a dropped topic."""
    entities = build_graph(system_name="Kafka Broker", cluster_id="abc123", trees=[TopicTree("mystery")])
    assert [entity.type_name for entity in entities] == ["m4i_system", "m4i_collection", "m4i_dataset"]
    assert (entities[2].attributes or {})["name"] == "mystery"
    assert entities[2].relationship_attributes == {
        "collections": [{"guid": entities[1].guid, "typeName": "m4i_collection"}],
        "fields": [],
    }


@pytest.mark.covers("aurelius_atlas_kafka_scanner.graph.entity_line", rules=["KSC-08"])
def test_the_dry_run_line_names_the_type_and_the_qualified_name() -> None:
    """One line per entity, the dry run's whole output (KSC-08)."""
    entity = build_graph(system_name="Kafka Broker", cluster_id="abc", trees=[TopicTree("orders")])[2]
    assert entity_line(entity) == "m4i_dataset kafka-broker--abc--orders"
