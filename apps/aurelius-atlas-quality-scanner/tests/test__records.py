"""The score and ERROR entities (DQS-06, DQS-07, DQS-08): keys, attributes and verdicts."""

from __future__ import annotations

from typing import Any

import pytest
from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_quality_scanner.records import (
    ERROR_VERDICT,
    FAILED_VERDICT,
    PASSED_VERDICT,
    QUALIFIED_NAME_ROOT,
    error_entity,
    score_entity,
    score_key,
)

RULE_DOCUMENT: dict[str, Any] = {
    "typeName": "m4i_dq_score",
    "ruleGuid": "r1",
    "datasetGuid": "d3",
    "runId": "run-1",
    "runAtMs": 1_700_000_000_000,
    "dimension": "COMPLETENESS",
    "checkKind": "not_null",
    "score": 0.75,
    "passed": False,
    "rowsChecked": 4,
    "rowsFailed": 1,
}
"""A rule document as the engine's :func:`result_documents` answers it (12.1, DQ-08)."""

SUMMARY_DOCUMENT: dict[str, Any] = {
    "typeName": "m4i_dq_score",
    "ruleGuid": None,
    "datasetGuid": "d3",
    "runId": "run-1",
    "runAtMs": 1_700_000_000_000,
    "dimension": None,
    "checkKind": None,
    "score": 0.8,
    "passed": None,
    "rowsChecked": None,
    "rowsFailed": None,
    "dimensions": {"COMPLETENESS": 0.75, "VALIDITY": 1.0},
}
"""The dataset's summary document: no rule, no passed, a dimensions map."""


@pytest.mark.covers("aurelius_atlas_quality_scanner.records.score_key", rules=["DQS-06"])
def test_a_rule_document_keys_on_rule_and_dataset() -> None:
    """DQS-06: the key of a rule's score names its dataset and rule — one newest row per pair."""
    assert score_key(RULE_DOCUMENT) == "d3/r1"


@pytest.mark.covers("aurelius_atlas_quality_scanner.records.score_key", rules=["DQS-06"])
def test_the_summary_document_keys_on_the_dataset_alone() -> None:
    """DQS-06: the dataset's one summary carries the key ``{dataset}/overall``."""
    assert score_key(SUMMARY_DOCUMENT) == "d3/overall"


@pytest.mark.covers("aurelius_atlas_quality_scanner.records.score_entity", rules=["DQS-07"])
def test_a_rule_document_becomes_a_score_entity_with_every_attribute() -> None:
    """DQS-07: the entity carries each document attribute, the verdict, the key and the qualified name."""
    entity = score_entity(RULE_DOCUMENT)
    attributes = entity.attributes or {}
    assert entity.type_name == "m4i_dq_score"
    assert str(entity.guid).startswith("-")  # DQS-06: a temp internal id, never an assigned GUID
    for name in ("ruleGuid", "datasetGuid", "runId", "runAtMs", "dimension", "checkKind", "score", "rowsChecked"):
        assert attributes[name] == RULE_DOCUMENT[name]
    assert attributes["verdict"] == FAILED_VERDICT  # DQS-07: passed False reads as FAIL
    assert attributes["scoreKey"] == "d3/r1"
    assert attributes["qualifiedName"] == f"{QUALIFIED_NAME_ROOT}/d3/r1"


@pytest.mark.covers("aurelius_atlas_quality_scanner.records.score_entity", rules=["DQS-07"])
def test_a_passed_document_reads_as_a_pass_verdict() -> None:
    """DQS-07: a rule that passed its threshold carries PASS."""
    entity = score_entity({**RULE_DOCUMENT, "passed": True})
    assert (entity.attributes or {})["verdict"] == PASSED_VERDICT


@pytest.mark.covers("aurelius_atlas_quality_scanner.records.score_entity", rules=["DQS-07"])
def test_the_summary_keeps_its_dimension_scores_as_text() -> None:
    """DQS-07: the type's ``map<string,string>`` holds each dimension score as text."""
    entity = score_entity(SUMMARY_DOCUMENT, PASSED_VERDICT)
    attributes = entity.attributes or {}
    assert attributes["dimensions"] == {"COMPLETENESS": "0.75", "VALIDITY": "1.0"}
    assert attributes["verdict"] == PASSED_VERDICT  # the summary has no passed; the scan names the verdict
    assert "passed" not in attributes or attributes["passed"] is None


@pytest.mark.covers("aurelius_atlas_quality_scanner.records.error_entity", rules=["DQS-08"])
def test_a_rule_that_cannot_run_becomes_an_error_entity_with_the_cause() -> None:
    """DQS-08: the ERROR entity shares the score's key and ids, carries the cause, and no score."""
    entity = error_entity("r2", "d3", "run-1", 1_700_000_000_000, "column 'total' not found")
    attributes = entity.attributes or {}
    assert entity.type_name == "m4i_dq_score"
    assert attributes["verdict"] == ERROR_VERDICT
    assert attributes["scoreKey"] == "d3/r2"
    assert attributes["qualifiedName"] == f"{QUALIFIED_NAME_ROOT}/d3/r2"
    assert attributes["errorMessage"] == "column 'total' not found"
    assert attributes.get("score") is None
    assert "rowsChecked" not in attributes


@pytest.mark.covers("aurelius_atlas_quality_scanner.records.score_entity", rules=["DQS-06"])
def test_the_same_key_survives_a_round_trip_of_the_write_model() -> None:
    """DQS-06: two entities of one key serialise to the same unique key, which is what updates in place."""
    first = score_entity({**RULE_DOCUMENT, "score": 0.5})
    second = score_entity({**RULE_DOCUMENT, "score": 0.9})
    assert isinstance(first, AtlasEntity)
    keys = {(first.attributes or {})["scoreKey"], (second.attributes or {})["scoreKey"]}
    assert keys == {"d3/r1"}
