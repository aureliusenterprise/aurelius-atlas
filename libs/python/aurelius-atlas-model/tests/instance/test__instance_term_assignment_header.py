"""``AtlasTermAssignmentHeader`` (ENT-15).

Read from ``glossary.relations.AtlasTermAssignmentHeader`` and ``annotation.AtlasJSON`` of Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.instance import AtlasEntity, AtlasTermAssignmentHeader


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-15"])
def test__a_term_assignment_header_reads_and_writes_its_fields() -> None:
    """Every getter of the header."""
    body = {
        "termGuid": "t",
        "relationGuid": "r",
        "description": "d",
        "displayText": "term",
        "expression": "e",
        "createdBy": "admin",
        "steward": "s",
        "source": "src",
        "confidence": 50,
        "status": "DISCOVERED",
        "qualifiedName": "term@glossary",
    }

    assert AtlasTermAssignmentHeader.model_validate(body).to_json() == body


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["ENT-15"])
def test__empty_strings_are_left_out_but_confidence_is_always_written() -> None:
    """``NON_EMPTY`` leaves out nulls and empty strings, also inside an entity; an ``int`` is never empty."""
    header = AtlasTermAssignmentHeader.model_validate({"termGuid": "t", "description": "", "confidence": None})

    assert header.to_json() == {"termGuid": "t", "confidence": 0}
    assert AtlasEntity(meanings=[header]).to_json()["meanings"] == [{"termGuid": "t", "confidence": 0}]
