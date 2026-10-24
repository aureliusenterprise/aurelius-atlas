"""The governance-quality document, as the client lib owns it (CL-40; DD-203).

The card the 8.3 mock answers — the editor's contract (VE-02) — stated once so
the app's constant and a caller's parse validate one model.
"""

from typing import Any

import pytest
from aurelius_atlas_validate_entity_client.models import (
    GovQualityItem,
    GovQualityMeta,
    GovQualityValue,
    ValidationCard,
    ValidationResponse,
)
from pydantic import ValidationError


def _card(raw: str, compliant: str) -> dict[str, Any]:
    """One card, as the mock emits it: the raw wrappers, the string verdict, the doc id."""
    return {
        "items": [
            {
                "result": {"raw": raw},
                "dataqualitytype": {"raw": "attribute"},
                "usedattributes": {"raw": ["name"]},
                "name": {"raw": f"Attribute - {compliant}"},
                "compliant": {"raw": compliant},
                "_meta": {"engine": "atlas-dev-gov-quality", "score": 1, "id": "doc-1"},
                "id": {"raw": "doc-1"},
            }
        ],
        "isNonCompliant": compliant == "0",
    }


ANSWER: dict[str, Any] = {
    "dataEntity": _card("This entity is missing a dataEntity", "0"),
    "definition": _card("This entity has a definition", "1"),
    "domainLead": _card("This entity is missing a domainLead", "0"),
    "name": _card("This entity has a name", "1"),
}


@pytest.mark.covers(rules=["CL-40"])
def test__the_four_cards_parse_as_the_editor_receives_them() -> None:
    """``dataEntity``/``definition``/``domainLead``/``name``, the legacy's keys (VE-02)."""
    response = ValidationResponse.model_validate(ANSWER)

    assert response.data_entity.is_non_compliant is True
    assert response.definition.is_non_compliant is False
    assert response.domain_lead.items[0].compliant.raw == "0"
    assert response.name.items[0].name.raw == "Attribute - 1"


@pytest.mark.covers(rules=["CL-40"])
def test__every_leaf_is_a_raw_wrapper() -> None:
    """The ``{"raw": …}`` shape is the browser contract, modelled as it arrives."""
    value = GovQualityValue.model_validate({"raw": ["dataEntity"]})

    assert value.raw == ["dataEntity"]


@pytest.mark.covers(rules=["CL-40"])
def test__the_meta_keeps_the_engines_record() -> None:
    """``_meta``: the engine, the score, the document id (the mock's DV-67 values)."""
    meta = GovQualityMeta.model_validate({"engine": "atlas-dev-gov-quality", "score": 1, "id": "doc-1"})

    assert meta.engine == "atlas-dev-gov-quality"


@pytest.mark.covers(rules=["CL-40"])
def test__an_unknown_field_is_a_validation_error() -> None:
    """``extra='forbid'``: a card the legacy does not send is not the contract, not silence."""
    with pytest.raises(ValidationError):
        ValidationCard.model_validate({"items": [], "isNonCompliant": False, "surprise": 1})


@pytest.mark.covers(rules=["CL-40"])
def test__the_document_is_immutable_once_parsed() -> None:
    """Frozen models: the validated card cannot drift from the wire."""
    card = ValidationCard.model_validate(_card("r", "1"))

    with pytest.raises(ValidationError):
        card.is_non_compliant = True


@pytest.mark.covers(rules=["CL-40"])
def test__an_item_needs_every_check_field() -> None:
    """The item is exact: a missing verdict leaf is a validation error (VE-02)."""
    with pytest.raises(ValidationError):
        GovQualityItem.model_validate({"result": {"raw": "r"}})
