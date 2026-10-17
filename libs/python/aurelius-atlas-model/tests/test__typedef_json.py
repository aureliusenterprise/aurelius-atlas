"""Reading and writing Atlas's REST JSON (TDM-01 to TDM-05, TDM-13 to TDM-15, TDM-20).

Expected bodies are read from the Apache Atlas 2.4.0 typedef classes and Jackson 2.12's defaults, which
``AtlasJsonProvider`` uses unchanged.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasConstraintDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
    AtlasTypeDefHeader,
    AtlasTypesDef,
    Cardinality,
    PropagateTags,
    RelationshipCategory,
    TypeCategory,
)
from pydantic import ValidationError

FIXTURES = Path(__file__).parent / "fixtures"

ATTRIBUTE_DEFAULTS = {
    "isOptional": False,
    "cardinality": "SINGLE",
    "valuesMinCount": -1,
    "valuesMaxCount": -1,
    "isUnique": False,
    "isIndexable": False,
    "includeInNotification": False,
    "searchWeight": -1,
}
"""What ``new AtlasAttributeDef()`` writes: its primitives always, its objects only when set."""


@pytest.mark.covers("aurelius_atlas_model.typedef.AtlasModel.to_json", rules=["TDM-01", "TDM-02"])
def test__an_attribute_definition_is_written_under_the_java_getter_names() -> None:
    """Every field of ``AtlasAttributeDef`` is written as its getter names it; null ones are left out."""
    attribute = AtlasAttributeDef(
        name="owner",
        type_name="string",
        is_optional=True,
        cardinality=None,
        values_min_count=0,
        values_max_count=1,
        is_unique=True,
        is_indexable=True,
        include_in_notification=True,
        default_value="nobody",
        description="who owns it",
        search_weight=5,
        constraints=[AtlasConstraintDef(type="ownedRef")],
        options={"isSoftReference": "true"},
        display_name="Owner",
    )

    assert attribute.to_json() == {
        "name": "owner",
        "typeName": "string",
        "isOptional": True,
        "valuesMinCount": 0,
        "valuesMaxCount": 1,
        "isUnique": True,
        "isIndexable": True,
        "includeInNotification": True,
        "defaultValue": "nobody",
        "description": "who owns it",
        "searchWeight": 5,
        "constraints": [{"type": "ownedRef"}],
        "options": {"isSoftReference": "true"},
        "displayName": "Owner",
    }


@pytest.mark.covers("aurelius_atlas_model.typedef.AtlasModel.to_json", rules=["TDM-01", "TDM-02"])
def test__a_relationship_definition_is_written_under_the_java_getter_names() -> None:
    """``endDef1``, ``endDef2``, ``isContainer`` and ``isLegacyAttribute`` keep their Java spelling."""
    relationship = AtlasRelationshipDef(
        name="table_columns",
        relationship_category=RelationshipCategory.COMPOSITION,
        relationship_label="__table.columns",
        propagate_tags=PropagateTags.NONE,
        end_def1=AtlasRelationshipEndDef(type="table", name="columns", cardinality=Cardinality.SET, is_container=True),
        end_def2=AtlasRelationshipEndDef(type="column", name="table", is_legacy_attribute=True),
    )

    assert relationship.to_json() == {
        "name": "table_columns",
        "category": "RELATIONSHIP",
        "attributeDefs": [],
        "relationshipCategory": "COMPOSITION",
        "relationshipLabel": "__table.columns",
        "propagateTags": "NONE",
        "endDef1": {
            "type": "table",
            "name": "columns",
            "isContainer": True,
            "cardinality": "SET",
            "isLegacyAttribute": False,
        },
        "endDef2": {
            "type": "column",
            "name": "table",
            "isContainer": False,
            "cardinality": "SINGLE",
            "isLegacyAttribute": True,
        },
    }


@pytest.mark.covers("aurelius_atlas_model.typedef.AtlasModel.to_json", rules=["TDM-01", "TDM-02"])
def test__an_entity_definition_writes_its_derived_fields_when_they_are_set() -> None:
    """``subTypes``, ``relationshipAttributeDefs`` and ``businessAttributeDefs`` appear only when set."""
    entity = AtlasEntityDef.model_validate(
        {
            "name": "table",
            "serviceType": "hive",
            "typeVersion": "1.0",
            "subTypes": ["view"],
            "relationshipAttributeDefs": [{"name": "columns", "relationshipTypeName": "table_columns"}],
            "businessAttributeDefs": {"bm": [{"name": "owner"}]},
        }
    )

    assert entity.to_json() == {
        "name": "table",
        "serviceType": "hive",
        "typeVersion": "1.0",
        "category": "ENTITY",
        "attributeDefs": [],
        "superTypes": [],
        "subTypes": ["view"],
        "relationshipAttributeDefs": [
            {"name": "columns", "relationshipTypeName": "table_columns", "isLegacyAttribute": False}
            | ATTRIBUTE_DEFAULTS
        ],
        "businessAttributeDefs": {"bm": [{"name": "owner"} | ATTRIBUTE_DEFAULTS]},
    }


@pytest.mark.covers("aurelius_atlas_model.typedef.AtlasModel.to_json", rules=["TDM-02"])
def test__null_values_inside_a_map_are_written() -> None:
    """``NON_NULL`` applies to properties, not to map contents: a constraint parameter may be null."""
    constraint = AtlasConstraintDef(type="inverseRef", params={"attribute": None})

    assert constraint.to_json() == {"type": "inverseRef", "params": {"attribute": None}}


@pytest.mark.covers(rules=["TDM-03"])
def test__unknown_fields_are_ignored() -> None:
    """``@JsonIgnoreProperties(ignoreUnknown=true)`` on every class."""
    enum = AtlasEnumDef.model_validate(
        {"name": "colour", "flavour": "sweet", "elementDefs": [{"value": "red", "rank": 1}]}
    )

    assert enum.to_json() == {"name": "colour", "category": "ENUM", "elementDefs": [{"value": "red"}]}


@pytest.mark.covers("aurelius_atlas_model.typedef.AtlasBaseTypeDef.category", rules=["TDM-04"])
@pytest.mark.parametrize(
    ("model", "category"),
    [
        (AtlasEnumDef, TypeCategory.ENUM),
        (AtlasStructDef, TypeCategory.STRUCT),
        (AtlasClassificationDef, TypeCategory.CLASSIFICATION),
        (AtlasEntityDef, TypeCategory.ENTITY),
        (AtlasRelationshipDef, TypeCategory.RELATIONSHIP),
        (AtlasBusinessMetadataDef, TypeCategory.BUSINESS_METADATA),
    ],
)
def test__each_type_definition_writes_its_own_category(model: type[AtlasStructDef], category: TypeCategory) -> None:
    """``getCategory()`` returns what the constructor fixed; ``category`` has no setter, so input is ignored."""
    typedef = model.model_validate({"name": "t", "category": "PRIMITIVE"})

    assert typedef.category is category
    assert typedef.to_json()["category"] == category.value


@pytest.mark.covers(rules=["TDM-04"])
def test__a_header_reads_and_writes_its_category() -> None:
    """``AtlasTypeDefHeader`` has ``setCategory``, so its category is an ordinary field."""
    header = AtlasTypeDefHeader.model_validate({"guid": "g", "name": "t", "category": "ENTITY"})

    assert header.category is TypeCategory.ENTITY
    assert header.to_json() == {"guid": "g", "name": "t", "category": "ENTITY"}


@pytest.mark.covers(rules=["TDM-05"])
@pytest.mark.parametrize(
    "value",
    [1792231200123, "1792231200123", "2026-10-17T10:00:00.123Z", "2026-10-17T12:00:00.123+02:00"],
    ids=["number", "digits", "iso-utc", "iso-offset"],
)
def test__timestamps_are_read_from_numbers_and_iso_strings(value: object) -> None:
    """Jackson's ``StdDateFormat`` reads epoch milliseconds, digit strings and ISO-8601 (DD-022)."""
    struct = AtlasStructDef.model_validate({"createTime": value, "updateTime": value})

    assert struct.create_time == datetime(2026, 10, 17, 10, 0, 0, 123000, tzinfo=UTC)
    assert struct.to_json()["createTime"] == 1792231200123
    assert struct.to_json()["updateTime"] == 1792231200123


@pytest.mark.covers(rules=["TDM-05"])
def test__a_timestamp_without_a_zone_is_utc() -> None:
    """``StdDateFormat`` defaults to UTC for an ISO-8601 string without an offset."""
    struct = AtlasStructDef.model_validate({"createTime": "2026-10-17T10:00:00"})

    assert struct.to_json()["createTime"] == 1792231200000


@pytest.mark.covers(rules=["TDM-13"])
def test__a_types_def_keeps_an_explicit_null_list_and_does_not_write_it() -> None:
    """``new AtlasTypesDef()`` starts with six empty lists; the setters store what Jackson gives them."""
    types = AtlasTypesDef.model_validate({"enumDefs": None, "entityDefs": [{"name": "t"}]})

    assert types.enum_defs is None
    assert types.to_json() == {
        "structDefs": [],
        "classificationDefs": [],
        "entityDefs": [{"name": "t", "category": "ENTITY", "attributeDefs": [], "superTypes": []}],
        "relationshipDefs": [],
        "businessMetadataDefs": [],
    }


@pytest.mark.covers(rules=["TDM-14"])
@pytest.mark.parametrize(
    ("model", "body"),
    [
        (AtlasAttributeDef, {"cardinality": "single"}),
        (AtlasAttributeDef, {"indexType": "TEXT"}),
        (AtlasRelationshipDef, {"relationshipCategory": "Composition"}),
        (AtlasRelationshipDef, {"propagateTags": "ALL"}),
        (AtlasTypeDefHeader, {"category": "entity"}),
    ],
)
def test__enum_values_are_read_by_their_java_name_with_case(
    model: type[AtlasAttributeDef], body: dict[str, Any]
) -> None:
    """Jackson reads Java enums by ``name()``, case-sensitively, and fails on any other value."""
    with pytest.raises(ValidationError):
        model.model_validate(body)


@pytest.mark.covers(rules=["TDM-15"])
def test__scalars_are_coerced_as_jackson_coerces_them() -> None:
    """Jackson 2.12 allows scalar coercion by default: numbers into strings, numeric and boolean strings."""
    attribute = AtlasAttributeDef.model_validate(
        {"name": 42, "isOptional": "true", "valuesMaxCount": "3", "description": 1.5}
    )

    assert attribute.name == "42"
    assert attribute.is_optional is True
    assert attribute.values_max_count == 3
    assert attribute.description == "1.5"


@pytest.mark.covers(rules=["TDM-15"])
def test__a_boolean_is_not_a_timestamp() -> None:
    """Jackson's date deserialiser takes numbers and strings only."""
    with pytest.raises(ValidationError):
        AtlasStructDef.model_validate({"createTime": True})


@pytest.mark.covers(rules=["TDM-15"])
def test__a_value_that_cannot_be_coerced_is_rejected_naming_the_field() -> None:
    """An object where a string is expected fails, and the error names the field."""
    with pytest.raises(ValidationError) as raised:
        AtlasEntityDef.model_validate({"attributeDefs": [{"typeName": {"nested": True}}]})

    assert raised.value.errors()[0]["loc"] == ("attributeDefs", 0, "typeName")


def _read(name: str) -> AtlasTypesDef:
    return AtlasTypesDef.model_validate(json.loads((FIXTURES / name).read_text()))


@pytest.mark.covers(rules=["TDM-20"])
@pytest.mark.parametrize("name", ["0010-base_model.json", "0011-glossary_model.json"])
def test__atlas_built_in_models_read_and_survive_a_round_trip(name: str) -> None:
    """Atlas's ``addons/models`` files read; writing and reading again gives the same definitions."""
    types = _read(name)

    assert types == AtlasTypesDef.model_validate(types.to_json())
    assert not types.is_empty()


@pytest.mark.covers(rules=["TDM-20"])
def test__the_base_model_reads_as_atlas_defines_it() -> None:
    """Spot checks of ``0010-base_model.json``: names, super types, a relationship end and an attribute."""
    types = _read("0010-base_model.json")
    process = next(entity for entity in types.entity_defs or [] if entity.name == "Process")
    inputs = process.get_attribute("inputs")

    assert types.has_entity_def("Referenceable")
    assert types.has_enum_def("atlas_operation")
    assert process.super_types == ["Asset"]
    assert inputs is not None
    assert inputs.type_name == "array<DataSet>"
    assert inputs.cardinality == "SET"
    assert inputs.is_optional is True


@pytest.mark.covers(rules=["TDM-20"])
@pytest.mark.parametrize(
    "typedef",
    [
        AtlasEnumDef(name="e", element_defs=[AtlasEnumElementDef(value="A", ordinal=1)], default_value="A"),
        AtlasStructDef(name="s", attribute_defs=[AtlasAttributeDef(name="a", type_name="int")]),
        AtlasClassificationDef(name="c", super_types=["PII"], entity_types=["table"]),
        AtlasEntityDef(name="t", super_types=["DataSet"], create_time=datetime(2026, 1, 1, tzinfo=UTC)),
        AtlasRelationshipDef(name="r", end_def1=AtlasRelationshipEndDef(type="t", name="x")),
        AtlasBusinessMetadataDef(name="b", options={"x": "y"}),
    ],
    ids=["enum", "struct", "classification", "entity", "relationship", "business-metadata"],
)
def test__writing_and_reading_gives_an_equal_model(typedef: AtlasStructDef) -> None:
    """The SerDe tests of ``TestAtlas*Def``: ``fromJson(toJson(def))`` equals ``def``."""
    assert type(typedef).model_validate(typedef.to_json()) == typedef
