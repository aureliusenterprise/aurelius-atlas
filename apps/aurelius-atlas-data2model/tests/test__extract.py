"""Unit tests for the extraction engine (DTM-01..DTM-09, DTM-12).

Each test names the rule it keeps (ADR 049). The fixtures are the smallest data
that shows the rule; the lineage caller's fixed rules (8.2) are exercised as a
whole by the parity scenario, not here.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from aurelius_atlas_data2model.extract import extract
from aurelius_atlas_data2model.rules import ExtractionRequest
from aurelius_atlas_data2model_client.models import ExtractionResponse

# The smallest rules that produce a node: one element rule over an `eid` column.
_ONE_ELEMENT: dict[str, Any] = {
    "elements": [{"id": "e1", "concept_type": "lineage_dataset", "id_key": "eid", "concept_name_key": "ename"}],
    "relations": [],
    "views": [],
}


def _request(data: list[dict[str, Any]], rules: dict[str, Any] | None = None) -> ExtractionResponse:
    """Run an extraction: data rows plus rules, the answer as the contract model."""
    return extract(ExtractionRequest.model_validate({"data": data, "rules": rules or _ONE_ELEMENT}))


def _model(answer: ExtractionResponse) -> dict[str, Any]:
    """The ar3 model the answer carries, parsed from its JSON string (DTM-01)."""
    return json.loads(answer.model)


def _identifiers(ar3: dict[str, Any]) -> list[str]:
    """The ids of the model's elements, in order."""
    return [element["@identifier"] for element in ar3["ar3_model"]["ar3_elements"]["ar3_element"]]


# ---------------------------------------------------------------------------
# DTM-02 — element rules read their id column
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-02"])
def test__element_rules_read_their_id_column() -> None:
    """Each row yields a node: id from id_key, name from concept_name_key, type from concept_type."""
    ar3 = _model(_request([{"eid": "a", "ename": "Alpha"}, {"eid": "b", "ename": "Beta"}]))
    elements = ar3["ar3_model"]["ar3_elements"]["ar3_element"]
    assert [e["@identifier"] for e in elements] == ["a", "b"]
    assert [e["@xsi_type"] for e in elements] == ["lineage_dataset", "lineage_dataset"]
    assert [e["ar3_name"][0]["value"] for e in elements] == ["Alpha", "Beta"]


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-02"])
def test__a_null_id_row_is_dropped() -> None:
    """A row whose id is null yields no node — and no 'nan' node (the stated deviation)."""
    ar3 = _model(_request([{"eid": None, "ename": "Ghost"}, {"eid": "a", "ename": "Alpha"}]))
    assert _identifiers(ar3) == ["a"]


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-02"])
def test__a_rule_for_an_absent_column_yields_nothing() -> None:
    """A rule whose id_key is not a column of the data is dropped."""
    rules: dict[str, Any] = {
        "elements": [{"id": "e1", "concept_type": "lineage_dataset", "id_key": "eid"}],
        "relations": [],
        "views": [],
    }
    ar3 = _model(_request([{"other": 1}], rules))
    assert ar3["ar3_model"]["ar3_elements"] == {"ar3_element": []}


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-02"])
def test__the_first_row_per_id_is_kept_per_rule() -> None:
    """Two rows sharing an id yield one node, from the first row (keep='first')."""
    ar3 = _model(_request([{"eid": "a", "ename": "First"}, {"eid": "a", "ename": "Second"}]))
    elements = ar3["ar3_model"]["ar3_elements"]["ar3_element"]
    assert len(elements) == 1
    assert elements[0]["ar3_name"][0]["value"] == "First"


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-02"])
def test__a_null_name_is_the_empty_string() -> None:
    """A null name is '' here, not the legacy's 'nan' string (the stated deviation)."""
    ar3 = _model(_request([{"eid": "a", "ename": None}]))
    element = ar3["ar3_model"]["ar3_elements"]["ar3_element"][0]
    assert element["ar3_name"][0]["value"] == ""


# ---------------------------------------------------------------------------
# DTM-03 — metadata names the source row per rule
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-03"])
def test__metadata_names_the_source_row_per_rule() -> None:
    """Every parsed row yields {id, data} with created_by, the id prefix/original id, and the mapping."""
    rules: dict[str, Any] = {
        "elements": [
            {
                "id": "e1",
                "concept_type": "lineage_dataset",
                "id_key": "eid",
                "concept_name_key": "ename",
                "id_prefix": "p:",
                "mapping": [{"key": "Type name", "value": "etype"}, {"key": "Missing", "value": "nope"}],
            }
        ],
        "relations": [],
        "views": [],
    }
    answer = _request([{"eid": "a", "ename": "A", "etype": "kafka_topic"}], rules)
    assert [entry.model_dump() for entry in answer.metadata] == [
        {
            "id": "p:a",
            "data": {
                "created_by": "Model Extractor API",
                "m4i_id_prefix": "p:",
                "m4i_original_id": "a",
                "Type name": "kafka_topic",
            },
        }
    ]


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-03"])
def test__metadata_lists_elements_then_relations_then_views() -> None:
    """The metadata is elements, relations, views, each in rule order."""
    rules: dict[str, Any] = {
        "elements": [
            {"id": "src", "concept_type": "lineage_dataset", "id_key": "eid"},
            {"id": "dst", "concept_type": "lineage_dataset", "id_key": "eid2"},
        ],
        "relations": [{"id": "r1", "relationship_type": "lr", "id_key": "rid", "source": "src", "target": "dst"}],
        "views": [
            {
                "id": "v1",
                "view_layout": "archimate_process",
                "id_type": "static",
                "id_value": "view",
                "view_name_type": "static",
                "view_name_value": "V",
                "view_nodes": [],
                "view_edges": [],
            }
        ],
    }
    answer = _request([{"eid": "a", "eid2": "b", "rid": "e1"}], rules)
    ids = [entry.data["m4i_original_id"] for entry in answer.metadata]
    assert ids == ["a", "b", "e1", "view"]


# ---------------------------------------------------------------------------
# DTM-04 — relation rules resolve their endpoint rules
# ---------------------------------------------------------------------------

_EDGE_RULES: dict[str, Any] = {
    "elements": [
        {"id": "src", "concept_type": "lineage_dataset", "id_key": "eid"},
        {"id": "dst", "concept_type": "lineage_dataset", "id_key": "eid2"},
    ],
    "relations": [{"id": "r1", "relationship_type": "lr", "id_key": "rid", "source": "src", "target": "dst"}],
    "views": [],
}


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-04"])
def test__relation_rules_resolve_their_endpoint_rules() -> None:
    """An edge runs from the source rule's id to the target rule's id, typed by the shorthand."""
    ar3 = _model(_request([{"eid": "a", "eid2": "b", "rid": "e1"}], _EDGE_RULES))
    relationship = ar3["ar3_model"]["ar3_relationships"]["ar3_relationship"][0]
    assert relationship["@identifier"] == "e1"
    assert relationship["@xsi_type"] == "lineage_relation"
    assert relationship["@source"] == "a"
    assert relationship["@target"] == "b"


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-04"])
def test__a_relation_row_with_a_null_endpoint_is_dropped() -> None:
    """A relation row with a null source or target yields no edge."""
    ar3 = _model(_request([{"eid": "a", "rid": "e1"}], _EDGE_RULES))
    assert ar3["ar3_model"]["ar3_relationships"] == {"ar3_relationship": []}


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-04"])
def test__every_edge_endpoint_is_a_model_node() -> None:
    """Every model edge's endpoints are model nodes (the legacy's membership filter).

    Over a validated rule the filter is defensive: the source/target keys are
    element rules, whose rows produce those nodes, so model and metadata stay in
    step, row for row.
    """
    data = [{"eid": "a", "eid2": "b", "rid": "e1"}, {"eid": "x", "eid2": "y", "rid": "e2"}]
    answer = _request(data, _EDGE_RULES)
    ar3 = _model(answer)
    relationships = ar3["ar3_model"]["ar3_relationships"]["ar3_relationship"]
    assert [r["@identifier"] for r in relationships] == ["e1", "e2"]
    node_ids = {e["@identifier"] for e in ar3["ar3_model"]["ar3_elements"]["ar3_element"]}
    sources = {r["@source"] for r in relationships}
    targets = {r["@target"] for r in relationships}
    assert sources <= node_ids
    assert targets <= node_ids
    metadata_ids = [entry.data["m4i_original_id"] for entry in answer.metadata]
    assert "e1" in metadata_ids
    assert "e2" in metadata_ids


# ---------------------------------------------------------------------------
# DTM-05 — model-wide dedup keeps the last
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-05"])
def test__duplicate_ids_keep_the_last_row() -> None:
    """The same node id from two rules: keep the last, at the kept row's position."""
    rules: dict[str, Any] = {
        "elements": [
            {"id": "r1", "concept_type": "lineage_dataset", "id_key": "eid", "concept_name_key": "ename"},
            {"id": "r2", "concept_type": "lineage_process", "id_key": "eid", "concept_name_key": "ename"},
        ],
        "relations": [],
        "views": [],
    }
    ar3 = _model(_request([{"eid": "a", "ename": "From r1"}, {"eid": "a", "ename": "From r2"}], rules))
    elements = ar3["ar3_model"]["ar3_elements"]["ar3_element"]
    assert len(elements) == 1
    assert elements[0]["@xsi_type"] == "lineage_process"


# ---------------------------------------------------------------------------
# DTM-06 — views: known layouts, static id/name
# ---------------------------------------------------------------------------

_KNOWN_VIEW: dict[str, Any] = {
    "elements": [{"id": "e1", "concept_type": "lineage_dataset", "id_key": "eid", "concept_name_key": "ename"}],
    "relations": [],
    "views": [
        {
            "id": "v1",
            "view_layout": "archimate_process",
            "id_type": "static",
            "id_value": "view",
            "view_name_type": "static",
            "view_name_value": "V",
            "view_nodes": [],
            "view_edges": [],
        }
    ],
}

_UNKNOWN_VIEW: dict[str, Any] = {**_KNOWN_VIEW, "views": [{**_KNOWN_VIEW["views"][0], "view_layout": "graphviz"}]}


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-06"])
def test__a_view_with_an_unknown_layout_is_ignored_entirely() -> None:
    """An unknown layout yields no view and no metadata."""
    answer = _request([{"eid": "a", "ename": "A"}], _UNKNOWN_VIEW)
    ar3 = _model(answer)
    assert ar3["ar3_model"]["ar3_views"]["ar3_diagrams"]["ar3_view"] == []
    assert [e.data["m4i_original_id"] for e in answer.metadata] == ["a"]


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-06"])
def test__a_static_view_takes_its_id_and_name_from_the_rule() -> None:
    """A static view is one diagram, ided and named by the rule."""
    ar3 = _model(_request([{"eid": "a", "ename": "A"}], _KNOWN_VIEW))
    views = ar3["ar3_model"]["ar3_views"]["ar3_diagrams"]["ar3_view"]
    assert [v["@identifier"] for v in views] == ["view"]
    assert views[0]["ar3_name"][0]["value"] == "V"


# ---------------------------------------------------------------------------
# DTM-07 — view node/edge collection
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-07"])
def test__view_nodes_are_collected_by_rule_and_intersected_with_the_model() -> None:
    """A view selects its nodes by its view_nodes rules, intersected with the model, in model order."""
    rules: dict[str, Any] = {
        "elements": [
            {"id": "src", "concept_type": "lineage_dataset", "id_key": "eid"},
            {"id": "dst", "concept_type": "lineage_dataset", "id_key": "eid2"},
        ],
        "relations": [{"id": "r1", "relationship_type": "lr", "id_key": "rid", "source": "src", "target": "dst"}],
        "views": [
            {
                "id": "v1",
                "view_layout": "archimate_process",
                "id_type": "static",
                "id_value": "view",
                "view_name_type": "static",
                "view_name_value": "V",
                "view_nodes": [{"rule": "dst"}, {"rule": "src"}],
                "view_edges": [],
            }
        ],
    }
    ar3 = _model(_request([{"eid": "a", "eid2": "b", "rid": "e1"}], rules))
    view = ar3["ar3_model"]["ar3_views"]["ar3_diagrams"]["ar3_view"][0]
    refs = [node["@elementRef"] for node in view["ar3_node"]]
    assert refs == ["a", "b"]
    assert [c["@relationshipRef"] for c in view["ar3_connection"]] == ["e1"]


# ---------------------------------------------------------------------------
# DTM-08 — the native layout
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-08"])
def test__the_layout_is_left_to_right_by_dependency_rank() -> None:
    """A → b → c lays out at x = 0, 320, 640; w=120, h=55."""
    rules: dict[str, Any] = {
        "elements": [
            {"id": "src", "concept_type": "lineage_dataset", "id_key": "eid"},
            {"id": "dst", "concept_type": "lineage_dataset", "id_key": "eid2"},
        ],
        "relations": [{"id": "r1", "relationship_type": "lr", "id_key": "rid", "source": "src", "target": "dst"}],
        "views": [
            {
                "id": "v1",
                "view_layout": "archimate_process",
                "id_type": "static",
                "id_value": "view",
                "view_name_type": "static",
                "view_name_value": "V",
                "view_nodes": [{"rule": "src"}, {"rule": "dst"}],
                "view_edges": [],
            }
        ],
    }
    ar3 = _model(_request([{"eid": "a", "eid2": "b", "rid": "e1"}, {"eid": "b", "eid2": "c", "rid": "e2"}], rules))
    view = ar3["ar3_model"]["ar3_views"]["ar3_diagrams"]["ar3_view"][0]
    by_ref = {node["@elementRef"]: node for node in view["ar3_node"]}
    assert by_ref["a"]["@x"] == 0
    assert by_ref["b"]["@x"] == 320
    assert by_ref["c"]["@x"] == 640
    assert by_ref["a"]["@w"] == 120
    assert by_ref["a"]["@h"] == 55


# ---------------------------------------------------------------------------
# DTM-09 — the ar3 shape
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-09"])
def test__the_model_string_follows_the_ar3_shape() -> None:
    """The model is {ar3_model: {...}} with the ar3 element/relationship/view keys."""
    ar3 = _model(_request([{"eid": "a", "ename": "A"}]))
    model = ar3["ar3_model"]
    assert model["@identifier"] == "Generated model"
    assert model["ar3_name"][0] == {"@xml_lang": "en", "value": "Generated model"}
    element = model["ar3_elements"]["ar3_element"][0]
    assert set(element) == {"@identifier", "@xsi_type", "ar3_name"}
    assert element["ar3_name"][0]["@xml_lang"] == "en"


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-09"])
def test__organizations_group_nodes_relations_and_views() -> None:
    """The organizations tree: nodes under a folder for their layer, views under Views."""
    ar3 = _model(_request([{"eid": "a", "ename": "A"}], _KNOWN_VIEW))
    root = ar3["ar3_model"]["ar3_organizations"][0]
    labels = [item["ar3_label"][0]["value"] for item in root["ar3_item"]]
    assert labels == ["Other", "Views"]
    other = root["ar3_item"][0]
    assert {"@identifierRef": "a"} in other["ar3_item"]


# ---------------------------------------------------------------------------
# DTM-12 — pydantic rules, plain rows
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-12"])
def test__rules_are_pydantic_models() -> None:
    """The request parses into pydantic rule models; the data stays plain row maps."""
    request = ExtractionRequest.model_validate({"data": [{"eid": "a"}], "rules": _ONE_ELEMENT})
    assert request.rules.elements[0].id == "e1"
    assert request.rules.elements[0].concept_type == "lineage_dataset"
    assert isinstance(request.data[0], dict)


@pytest.mark.covers("aurelius_atlas_data2model.extract.extract", rules=["DTM-12"])
def test__extra_rule_keys_are_ignored() -> None:
    """The caller's extra keys (alias, description, include, type) are ignored, as **kwargs were."""
    rules: dict[str, Any] = {
        "elements": [
            {
                "id": "e1",
                "concept_type": "lineage_dataset",
                "id_key": "eid",
                "concept_name_key": "ename",
                "alias": "Element rule for column eid",
                "description": "This rule generates a new element for every eid",
                "include": True,
                "type": "element",
            }
        ],
        "relations": [],
        "views": [],
    }
    ar3 = _model(_request([{"eid": "a", "ename": "A"}], rules))
    assert _identifiers(ar3) == ["a"]
