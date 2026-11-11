"""The rule vocabulary endpoints of the server (QRE-01 to QRE-05), on the fake store.

The routes hold no store call (QRE-04): the tests compare the kinds answer with the engine's own
``KINDS`` map, pair each validate answer with a rule ``rule_from_atlas_attributes`` parses or
raises on, and check the posture (signed-in, the same for every user) and Atlas's own endpoints.
"""

from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_quality import CASTABLE_TYPES, KINDS, QualityRuleError, rule_from_atlas_attributes
from fake_issuer import FakeIssuer
from fastapi import FastAPI

R = "aurelius_atlas_server.routes.quality"
BASE_URL = "https://aurelius-atlas"
"""The in-process server's address, as the conftest client rides it (AUT-05). Named here, not imported
from the conftest: the trace tool's collection can resolve ``conftest`` to the e2e one (the 11.5 pair's
blocker), and the value is the shared constant."""
KINDS_PATH = "/api/aurelius/v1/quality/kinds"
VALIDATE_PATH = "/api/aurelius/v1/quality/rules/validate"

VALID_RULE: dict[str, Any] = {
    "name": "orders total filled",
    "active": True,
    "dqcheckkind": "COLUMN_NOT_NULL_RATIO",
    "dqcolumn": "total",
    "threshold": 0.95,
}
"""A rule of the vocabulary (DQ-01's new names): the engine parses it."""

LEGACY_RULE: dict[str, Any] = {
    "name": "legacy unique id",
    "dataqualitytype": "attribute",
    "dataqualityoperator": "UNIQUE",
    "columnname": "id",
}
"""A legacy pair rule (DQ-07): the engine's pair map reads it, so the endpoint calls it valid."""

BROKEN_RULE: dict[str, Any] = {
    "name": "bad kind",
    "dqcheckkind": "COLUMN_IS_NICE",
}
"""A kind the vocabulary does not hold (DQ-02): the engine raises, the endpoint answers the reason."""


@pytest.mark.covers(f"{R}.quality_kinds", rules=["QRE-01"])
async def test__the_kinds_answer_the_vocabulary_the_engine_holds(client: httpx.AsyncClient) -> None:
    """Every ``KINDS`` entry, sorted, with the castable types and the threshold bounds (DD-473)."""
    response = await client.get(KINDS_PATH)

    assert response.status_code == 200
    body = response.json()
    assert [entry["name"] for entry in body["kinds"]] == sorted(kind.value for kind in KINDS)
    for entry in body["kinds"]:
        spec = KINDS[entry["name"]]
        assert (entry["dimension"], entry["required"], entry["optional"], entry["reason"]) == (
            spec.dimension.value,
            sorted(spec.required),
            sorted(spec.optional),
            spec.reason,
        )
    assert body["thresholdMin"] == 0.0
    assert body["thresholdMax"] == 1.0
    assert body["castableTypes"] == sorted(CASTABLE_TYPES)


@pytest.mark.covers(f"{R}.validate_quality_rule", rules=["QRE-02"])
async def test__a_rule_of_the_vocabulary_validates_with_its_kind_and_dimension(client: httpx.AsyncClient) -> None:
    """The engine's parse decides: the answer names the kind and dimension it read (DD-474)."""
    response = await client.post(VALIDATE_PATH, json=VALID_RULE)

    assert response.status_code == 200
    assert response.json() == {"valid": True, "kind": "COLUMN_NOT_NULL_RATIO", "dimension": "COMPLETENESS"}


@pytest.mark.covers(f"{R}.validate_quality_rule", rules=["QRE-02"])
async def test__a_legacy_pair_rule_validates_through_the_pair_map(client: httpx.AsyncClient) -> None:
    """DQ-07's pair reads as the vocabulary rule it maps to, so 7.27's legacy rule opens in the generic form."""
    response = await client.post(VALIDATE_PATH, json=LEGACY_RULE)

    assert response.status_code == 200
    assert response.json() == {"valid": True, "kind": "COLUMN_UNIQUE_RATIO", "dimension": "UNIQUENESS"}


@pytest.mark.covers(f"{R}.validate_quality_rule", rules=["QRE-03"])
async def test__an_unreadable_rule_answers_the_engine_reason_as_200(client: httpx.AsyncClient) -> None:
    """The engine's own sentence, on a 200: an unreadable rule is the product, not a rejected request."""
    response = await client.post(VALIDATE_PATH, json=BROKEN_RULE)

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert "COLUMN_IS_NICE" in body["reason"]
    with pytest.raises(QualityRuleError, match="COLUMN_IS_NICE") as raised:  # the same text (DD-474)
        rule_from_atlas_attributes(BROKEN_RULE)
    assert body["reason"] == str(raised.value)


@pytest.mark.covers(f"{R}.validate_quality_rule", rules=["QRE-03"])
async def test__a_missing_parameter_names_the_parameter(client: httpx.AsyncClient) -> None:
    """The parse-time check is the engine's: a kind without its column answers the engine's missing text."""
    response = await client.post(VALIDATE_PATH, json={"name": "no column", "dqcheckkind": "COLUMN_NOT_NULL_RATIO"})

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "column" in response.json()["reason"]


@pytest.mark.covers(f"{R}.validate_quality_rule", rules=["QRE-03"])
async def test__a_body_that_is_no_object_answers_400_in_atlas_shape(client: httpx.AsyncClient) -> None:
    """Only a non-object body is a bad request: the Atlas error shape, like every 400 (SRV-04)."""
    response = await client.post(VALIDATE_PATH, json=["not", "a", "rule"])

    assert response.status_code == 400
    assert response.json()["errorCode"].startswith("ATLAS-400")


@pytest.mark.covers(f"{R}.quality_kinds", rules=["QRE-04"])
@pytest.mark.covers(f"{R}.validate_quality_rule", rules=["QRE-04"])
async def test__both_need_a_signed_in_user(client: httpx.AsyncClient) -> None:
    """Without a token: 401, as every API path (the middleware, not the route)."""
    kinds = await client.get(KINDS_PATH, headers={"authorization": ""})
    validate = await client.post(VALIDATE_PATH, json=VALID_RULE, headers={"authorization": ""})

    assert (kinds.status_code, validate.status_code) == (401, 401)


@pytest.mark.covers(f"{R}.quality_kinds", rules=["QRE-04"])
async def test__a_role_less_user_gets_the_same_answer(app: FastAPI, issuer: FakeIssuer) -> None:
    """The vocabulary is the engine's, not the store's: an Atlas-role-less user sees the same answer (QRE-04)."""
    token = {"Authorization": f"Bearer {issuer.token(user='reader', atlas_roles=())}"}

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, headers=token) as reader:
            response = await reader.get(KINDS_PATH)

    assert response.status_code == 200
    assert [entry["name"] for entry in response.json()["kinds"]] == sorted(kind.value for kind in KINDS)


@pytest.mark.covers(rules=["QRE-05"])
async def test__atlas_s_own_endpoints_answer_as_before(client: httpx.AsyncClient) -> None:
    """The new router joins the include list without touching Atlas's surface (ADR 046)."""
    response = await client.get("/api/atlas/v2/types/typedefs")

    assert response.status_code == 200
    assert response.json()["enumDefs"] == []
