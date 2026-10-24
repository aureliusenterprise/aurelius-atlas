"""Basic search's models (SRC-01), read from ``org.apache.atlas.model.discovery`` of Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.discovery import AtlasSearchResult, Operator, SearchParameters
from aurelius_atlas_model.instance import AtlasEntityHeader

D = "aurelius_atlas_model.discovery"


@pytest.mark.covers(f"{D}.Operator.from_symbol", f"{D}.Operator.symbols", rules=["SRC-01"])
def test__operators_read_any_symbol_and_write_their_first() -> None:
    """``begins_with`` reads as ``STARTS_WITH`` and writes ``startsWith``; an unknown symbol reads as none."""
    body = {
        "typeName": "t",
        "entityFilters": {
            "condition": "AND",
            "criterion": [
                {"attributeName": "name", "operator": "begins_with", "attributeValue": "a"},
                {"attributeName": "size", "operator": "<=", "attributeValue": "3"},
                {"attributeName": "x", "operator": "nope", "attributeValue": "y"},
            ],
        },
    }

    read = SearchParameters.model_validate(body)
    criterion = read.entity_filters.criterion if read.entity_filters else []

    assert [c.operator for c in criterion or []] == [Operator.STARTS_WITH, Operator.LTE, None]
    assert [c.get("operator") for c in read.to_json()["entityFilters"]["criterion"]] == ["startsWith", "<=", None]
    assert Operator.from_symbol(Operator.EQ) is Operator.EQ
    assert Operator.from_symbol(3) is None
    assert Operator.NOT_EMPTY.symbols[0] == "notEmpty"


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["SRC-01"])
def test__search_parameters_write_their_flags_and_defaults() -> None:
    """Sub types and sub classifications are included unless switched off; the other flags default to false."""
    written = SearchParameters.model_validate({"typeName": "t", "includeSubTypes": None}).to_json()

    assert written == {
        "typeName": "t",
        "excludeDeletedEntities": False,
        "includeClassificationAttributes": False,
        "includeSubTypes": True,
        "includeSubClassifications": True,
        "excludeHeaderAttributes": False,
        "limit": 0,
        "offset": 0,
    }


@pytest.mark.covers(f"{D}.AtlasSearchResult.add_entity", rules=["SRC-01", "SRC-09"])
def test__a_search_result_counts_minus_one_and_keeps_an_entity_once() -> None:
    """``approximateCount`` defaults to -1; an entity added again replaces the earlier one at the end."""
    result = AtlasSearchResult()
    for guid in ("a", "b", "a"):
        result.add_entity(AtlasEntityHeader(guid=guid, type_name="t"))

    assert [header.guid for header in result.entities or []] == ["b", "a"]
    assert AtlasSearchResult().to_json() == {"approximateCount": -1}
