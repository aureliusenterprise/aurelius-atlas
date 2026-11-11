"""The field parsers: Avro renders, JSON-schema walks, payload inference, the wire id (KSC-04..06).

The renders are the legacy scanner's, so these tests are fidelity tests as much as unit tests:
each expected string is what the legacy job wrote for the same schema, read from its own tests.
"""

import json

import pytest
from aurelius_atlas_kafka_scanner.fields import FieldSpec, parse_avro, parse_json_schema, parse_payload, schema_id_of

NESTED_AVRO = """
{
  "type": "record",
  "name": "Order",
  "namespace": "shop",
  "fields": [
    {"name": "id", "type": "string", "doc": "the order id"},
    {"name": "total", "type": ["null", "double"], "doc": null},
    {"name": "lines", "type": {
        "type": "array",
        "items": {"type": "record", "name": "Line", "fields": [
            {"name": "sku", "type": "string"},
            {"name": "qty", "type": "int"}
        ]}
    }},
    {"name": "tags", "type": {"type": "map", "values": "string"}},
    {"name": "address", "type": {"type": "record", "name": "Address", "fields": [
        {"name": "city", "type": "string"}
    ]}}
  ]
}
"""


def _tree(fields: list[FieldSpec]) -> dict[str, FieldSpec]:
    return {field.name: field for field in fields}


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.schema_id_of", rules=["KSC-05"])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (b"\x00\x00\x00\x00\x2a payload", 42),
        (b"\x00\x00\x00\x01\x35", 309),
        (b'{"id": 1}', None),
        (b"\x01\x00\x00\x00\x2a", None),
        (b"\x00\x00", None),
        (b"", None),
    ],
)
def test_the_wire_id_is_the_magic_byte_plus_four_bytes(value: bytes, expected: int | None) -> None:
    """KSC-05: the magic byte names a schema id in the next four big-endian bytes; anything else is not wire format."""
    assert schema_id_of(value) == expected


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_avro", rules=["KSC-04", "KSC-06"])
def test_avro_primitive_and_union_renders() -> None:
    """The legacy renders: a named type by its name, a union joined with ' | ' (KSC-06)."""
    fields = _tree(parse_avro(NESTED_AVRO))
    assert fields["id"].type_name == "string"
    assert fields["id"].definition == "the order id"
    assert fields["total"].type_name == "null | double"


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_avro", rules=["KSC-06"])
def test_avro_composites_render_and_nest_the_legacy_way() -> None:
    """array<>, map<>, a record's children, an array item's records — the legacy walk (KSC-06)."""
    fields = _tree(parse_avro(NESTED_AVRO))
    assert fields["lines"].type_name == "array<Line>"
    assert [child.name for child in fields["lines"].children] == ["sku", "qty"]
    assert fields["tags"].type_name == "map<string>"
    assert [child.name for child in fields["tags"].children] == ["tags_value"]
    assert fields["tags"].children[0].type_name == "string"
    assert fields["address"].type_name == "Address"
    assert [child.name for child in fields["address"].children] == ["city"]


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_avro", rules=["KSC-06"])
def test_avro_array_of_scalars_names_its_item_child() -> None:
    """An array whose items are not a record still gets the ``<field>_item`` child (KSC-06)."""
    schema = """
    {"type": "record", "name": "R", "fields": [
        {"name": "scores", "type": {"type": "array", "items": "int"}}
    ]}
    """
    fields = _tree(parse_avro(schema))
    assert fields["scores"].type_name == "array<int>"
    assert fields["scores"].children[0].name == "scores_item"


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_avro", rules=["KSC-04"])
def test_an_avro_schema_that_is_no_record_raises() -> None:
    """A parser never guesses: a schema with no fields is an error the scan turns into a notice (KSC-04)."""
    with pytest.raises(TypeError, match="names no fields"):
        parse_avro('"string"')


JSON_SCHEMA = """
{
  "type": "object",
  "title": "Order",
  "properties": {
    "id": {"type": "string", "description": "the order id"},
    "total": {"anyOf": [{"type": "number"}, {"type": "null"}]},
    "lines": {"type": "array", "items": {"type": "object", "title": "Line", "properties": {
        "sku": {"type": "string"}
    }}},
    "address": {"$ref": "#/$defs/Address"},
    "limits": {"allOf": [{"type": "object"}, {"minimum": 0}]},
    "choice": {"oneOf": [{"type": "string"}, {"type": "integer"}]}
  },
  "$defs": {
    "Address": {"type": "object", "title": "Address", "properties": {
        "city": {"type": "string"},
        "country": {"type": "string"}
    }}
  }
}
"""


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_json_schema", rules=["KSC-04", "KSC-06"])
def test_json_schema_renders_primitives_and_combinators() -> None:
    """Render the combinators: anyOf ' | ', oneOf ' ^ ', allOf ' & '; a plain type names itself (KSC-06)."""
    fields = _tree(parse_json_schema(JSON_SCHEMA))
    assert fields["id"].type_name == "string"
    assert fields["id"].definition == "the order id"
    assert fields["total"].type_name == "number | null"
    assert fields["choice"].type_name == "string ^ integer"
    assert fields["limits"].type_name == "object & minimum(0)"


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_json_schema", rules=["KSC-06"])
def test_json_schema_nests_objects_arrays_and_refs() -> None:
    """An object nests its own properties, an array of objects the item's, and a $ref nests its definition (KSC-06)."""
    fields = _tree(parse_json_schema(JSON_SCHEMA))
    assert fields["lines"].type_name == "array<Line>"
    assert [child.name for child in fields["lines"].children] == ["sku"]
    assert fields["address"].type_name == "Address"
    assert [child.name for child in fields["address"].children] == ["city", "country"]


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_json_schema", rules=["KSC-06"])
def test_a_self_referential_ref_nests_once() -> None:
    """A definition that names itself is not descended a second time — no infinite tree (KSC-06)."""
    schema = """
    {"type": "object", "properties": {"node": {"$ref": "#/$defs/Node"}},
     "$defs": {"Node": {"type": "object", "title": "Node", "properties": {
         "next": {"$ref": "#/$defs/Node"}}}}}
    """
    fields = _tree(parse_json_schema(schema))
    node = fields["node"]
    assert node.type_name == "Node"
    assert [child.name for child in node.children] == ["next"]
    assert node.children[0].children == ()


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_payload", rules=["KSC-05"])
def test_payload_inference_types_each_key_and_nests_objects() -> None:
    """A JSON object's keys infer fields: the words the catalogue uses for each Python kind (KSC-05)."""
    fields = _tree(parse_payload('{"id": "7", "qty": 3, "price": 9.5, "ok": true, "when": null, "who": {"n": 1}}'))
    assert fields["id"].type_name == "string"
    assert fields["qty"].type_name == "integer"
    assert fields["price"].type_name == "number"
    assert fields["ok"].type_name == "boolean"
    assert fields["when"].type_name == "null"
    assert fields["who"].type_name == "object"
    assert fields["who"].children[0].name == "n"


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_payload", rules=["KSC-05"])
def test_a_json_that_is_no_object_raises_the_named_error() -> None:
    """A JSON document that is not an object names no fields; the message says so (KSC-05)."""
    with pytest.raises(TypeError, match="names no fields"):
        parse_payload("[1, 2, 3]")


@pytest.mark.covers("aurelius_atlas_kafka_scanner.fields.parse_payload", rules=["KSC-05"])
@pytest.mark.parametrize("text", ["not json at all", "", "{"])
def test_text_that_is_no_json_raises_at_all(text: str) -> None:
    """Unreadable text is the scan's field-less notice; the parser raises a JSON decode error (KSC-05)."""
    with pytest.raises(json.JSONDecodeError):
        parse_payload(text)
