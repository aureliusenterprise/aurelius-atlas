"""The field tree: an Avro schema, a JSON schema, or an inferred payload shape (13.1, KSC-04, KSC-05, KSC-06).

The three parsers answer the same shape — a list of :class:`FieldSpec` trees — because the three
ways a topic's fields are known differ only upstream: the Schema Registry's latest subject
(KSC-04), the schema id inside one consumed record (KSC-05), or the JSON keys of that record
themselves (KSC-05). The renders follow the legacy scanner's, so a re-registered topic reads the
same as it did before the port: ``array<int>``, ``map<string>``, ``null | Address``, a named type
by its name, a nested record's fields as children, an array's item as ``<field>_item``, a map's
value as ``<field>_value``.

A parser raises on input it cannot read; KSC-04 makes that the topic's field-less case with a
notice, never a guess. Nothing here touches the catalogue or the broker: the tree is pure text
in, pure data out, which is what makes every rule of this module unit-testable.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass

from avro.schema import ArraySchema, Field, MapSchema, NamedSchema, RecordSchema, Schema, UnionSchema
from avro.schema import parse as parse_avro_schema

SchemaLike = Schema | str | None
"""A place an Avro schema sits: the parser's answer, a type name, or a held-back reference.

The avro package keeps a schema's members in untyped properties (a field's type, an array's
items, a map's values) and, on forward references it holds back, may hold a plain name or nothing
at all. Every read of one of those members narrows through :func:`_as_schema` first.
"""

WIRE_MAGIC = b"\x00"
"""The Confluent wire format's first byte: what names a schema id inside a record (KSC-05)."""

WIRE_ID_BYTES = 4
"""The width of the schema id that follows the magic byte, big-endian (KSC-05)."""


@dataclass(frozen=True)
class FieldSpec:
    """One field of a topic's tree: its name, its rendered type, its docs, and its children (KSC-06)."""

    name: str
    """The field's name: a schema field, or ``<field>_item`` / ``<field>_value`` for a member."""

    type_name: str
    """The rendered type text: ``string``, ``array<int>``, ``null | Address``, a named type's name."""

    definition: str | None = None
    """The field's docs, when its source carries any (an Avro ``doc``, a JSON ``description``)."""

    children: tuple[FieldSpec, ...] = ()
    """The fields nested under this one: a record's fields, an array's item, a map's value."""


def schema_id_of(record_value: bytes) -> int | None:
    """The schema id inside a record's value, or ``None`` when the value is not wire format (KSC-05).

    A value that starts with the magic byte carries the id in its next four bytes, big-endian —
    the whole of the decoding this increment needs, since the scan reads schemas, not rows.
    """
    if len(record_value) < 1 + WIRE_ID_BYTES or not record_value.startswith(WIRE_MAGIC):
        return None
    return int.from_bytes(record_value[1 : 1 + WIRE_ID_BYTES], "big")


def parse_avro(text: str) -> list[FieldSpec]:
    """The fields of an Avro record schema, as the legacy scanner rendered them (KSC-04, KSC-06).

    Raises:
        Exception: the text is not a readable Avro schema — the caller decides the notice (KSC-04).
    """
    schema = parse_avro_schema(text)
    if not isinstance(schema, RecordSchema):
        msg = f"an Avro schema of type {schema.type} names no fields"
        raise TypeError(msg)
    return _avro_record(schema)


def parse_json_schema(text: str) -> list[FieldSpec]:
    """The fields of a JSON-schema document, walking ``properties`` and ``$defs`` (KSC-04, KSC-06).

    Raises:
        Exception: the text is not readable JSON — the caller decides the notice (KSC-04).
    """
    schema = json.loads(text)
    if not isinstance(schema, dict):
        msg = "a JSON schema that is not an object names no fields"
        raise TypeError(msg)
    defs = schema.get("$defs")
    return _json_properties(schema, defs if isinstance(defs, dict) else {})


DATA_TYPE_MAPPING = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "dict": "object",
    "list": "array",
    "NoneType": "null",
}
"""The payload types the inference names, in the words the catalogue's field type uses (KSC-05)."""


def parse_payload(text: str) -> list[FieldSpec]:
    """The fields of a JSON object payload, inferred from its keys (KSC-05).

    Raises:
        Exception: the text is not JSON, or not a JSON object — the caller decides the notice.
    """
    payload = json.loads(text)
    if not isinstance(payload, dict):
        msg = "a payload that is not a JSON object names no fields"
        raise TypeError(msg)
    return _payload_object(payload)


def _avro_record(record: RecordSchema) -> list[FieldSpec]:
    """One Avro record's fields as a tree, by the legacy walk (KSC-06).

    A nested record hangs its fields under the field; an array names its item child ``_item`` and
    a map its value child ``_value`` — records inside them hang their own fields instead. A union
    renders but is not descended into, exactly as the legacy parser worked.
    """
    nodes: list[FieldSpec] = []
    for field in _record_fields(record):
        name = _text(field.name) or ""
        inner = _as_schema(field.type)
        node = FieldSpec(name=name, type_name=_avro_type(inner), definition=_text(field.doc))
        if isinstance(inner, RecordSchema):
            node = _with_children(node, _avro_record(inner))
        elif isinstance(inner, ArraySchema):
            items = _as_schema(inner.items)
            node = _with_children(
                node,
                _avro_record(items)
                if isinstance(items, RecordSchema)
                else [FieldSpec(f"{name}_item", _avro_type(items))],
            )
        elif isinstance(inner, MapSchema):
            values = _as_schema(inner.values)
            node = _with_children(
                node,
                _avro_record(values)
                if isinstance(values, RecordSchema)
                else [FieldSpec(f"{name}_value", _avro_type(values))],
            )
        nodes.append(node)
    return nodes


def _avro_type(schema: SchemaLike) -> str:
    """The rendered type of an Avro schema, by the legacy render rules (KSC-06)."""
    if isinstance(schema, UnionSchema):
        return " | ".join(_avro_type(_as_schema(member)) for member in schema.schemas)
    if isinstance(schema, MapSchema):
        return f"map<{_avro_type(_as_schema(schema.values))}>"
    if isinstance(schema, ArraySchema):
        return f"array<{_avro_type(_as_schema(schema.items))}>"
    if isinstance(schema, NamedSchema):
        return _text(schema.name) or _text(schema.type) or ""
    if isinstance(schema, Schema):
        return _text(schema.type) or ""
    return str(schema) if schema is not None else "null"


def _record_fields(record: RecordSchema) -> list[Field]:
    """The record's declared fields, as the avro package's :class:`Field` list (untyped member)."""
    return [field for field in _as_list(record.fields) if isinstance(field, Field)]


def _as_list(raw: object) -> list[object]:
    """An avro member read as a list; anything else reads as the empty list."""
    return list(raw) if isinstance(raw, list) else []


def _as_schema(raw: object) -> SchemaLike:
    """An avro member (a field's type, an array's items, a map's values) as a schema, name, or nothing.

    The avro package types none of these members; the schema classes and plain strings are all it
    ever puts there, and :func:`_avro_type` and the record walk handle each.
    """
    if isinstance(raw, (Schema, str)) or raw is None:
        return raw
    return str(raw)


def _json_properties(
    schema: Mapping[str, object],
    defs: Mapping[str, object],
    chain: frozenset[str] = frozenset(),
) -> list[FieldSpec]:
    """One JSON-schema object's properties as a tree (KSC-06).

    An object nests its own properties, an array of objects nests the item's, and every ``$ref``
    the property holds resolves through ``$defs`` and nests under the property that named it — the
    legacy walk. A ``$ref`` already in ``chain`` is not descended a second time: a
    self-referential definition would otherwise nest forever, the one legacy behaviour no scanner
    should keep.
    """
    nodes: list[FieldSpec] = []
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        return nodes
    for name, raw in properties.items():
        metadata = raw if isinstance(raw, Mapping) else {}
        property_name = str(name)
        type_name = _json_type(metadata, defs)
        children = _json_children(property_name, metadata, type_name, defs, chain)
        for ref in _referenced_names(metadata):
            if ref in chain:
                continue
            definition = _definition(ref, defs)
            if definition is not None:
                children.extend(_json_properties(definition, defs, chain | {ref}))
        nodes.append(
            FieldSpec(
                name=property_name,
                type_name=type_name,
                definition=_text(metadata.get("description")),
                children=tuple(children),
            )
        )
    return nodes


def _json_children(
    name: str,
    metadata: Mapping[str, object],
    type_name: str,
    defs: Mapping[str, object],
    chain: frozenset[str],
) -> list[FieldSpec]:
    """The fields nested under one property: an object's own, or an array item's (KSC-06).

    The legacy parser names the item child after the *property* (``<property>_item``), not the
    item's own title — a tree a re-scan reads the same as before the port.
    """
    children: list[FieldSpec] = []
    if metadata.get("type") == "object":
        return _json_properties(metadata, defs, chain)
    items = metadata.get("items")
    if type_name.startswith("array") and isinstance(items, Mapping):
        if items.get("type") == "object":
            return _json_properties(items, defs, chain)
        return [FieldSpec(f"{name}_item", _json_type(items, defs, chain))]
    return children


def _json_type(schema: Mapping[str, object], defs: Mapping[str, object], chain: frozenset[str] = frozenset()) -> str:
    """The rendered type of a JSON-schema fragment, by the legacy render rules (KSC-06)."""
    ref = _ref_name(schema)
    if ref is not None:
        definition = _definition(ref, defs)
        if definition is not None:
            return _json_type(definition, defs, chain)
    combinator = _combinator_type(schema, defs, chain)
    if combinator is not None:
        return combinator
    type_name = str(schema.get("type", "object"))
    if type_name == "array":
        items = schema.get("items")
        if isinstance(items, Mapping):
            return f"array<{_json_type(items, defs, chain)}>"
        return "array"
    if type_name == "object":
        return str(schema.get("title", "object"))
    return type_name


def _combinator_type(schema: Mapping[str, object], defs: Mapping[str, object], chain: frozenset[str]) -> str | None:
    """The rendered type of a fragment's combinator (KSC-06), or ``None`` when it holds none.

    ``anyOf`` joins with `` | ``, ``oneOf`` with `` ^ ``, and ``allOf`` with `` & `` — an ``allOf``
    part that is a constraint rather than a type renders ``minimum(0)``-style, the legacy text.
    """
    for key, separator in (("anyOf", " | "), ("allOf", " & "), ("oneOf", " ^ ")):
        if key not in schema:
            continue
        parts = [_as_mapping(part) for part in _parts(schema[key])]
        if key == "allOf":
            return separator.join(
                _json_type(part, defs, chain) if ("type" in part or "$ref" in part) else _constraint(part)
                for part in parts
            )
        return separator.join(_json_type(part, defs, chain) for part in parts)
    return None


def _constraint(schema: Mapping[str, object]) -> str:
    """An ``allOf`` part that is a constraint rather than a type: ``minimum(0)`` style (KSC-06)."""
    return " & ".join(f"{key}({_render(value)})" for key, value in schema.items())


def _referenced_names(schema: Mapping[str, object]) -> list[str]:
    """The ``$ref`` names a property reaches directly or through its combinators and items (KSC-06)."""
    names: list[str] = []
    if (own := _ref_name(schema)) is not None:
        names.append(own)
    parts = [part for key in ("anyOf", "allOf", "oneOf") for part in _parts(schema.get(key, []))]
    if (items := schema.get("items")) is not None:
        parts.append(items)
    names.extend(name for part in parts if (name := _ref_name(_as_mapping(part))) is not None)
    return names


def _payload_object(payload: Mapping[str, object]) -> list[FieldSpec]:
    """One JSON object payload's fields as a tree, by the legacy inference (KSC-05)."""
    nodes: list[FieldSpec] = []
    for name, value in payload.items():
        kind = type(value).__name__
        node = FieldSpec(name=str(name), type_name=DATA_TYPE_MAPPING.get(kind, kind))
        if isinstance(value, dict):
            node = _with_children(node, _payload_object(value))
        nodes.append(node)
    return nodes


def _with_children(node: FieldSpec, children: list[FieldSpec]) -> FieldSpec:
    """``node`` with its children attached: the dataclass is frozen, so the rebuilt copy is returned."""
    return FieldSpec(node.name, node.type_name, node.definition, tuple(children))


def _definition(
    ref: str, defs: Mapping[str, object], chain: frozenset[str] = frozenset()
) -> Mapping[str, object] | None:
    """The ``$defs`` entry a ``$ref`` names, or ``None`` when absent or already in the chain."""
    if ref in chain:
        return None
    entry = defs.get(ref.removeprefix("#/$defs/"))
    return entry if isinstance(entry, Mapping) else None


def _ref_name(schema: Mapping[str, object]) -> str | None:
    """The ``$ref`` of a fragment, when it carries one."""
    ref = schema.get("$ref")
    return str(ref) if isinstance(ref, str) else None


def _as_mapping(raw: object) -> Mapping[str, object]:
    """A combinator part as a mapping; anything else reads as the empty fragment."""
    return raw if isinstance(raw, Mapping) else {}


def _parts(raw: object) -> list[object]:
    """The members of a combinator list; a schema that is not a list holds one part."""
    return list(raw) if isinstance(raw, list) else [raw]


def _text(raw: object) -> str | None:
    """A documentation value as text, or ``None`` when absent."""
    return str(raw) if isinstance(raw, str) and raw else None


def _render(raw: object) -> str:
    """A constraint value for the render: numbers and words as JSON spells them."""
    return json.dumps(raw)
