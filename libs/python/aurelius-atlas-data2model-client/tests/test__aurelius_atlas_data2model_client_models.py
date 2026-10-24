"""The rules family and the extract shapes, as the client lib owns them (CL-20).

The models moved here from 8.1's app module; the DTM-11 validation is the
request contract, stated once for both sides of the wire (DD-114).
"""

from typing import Any

import pytest
from aurelius_atlas_data2model_client.models import (
    UNKNOWN_CONCEPT_TYPE_ERROR,
    UNKNOWN_ELEMENT_RULE_ERROR,
    ElementRule,
    ExtractionRequest,
    ExtractionResponse,
    LegacyStr,  # noqa: F401 - the name the contract states (CL-20)
    MappingEntry,
    MetadataEntry,
    RelationRule,
    RulesDef,
)
from pydantic import ValidationError

# The minimal rules document the 8.2 chain sends, as the contract states it.
LINEAGE_RULES: dict[str, Any] = {
    "elements": [
        {"id": "dataset", "id_key": "id", "concept_type": "lineage_dataset", "concept_name_key": "name"},
        {"id": "process", "id_key": "id", "concept_type": "lineage_process", "concept_name_key": "name"},
    ],
    "relations": [{"id": "edge", "id_key": "id", "relationship_type": "lr", "source": "dataset", "target": "process"}],
    "views": [
        {
            "id": "view",
            "view_layout": "archimate_process",
            "id_type": "static",
            "id_value": "lineage_view",
            "view_name_type": "static",
            "view_name_value": "Lineage",
            "view_nodes": [{"rule": "dataset"}, {"rule": "process"}],
        }
    ],
}


@pytest.mark.covers(rules=["CL-20"])
def test__the_lineage_rules_document_parses_as_the_contract() -> None:
    """The document 8.2 posts is a valid ``RulesDef`` — one contract for caller and server (CL-21)."""
    rules = RulesDef.model_validate(LINEAGE_RULES)

    assert [rule.id for rule in rules.elements] == ["dataset", "process"]
    assert rules.relations[0].relationship_type == "lr"
    assert rules.views[0].view_nodes[1].rule == "process"


@pytest.mark.covers(rules=["CL-20"])
def test__nulls_normalise_to_empty_strings_as_the_legacy_adapters_did() -> None:
    """``LegacyStr``: the lineage chain sends nulls for the prefixes, the contract reads '' (DTM-11)."""
    rule = ElementRule.model_validate(
        {"id": None, "id_key": "id", "concept_type": "lineage_dataset", "id_prefix": None, "concept_name_key": None}
    )

    assert rule.id == ""
    assert rule.id_prefix == ""
    assert rule.concept_name_key == ""


@pytest.mark.covers(rules=["CL-20"])
def test__an_unknown_concept_type_is_rejected() -> None:
    """A concept type outside the ported table is the DTM-11 400, not a 500 (the legacy's KeyError)."""
    with pytest.raises(ValidationError, match="unknown concept type"):
        ElementRule.model_validate({"id_key": "id", "concept_type": "lineage_nonsense"})
    assert "{value!r}" in UNKNOWN_CONCEPT_TYPE_ERROR  # the message names the offender


@pytest.mark.covers(rules=["CL-20"])
def test__an_unknown_relationship_type_is_rejected() -> None:
    """``relationship_type`` is validated against the shorthand table (DTM-11)."""
    with pytest.raises(ValidationError, match="unknown relationship type"):
        RelationRule.model_validate({"id_key": "id", "relationship_type": "nonsense"})


@pytest.mark.covers(rules=["CL-20"])
def test__a_dangling_relation_reference_is_named_in_the_error() -> None:
    """A source/target naming no element rule: the port names the offender, the legacy raised KeyError."""
    with pytest.raises(ValidationError) as raised:
        RulesDef.model_validate(
            {
                "elements": [{"id": "dataset", "id_key": "id", "concept_type": "lineage_dataset"}],
                "relations": [
                    {
                        "id": "edge",
                        "id_key": "id",
                        "relationship_type": "lr",
                        "source": "missing",
                        "target": "dataset",
                    }
                ],
            }
        )

    assert UNKNOWN_ELEMENT_RULE_ERROR.format(rule="edge", side="source", ref="missing") in str(raised.value)


@pytest.mark.covers(rules=["CL-20"])
def test__a_dangling_view_reference_is_rejected() -> None:
    """A view naming no element rule is the same 400 family (DTM-11)."""
    with pytest.raises(ValidationError, match="unknown element rule"):
        RulesDef.model_validate({"views": [{"id": "view", "view_nodes": [{"rule": "missing"}]}]})
    with pytest.raises(ValidationError, match="unknown relation rule"):
        RulesDef.model_validate({"views": [{"id": "view", "view_edges": [{"rule": "missing"}]}]})


@pytest.mark.covers(rules=["CL-20"])
def test__extra_keys_are_ignored_as_the_kwargs_adapters_did() -> None:
    """``alias``, ``description``, ``include``: the legacy adapters tolerated them (DTM-11)."""
    rule = ElementRule.model_validate(
        {"id_key": "id", "concept_type": "lineage_dataset", "alias": "a", "description": "d", "include": True}
    )

    assert rule.concept_type == "lineage_dataset"


@pytest.mark.covers(rules=["CL-20"])
def test__a_mapping_entry_maps_a_column_to_an_attribute() -> None:
    """``{key, value}``: the metadata attribute and its source column (DTM-03)."""
    entry = MappingEntry.model_validate({"id": "m", "key": "m4i_id", "value": "guid"})

    assert (entry.key, entry.value) == ("m4i_id", "guid")


@pytest.mark.covers(rules=["CL-20"])
def test__the_request_defaults_to_the_empty_extraction() -> None:
    """Absent data/rules is the empty extraction the legacy answers with the skeleton (DTM-11)."""
    request = ExtractionRequest.model_validate({})

    assert request.data == []
    assert request.rules.elements == []


@pytest.mark.covers(rules=["CL-20"])
def test__the_response_states_the_answer_the_apps_send() -> None:
    """``{metadata: [{id, data}], model: "<ar3 JSON string>"}`` — the model is a string (DV-51)."""
    response = ExtractionResponse.model_validate(
        {"metadata": [{"id": "n-1", "data": {"created_by": "dataset"}}], "model": '{"ar3_model": {}}', "extra": 1}
    )

    assert response.metadata == [MetadataEntry(id="n-1", data={"created_by": "dataset"})]
    assert response.model == '{"ar3_model": {}}'


@pytest.mark.covers(rules=["CL-20"])
def test__the_request_serialises_the_legacy_wire_keys() -> None:
    """The dump a client posts: snake_case in the model, the legacy keys on the wire (CL-06)."""
    body = ExtractionRequest.model_validate(
        {
            "data": [{"id": "e-1"}],
            "rules": {"elements": [{"id": "d", "id_key": "id", "concept_type": "lineage_dataset"}]},
        }
    ).model_dump(mode="json", by_alias=True)

    assert body["data"] == [{"id": "e-1"}]
    assert body["rules"]["elements"][0]["concept_type"] == "lineage_dataset"
    assert body["rules"]["elements"][0]["id_prefix"] == ""
