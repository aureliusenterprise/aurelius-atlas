import json
import time
from uuid import UUID

import pytest
from aurelius_example import Entity
from confluent_kafka import Consumer, Producer
from confluent_kafka.serialization import MessageField, SerializationContext, Serializer
from sqlmodel import Session
from tenacity import retry, stop_after_attempt, wait_fixed


def produce_message(  # noqa: PLR0917
    entity: Entity | None,
    guid: UUID,
    kafka_producer: Producer,
    kafka_topic: str,
    key_serializer: Serializer,
    value_serializer: Serializer,
) -> None:
    """Produce a message to the Kafka topic."""
    headers = {}

    key = key_serializer(
        str(guid),
        SerializationContext(
            field=MessageField.KEY,
            headers=headers,
            topic=kafka_topic,
        ),
    )

    value = value_serializer(
        entity.model_dump(mode="json") if entity else None,
        SerializationContext(
            field=MessageField.VALUE,
            headers=headers,
            topic=kafka_topic,
        ),
    )

    kafka_producer.produce(
        topic=kafka_topic,
        key=key,
        value=value,
        headers=headers,
    )

    kafka_producer.flush()


@retry(stop=stop_after_attempt(15), wait=wait_fixed(5))
def assert_entity_in_database(
    expected: Entity,
    session: Session,
) -> None:
    """Assert that the entity exists in the database."""
    actual = session.get(Entity, expected.guid)
    assert actual == expected, f"Expected {expected} but got {actual}"


@retry(stop=stop_after_attempt(15), wait=wait_fixed(5))
def assert_entity_not_in_database(
    primary_key: UUID,
    session: Session,
) -> None:
    """Assert that the entity does not exist in the database."""
    actual = session.get(Entity, primary_key)
    assert actual is None, f"Expected {primary_key} to be deleted but got {actual}"


@pytest.mark.parametrize(
    ("entity", "value_serializer_name"),
    [
        (Entity(), "value_serializer_with_header_schema_id"),
        (Entity(), "value_serializer_with_prefix_schema_id"),
        (Entity(name="Hello World", description="This is a test"), "value_serializer_with_header_schema_id"),
        (Entity(name="Hello World", description="This is a test"), "value_serializer_with_prefix_schema_id"),
    ],
)
def test__aurelius_kafka_connect_jdbc_sink_example_handles_messages(  # noqa: PLR0917
    entity: Entity,
    kafka_producer: Producer,
    kafka_topic: str,
    key_serializer: Serializer,
    value_serializer_name: str,
    request: pytest.FixtureRequest,
    session: Session,
) -> None:
    """
    Test that messages are correctly processed by the Kafka Connect JDBC Sink.

    Asserts:
        - The entity retrieved from the database matches the expected entity.
    """
    value_serializer: Serializer = request.getfixturevalue(value_serializer_name)

    produce_message(
        entity=entity,
        guid=entity.guid,
        kafka_producer=kafka_producer,
        kafka_topic=kafka_topic,
        key_serializer=key_serializer,
        value_serializer=value_serializer,
    )

    assert_entity_in_database(expected=entity, session=session)


@pytest.mark.parametrize(
    ("entity", "value_serializer_name"),
    [
        (Entity(name="To Be Deleted"), "value_serializer_with_header_schema_id"),
        (Entity(name="To Be Deleted"), "value_serializer_with_prefix_schema_id"),
    ],
)
def test__aurelius_kafka_connect_jdbc_sink_example_handles_tombstone_messages(  # noqa: PLR0917
    entity: Entity,
    kafka_producer: Producer,
    kafka_topic: str,
    key_serializer: Serializer,
    value_serializer_name: str,
    request: pytest.FixtureRequest,
    session: Session,
) -> None:
    """
    Test that tombstone messages are correctly processed by the Kafka Connect JDBC Sink.

    First, produce a message to create the entity, then produce a tombstone message to delete it.

    Asserts:
        - The entity is deleted from the database.
    """
    value_serializer: Serializer = request.getfixturevalue(value_serializer_name)

    produce_message(
        entity=entity,
        guid=entity.guid,
        kafka_producer=kafka_producer,
        kafka_topic=kafka_topic,
        key_serializer=key_serializer,
        value_serializer=value_serializer,
    )

    assert_entity_in_database(expected=entity, session=session)

    produce_message(
        entity=None,
        guid=entity.guid,
        kafka_producer=kafka_producer,
        kafka_topic=kafka_topic,
        key_serializer=key_serializer,
        value_serializer=value_serializer,
    )

    assert_entity_not_in_database(primary_key=entity.guid, session=session)


# The job identity the native Debezium OpenLineage integration stamps on its
# events. OpenMetadata's OpenLineage connector derives the pipeline as
# "{namespace}-{name}" and looks it up by exact match, so these strings are the
# lineage join contract (see openlineage.yaml / AGENTS.md): the namespace comes
# from `openlineage.integration.job.namespace` and the name from Debezium's
# "{connectorName}.{taskId}" convention. A drift here silently detaches the
# sink's lineage from the catalog without any error.
OL_JOB_NAMESPACE = "aurelius-openlineage"
OL_JOB_NAME = "aurelius-kafka-connect-jdbc-sink-example.0"


def _await_sink_openlineage_events(
    consumer: Consumer,
    kafka_topic: str,
    timeout_seconds: float = 90.0,
) -> list[dict]:
    """Poll the OpenLineage topic for the sink connector's events.

    Debezium emits run lifecycle events (START/RUNNING/COMPLETE); a fresh
    earliest-offset group replays everything already on the topic, so the
    worker's startup events are visible even though it ran before the message
    was produced. Other producers share the topic, so foreign events (and any
    non-JSON payload) are skipped. Returns once the collected sink events
    mention both the kafka:// dataset namespace and the sink's topic, or after
    the timeout with whatever was seen (the caller asserts on the outcome).

    Returns:
        JSON events whose job identity matches the sink connector, in order.
    """
    sink_events: list[dict] = []
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        message = consumer.poll(2.0)
        if message is None:
            continue
        if message.error() is not None:
            continue
        value = message.value()
        if value is None:
            continue
        try:
            event = json.loads(value.decode("utf-8"))
        except UnicodeDecodeError, json.JSONDecodeError:
            # Not a JSON event on the shared topic; ignore.
            continue

        job = event.get("job", {})
        if (job.get("namespace"), job.get("name")) == (OL_JOB_NAMESPACE, OL_JOB_NAME):
            sink_events.append(event)
            payload = json.dumps(sink_events)
            if "kafka://" in payload and kafka_topic in payload:
                return sink_events

    return sink_events


def test__openlineage_integration_emits_job_identity(
    kafka_producer: Producer,
    kafka_topic: str,
    key_serializer: Serializer,
    value_serializer_with_header_schema_id: Serializer,
    openlineage_consumer: Consumer,
) -> None:
    """Assert the sink's native OpenLineage integration emits events for us.

    We add the debezium-openlineage-core + openlineage-java jars to the image
    and wire `openlineage.integration.*` + the rendered /tmp/openlineage.yml
    transport ourselves. If the jars are missing the ServiceLoader silently
    no-ops (enabled alone proves nothing), and if the transport or config
    drifts the events reach the topic with the wrong job identity — either
    way the catalog loses this sink's lineage without an error. This asserts
    the observable event stream we are responsible for, not Debezium internals.
    """
    entity = Entity(name="OpenLineage probe")

    produce_message(
        entity=entity,
        guid=entity.guid,
        kafka_producer=kafka_producer,
        kafka_topic=kafka_topic,
        key_serializer=key_serializer,
        value_serializer=value_serializer_with_header_schema_id,
    )

    sink_events = _await_sink_openlineage_events(openlineage_consumer, kafka_topic)

    assert sink_events, (
        f"the sink emitted no OpenLineage events for job {OL_JOB_NAMESPACE}.{OL_JOB_NAME}; "
        "the debezium-openlineage-core jar may be missing from the image (ServiceLoader "
        "silently no-ops) or the rendered /tmp/openlineage.yml transport is broken"
    )

    # The sink describes its topic dataset with the kafka:// namespace the
    # OpenLineage ingestion matches against the Kafka service's bootstrapServers.
    payload = json.dumps(sink_events)
    assert "kafka://" in payload, "sink OpenLineage events must use a kafka:// dataset namespace"
    assert kafka_topic in payload, "sink OpenLineage events must name the sink's topic"
