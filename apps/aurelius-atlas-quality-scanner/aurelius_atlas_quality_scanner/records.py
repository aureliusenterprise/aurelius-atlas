"""The engine's score documents, and an ERROR finding, as the entities to store (12.2, DQS-06, DQS-07, DQS-08).

A score document (12.1, DQ-08) becomes an ``m4i_dq_score`` entity whose unique ``scoreKey`` names
the rule and dataset it scores: the write updates the entity with that key, so the store keeps the
newest scan per rule and dataset (DD-456). A rule that cannot run becomes the same key with the
ERROR verdict and no score (DQS-08).
"""

from typing import Any, Literal

from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_quality import SCORE_TYPE_NAME

type Verdict = Literal["PASS", "FAIL", "ERROR"]
"""The verdicts a stored score entity carries (DQS-07, DQS-08)."""

PASSED_VERDICT: Verdict = "PASS"
"""The verdict of a rule that passed (DQS-07)."""

FAILED_VERDICT: Verdict = "FAIL"
"""The verdict of a rule that did not reach its threshold (DQS-07)."""

ERROR_VERDICT: Verdict = "ERROR"
"""The verdict of a rule that could not run over the extract (DQS-08)."""

OVERALL = "overall"
"""The rule part of a summary document's key (DQS-06)."""

QUALIFIED_NAME_ROOT = "dq-score"
"""The root qualified names are made under, by key (DQS-07): one entity per key."""

SCORE_ATTRIBUTES: tuple[str, ...] = (
    "ruleGuid",
    "datasetGuid",
    "runId",
    "runAtMs",
    "dimension",
    "checkKind",
    "score",
    "passed",
    "rowsChecked",
    "rowsFailed",
)
"""The document attributes an entity carries, as the type names them (DQS-07)."""


def score_key(document: dict[str, Any]) -> str:
    """The key of a score document: ``{datasetGuid}/{ruleGuid}``, or ``{datasetGuid}/overall`` (DQS-06)."""
    rule_guid = document.get("ruleGuid")
    return f"{document['datasetGuid']}/{OVERALL if rule_guid is None else rule_guid}"


def score_entity(document: dict[str, Any], verdict: Verdict | None = None) -> AtlasEntity:
    """The entity of one score document: its attributes, the verdict, and its key (DQS-06, DQS-07).

    The verdict is ``PASS`` or ``FAIL`` from the document's ``passed``, unless the caller names one
    — the summary document has no ``passed``, and the scan answers its verdict from the rule rows
    (every scored rule passed). The entity carries no assigned GUID — only the temp internal id
    the write model defaults to: the store resolves it by the unique ``scoreKey`` and updates the
    entity with that key in place (EWR-05/EWR-06). The summary's
    ``dimensions`` map is stored with every value as text, the shape the type's
    ``map<string,string>`` holds; the entity's ``qualifiedName`` is the key under
    :data:`QUALIFIED_NAME_ROOT`.
    """
    if verdict is None:
        verdict = PASSED_VERDICT if document.get("passed") else FAILED_VERDICT
    key = score_key(document)
    attributes: dict[str, Any] = {name: document.get(name) for name in SCORE_ATTRIBUTES}
    attributes["verdict"] = verdict
    attributes["scoreKey"] = key
    attributes["qualifiedName"] = f"{QUALIFIED_NAME_ROOT}/{key}"
    dimensions = document.get("dimensions")
    if dimensions:
        attributes["dimensions"] = {str(name): str(score) for name, score in dimensions.items()}
    return AtlasEntity(type_name=SCORE_TYPE_NAME, attributes=attributes)


def error_entity(rule_guid: str, dataset_guid: str, run_id: str, run_at_ms: int, cause: str) -> AtlasEntity:
    """The ERROR entity of a rule that could not run over one dataset's extract (DQS-08).

    The same key and ids a score would carry, the ERROR verdict, and ``errorMessage`` naming the
    cause; no score, and no row counts — nothing was measured. The qualified name is the score's,
    so a re-run that repairs the rule updates the same entity (the store replaces the stored
    attributes, so the stale ``errorMessage`` is gone with the old verdict).
    """
    key = f"{dataset_guid}/{rule_guid}"
    attributes: dict[str, Any] = {
        "ruleGuid": rule_guid,
        "datasetGuid": dataset_guid,
        "runId": run_id,
        "runAtMs": run_at_ms,
        "verdict": ERROR_VERDICT,
        "scoreKey": key,
        "qualifiedName": f"{QUALIFIED_NAME_ROOT}/{key}",
        "errorMessage": cause,
    }
    return AtlasEntity(type_name=SCORE_TYPE_NAME, attributes=attributes)
