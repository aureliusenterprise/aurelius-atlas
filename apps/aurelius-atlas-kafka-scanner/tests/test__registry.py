"""The Registry door over its REST API: the two reads, the 404s, the absent door (KSC-04, KSC-05).

httpx's mock transport answers the requests; the door's contract is what the scan relies on:
``None`` means "the Registry holds no answer here", a refusal raises.
"""

from collections.abc import Callable

import httpx2 as httpx
import pytest
from aurelius_atlas_kafka_scanner.registry import SchemaRegistry

Handler = Callable[[httpx.Request], httpx.Response]
"""The mock transport's answer shape."""


def _door(handler: Handler) -> SchemaRegistry:
    return SchemaRegistry("https://registry:8081", transport=httpx.MockTransport(handler))


@pytest.mark.covers("aurelius_atlas_kafka_scanner.registry.SchemaRegistry.latest", rules=["KSC-04"])
async def test_the_subject_read_answers_the_latest_schema() -> None:
    """The subject read reaches /subjects/{subject}/versions/latest and hands back type and text (KSC-04)."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/subjects/orders-value/versions/latest"
        return httpx.Response(200, json={"schemaType": "AVRO", "schema": '{"type": "record"}'})

    schema = await _door(handler).latest("orders-value")
    assert schema is not None
    assert (schema.schema_type, schema.schema_str) == ("AVRO", '{"type": "record"}')


@pytest.mark.covers("aurelius_atlas_kafka_scanner.registry.SchemaRegistry.latest", rules=["KSC-04"])
async def test_an_absent_subject_reads_as_no_answer() -> None:
    """A 404 is "no such subject" — the door answers None and the scan moves to the sniff (KSC-04)."""
    door = _door(lambda _request: httpx.Response(404, json={"error_code": 40401}))
    assert await door.latest("orders-value") is None


@pytest.mark.covers("aurelius_atlas_kafka_scanner.registry.SchemaRegistry.latest", rules=["KSC-04"])
async def test_an_angry_registry_raises() -> None:
    """A configured Registry that refuses is the job's failure, not an absent subject (KSC-04)."""
    door = _door(lambda _request: httpx.Response(500, json={"error_code": 50001}))
    with pytest.raises(httpx.HTTPStatusError):
        await door.latest("orders-value")


@pytest.mark.covers("aurelius_atlas_kafka_scanner.registry.SchemaRegistry.by_id", rules=["KSC-05"])
async def test_the_id_read_answers_the_schema_and_a_missing_id_reads_as_none() -> None:
    """The by-id read reaches /schemas/ids/{id}; an old Registry names no type, which reads AVRO (KSC-05)."""

    def found(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/schemas/ids/42"
        return httpx.Response(200, json={"schema": '{"type": "record"}'})

    assert (await _door(found).by_id(42)) is not None
    assert await _door(lambda _request: httpx.Response(404)).by_id(42) is None


@pytest.mark.covers("aurelius_atlas_kafka_scanner.registry.SchemaRegistry.latest", rules=["KSC-04"])
async def test_a_settings_drawing_no_registry_answers_nothing_anywhere() -> None:
    """No Schema Registry in the settings is the sniff-everything case (KSC-04): the door exists, answers None."""
    door = SchemaRegistry(None)
    assert await door.latest("orders-value") is None
    assert await door.by_id(1) is None
    await door.close()
