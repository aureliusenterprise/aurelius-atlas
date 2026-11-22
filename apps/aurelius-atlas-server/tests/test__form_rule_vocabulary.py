"""The form-rule vocabulary the webapp editor copies, produced here (WFE-05, DD-805).

``form-fields.ts`` re-implements rules the server owns — the numeric types that get a
number input, the cardinality values, the 18.3 constraint names, and the two description
keys. The client guard (``form-rules.spec.ts``) fails when its copy drifts from the
fixture this module pins, and this module fails when the fixture drifts from the server,
so a server-side change can never leave the client copy behind quietly. Nothing here is
hand-copied: the numbers, cardinalities, constraint names, and type names come from the
server's own constants, and the description keys are probed out of ``view_of`` itself —
the same AVS-03 rule the details card reads.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.view_derivation import view_of
from aurelius_atlas_model.typedef import (
    ATLAS_PRIMITIVE_TYPES,
    ATLAS_TYPE_BOOLEAN,
    ATLAS_TYPE_DATE,
    ATLAS_TYPE_STRING,
    CONSTRAINT_PARAM_GROUP,
    CONSTRAINT_TYPE_MUTUAL_EXCLUSION,
    AtlasTypesDef,
    Cardinality,
    array_type_name,
)
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry

FIXTURE = Path(__file__).parents[3] / "apps/aurelius-atlas-webapp/tests/fixtures/form-rules.json"

PROBE_CANDIDATES = ("definition", "description", "summary", "comment")
"""Attribute names to probe for the card description (AVS-03): which of these
``view_of`` actually reads, and in what order. 18.8/SPA-05 retires the dictionary's
``definition``, so it joins ``summary`` and ``comment`` as a control: a plausible
prose key the server must no longer read, or the vocabulary would silently widen."""


def _probe_registry() -> tuple[TypeRegistry, EntityType]:
    """A registry with one type carrying every probe candidate (offline, no store)."""
    registry = TypeRegistry()
    types_def = AtlasTypesDef.model_validate(
        {
            "entityDefs": [
                {
                    "name": "probe",
                    "attributeDefs": [
                        {"name": name, "typeName": "string", "isOptional": True} for name in PROBE_CANDIDATES
                    ],
                }
            ]
        }
    )
    with registry.update() as transient:
        transient.add_types(types_def)
    entity_type = registry.entity_type("probe")
    assert entity_type is not None
    return registry, entity_type


def _probe_description_keys() -> list[str]:
    """The description keys the server reads, in the order it prefers them (AVS-03).

    Each candidate's value is its own name, so ``view_of`` answers with the key it
    chose; drop the winner and ask again, until it answers nothing.
    """
    _, entity_type = _probe_registry()

    def stored_excluding(excluded: set[str]) -> StoredEntity:
        attributes: dict[str, str] = {}
        for name in PROBE_CANDIDATES:
            if name in excluded:
                continue
            defining = entity_type.attribute(name)
            assert defining is not None, name
            attributes[defining.qualified_name] = name
        return StoredEntity(guid="g", type_name="probe", attributes=attributes)

    keys: list[str] = []
    while True:
        answer = view_of(stored_excluding(set(keys)), entity_type).definition
        if answer is None:
            return keys
        assert answer in PROBE_CANDIDATES, answer
        keys.append(answer)


def _numeric_types() -> list[str]:
    """The primitive types that are numbers: the primitives minus boolean and string (TDM-19)."""
    return sorted(set(ATLAS_PRIMITIVE_TYPES) - {ATLAS_TYPE_BOOLEAN, ATLAS_TYPE_STRING})


def produce_vocabulary() -> dict[str, Any]:
    """The vocabulary the client copy is guarded against, from the server's own rules."""
    array_prefix, array_suffix = array_type_name(ATLAS_TYPE_STRING).split(ATLAS_TYPE_STRING)
    return {
        "arrayPrefix": array_prefix,
        "arraySuffix": array_suffix,
        "booleanType": ATLAS_TYPE_BOOLEAN,
        "cardinalityMulti": [Cardinality.LIST.value, Cardinality.SET.value],
        "cardinalitySingle": Cardinality.SINGLE.value,
        "constraintGroupParam": CONSTRAINT_PARAM_GROUP,
        "constraintType": CONSTRAINT_TYPE_MUTUAL_EXCLUSION,
        "dateType": ATLAS_TYPE_DATE,
        "descriptionKeys": _probe_description_keys(),
        "numericTypes": _numeric_types(),
        "textType": ATLAS_TYPE_STRING,
    }


def render_fixture() -> bytes:
    """The fixture's bytes: sorted keys, four-space indent, one final newline."""
    return (json.dumps(produce_vocabulary(), indent=4, sort_keys=True) + "\n").encode()


@pytest.mark.covers(rules=["WFE-05"])
def test__fixture_is_the_vocabulary_the_server_produces() -> None:
    """The committed fixture equals, byte for byte, what these tests derive from the server (WFE-05, DD-805)."""
    assert FIXTURE.read_bytes() == render_fixture(), (
        "the fixture drifted from the server's vocabulary; after a deliberate rule "
        "change, regenerate it with `uv run python tools/form_rules_snapshot.py`"
    )


@pytest.mark.covers(rules=["WFE-05"])
def test__description_keys_are_the_one_the_card_reads() -> None:
    """The probe finds ``description`` and nothing else, not the retired ``definition`` (AVS-03, WFE-05, SPA-05)."""
    assert _probe_description_keys() == ["description"]
