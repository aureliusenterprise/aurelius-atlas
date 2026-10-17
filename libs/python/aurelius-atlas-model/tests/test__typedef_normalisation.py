"""The Java setters' and constructors' normalisations (TDM-06 to TDM-12).

Each runs when Jackson reads a body, so a client sees it in the response. Read from the setters of
``AtlasStructDef``, ``AtlasEnumDef``, ``AtlasClassificationDef``, ``AtlasEntityDef``, ``AtlasAttributeDef``,
``AtlasRelationshipDef`` and ``AtlasRelationshipEndDef`` in Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasClassificationDef,
    AtlasConstraintDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
    Cardinality,
)


@pytest.mark.covers(rules=["TDM-06"])
@pytest.mark.parametrize("body", [{}, {"attributeDefs": None}, {"attributeDefs": []}], ids=["missing", "null", "empty"])
def test__attribute_defs_are_never_null(body: dict[str, Any]) -> None:
    """``setAttributeDefs`` stores a new empty list for null or empty input."""
    assert AtlasStructDef.model_validate(body).to_json()["attributeDefs"] == []


@pytest.mark.covers(rules=["TDM-06"])
@pytest.mark.parametrize("value", [None, []], ids=["null", "empty"])
def test__element_defs_super_types_and_entity_types_are_never_null(value: object) -> None:
    """``setElementDefs``, ``setSuperTypes`` and ``setEntityTypes`` do the same."""
    classification = AtlasClassificationDef.model_validate({"superTypes": value, "entityTypes": value})
    entity = AtlasEntityDef.model_validate({"superTypes": value})
    enum = AtlasEnumDef.model_validate({"elementDefs": value})

    assert (classification.super_types, classification.entity_types) == ([], [])
    assert entity.super_types == []
    assert enum.element_defs == []


@pytest.mark.covers(rules=["TDM-06"])
def test__derived_entity_fields_stay_null_when_not_given() -> None:
    """``subTypes``, ``relationshipAttributeDefs`` and ``businessAttributeDefs`` have plain setters."""
    entity = AtlasEntityDef.model_validate({"subTypes": None})

    assert entity.sub_types is None
    assert entity.relationship_attribute_defs is None
    assert entity.business_attribute_defs is None


@pytest.mark.covers(rules=["TDM-07"])
def test__the_last_attribute_with_a_name_is_kept_at_its_own_position() -> None:
    """``setAttributeDefs`` walks the list backwards, keeps the first of each lower-cased name, then reverses."""
    struct = AtlasStructDef.model_validate(
        {
            "attributeDefs": [
                {"name": "a", "typeName": "int"},
                {"name": "b", "typeName": "int"},
                {"name": "A", "typeName": "string"},
                {"typeName": "nameless"},
                {"name": "c", "typeName": "int"},
            ]
        }
    )

    assert [(attribute.name, attribute.type_name) for attribute in struct.attribute_defs] == [
        ("b", "int"),
        ("A", "string"),
        ("c", "int"),
    ]


@pytest.mark.covers(rules=["TDM-07"])
def test__assigning_attribute_defs_normalises_them_too() -> None:
    """The Java setter runs on every assignment, not only on construction."""
    struct = AtlasStructDef()
    struct.attribute_defs = [AtlasAttributeDef(name="x"), AtlasAttributeDef(name="X", type_name="int")]

    assert [attribute.type_name for attribute in struct.attribute_defs] == ["int"]


@pytest.mark.covers(rules=["TDM-08"])
def test__the_last_enum_element_with_a_value_is_kept_at_its_own_position() -> None:
    """``setElementDefs`` compares lower-cased values and drops elements without one."""
    enum = AtlasEnumDef.model_validate(
        {
            "elementDefs": [
                {"value": "RED", "ordinal": 1},
                {"value": "GREEN", "ordinal": 2},
                {"ordinal": 3},
                {"value": "red", "ordinal": 4},
            ]
        }
    )

    assert [(element.value, element.ordinal) for element in enum.element_defs] == [("GREEN", 2), ("red", 4)]


@pytest.mark.covers(rules=["TDM-09"])
def test__set_valued_fields_hold_each_name_once_in_first_seen_order() -> None:
    """Java's ``HashSet`` drops duplicates; the order is first-seen (DD-021)."""
    classification = AtlasClassificationDef.model_validate(
        {"superTypes": ["b", "a", "b"], "entityTypes": ["t", "t"], "subTypes": ["x", "y", "x"]}
    )
    entity = AtlasEntityDef.model_validate({"superTypes": ["DataSet", "Asset", "DataSet"], "subTypes": ["v", "v"]})

    assert classification.super_types == ["b", "a"]
    assert classification.entity_types == ["t"]
    assert classification.sub_types == ["x", "y"]
    assert entity.super_types == ["DataSet", "Asset"]
    assert entity.sub_types == ["v"]


@pytest.mark.covers(rules=["TDM-10"])
def test__an_attribute_definition_without_values_reads_as_javas_defaults() -> None:
    """``new AtlasAttributeDef()`` chains to ``SINGLE``, ``COUNT_NOT_SET`` and ``DEFAULT_SEARCHWEIGHT``."""
    attribute = AtlasAttributeDef.model_validate({})

    assert attribute.to_json() == {
        "isOptional": False,
        "cardinality": "SINGLE",
        "valuesMinCount": -1,
        "valuesMaxCount": -1,
        "isUnique": False,
        "isIndexable": False,
        "includeInNotification": False,
        "searchWeight": -1,
    }


@pytest.mark.covers(rules=["TDM-10"])
def test__an_explicit_null_reads_as_false_or_zero() -> None:
    """Jackson gives a primitive setter its default for null; ``setIncludeInNotification`` maps null to false."""
    attribute = AtlasAttributeDef.model_validate(
        {
            "isOptional": None,
            "valuesMinCount": None,
            "valuesMaxCount": None,
            "isUnique": None,
            "isIndexable": None,
            "includeInNotification": None,
            "searchWeight": None,
            "cardinality": None,
        }
    )

    assert attribute.to_json() == {
        "isOptional": False,
        "valuesMinCount": 0,
        "valuesMaxCount": 0,
        "isUnique": False,
        "isIndexable": False,
        "includeInNotification": False,
        "searchWeight": 0,
    }


@pytest.mark.covers(rules=["TDM-11"])
def test__an_empty_constraints_list_reads_as_null() -> None:
    """``setConstraints`` stores null for an empty list, so the field is not written."""
    attribute = AtlasAttributeDef.model_validate({"name": "a", "constraints": []})

    assert attribute.constraints is None
    assert "constraints" not in attribute.to_json()


@pytest.mark.covers(rules=["TDM-11"])
def test__options_are_copied() -> None:
    """``setOptions`` copies the map: changing the caller's map later does not change the definition."""
    options = {"k": "v"}
    attribute = AtlasAttributeDef(name="a", options=options)
    struct = AtlasStructDef(name="s", options=options)
    options["k"] = "changed"

    assert attribute.options == {"k": "v"}
    assert struct.options == {"k": "v"}


@pytest.mark.covers(rules=["TDM-12"])
def test__a_relationship_end_without_values_reads_as_javas_defaults() -> None:
    """``new AtlasRelationshipEndDef()`` is ``(null, null, SINGLE, false)`` and not a legacy attribute."""
    end = AtlasRelationshipEndDef.model_validate({"type": "table"})

    assert end.cardinality is Cardinality.SINGLE
    assert end.is_container is False
    assert end.is_legacy_attribute is False


@pytest.mark.covers(rules=["TDM-12"])
def test__a_relationship_keeps_category_tags_and_ends_null_when_not_given() -> None:
    """``AtlasRelationshipDef``'s setters store what they get; defaults come from the type registry (1.2)."""
    relationship = AtlasRelationshipDef.model_validate({"name": "r"})

    assert relationship.to_json() == {"name": "r", "category": "RELATIONSHIP", "attributeDefs": []}


@pytest.mark.covers(rules=["TDM-11"])
def test__constraints_given_in_code_are_kept() -> None:
    """A non-empty list is copied as given."""
    attribute = AtlasAttributeDef(name="a", constraints=[AtlasConstraintDef(type="ownedRef")])

    assert attribute.constraints == [AtlasConstraintDef(type="ownedRef")]
