"""What Atlas keeps of a definition (TDS-03, TDS-05, TDS-07).

Read from ``AtlasStructDefStoreV2`` and ``AtlasTypeDefGraphStoreV2`` of Apache Atlas 2.4.0.
"""

from datetime import UTC, datetime

import pytest
from aurelius_atlas_core.stored_form import (
    java_end_string,
    stamp_created,
    stamp_updated,
    stored_attribute,
    stored_typedef,
)
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasConstraintDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
)
from aurelius_atlas_typesystem.registry import TypeRegistry

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 2, 1, tzinfo=UTC)


@pytest.mark.covers(
    "aurelius_atlas_core.stored_form.stored_attribute",
    "aurelius_atlas_core.stored_form.stored_typedef",
    rules=["TDS-05"],
)
def test__an_inverse_reference_is_stored_and_other_constraints_dropped() -> None:
    """``reverseAttributeName`` keeps an ``inverseRef``; a struct keeps its plain kind."""
    registry = TypeRegistry()
    owner = AtlasAttributeDef(
        name="owner",
        type_name="t",
        is_optional=True,
        constraints=[AtlasConstraintDef(type="inverseRef", params={"attribute": "parts", "x": 1})],
    )
    with registry.update() as transient:
        transient.add_types(
            [
                AtlasEntityDef(
                    name="t", attribute_defs=[AtlasAttributeDef(name="parts", type_name="array<s>", is_optional=True)]
                ),
                AtlasEntityDef(name="s", attribute_defs=[owner]),
                AtlasStructDef(
                    name="plain", attribute_defs=[AtlasAttributeDef(name="a", type_name="int", is_optional=True)]
                ),
            ]
        )
    s, plain = registry.entity_type("s"), registry.struct_type("plain")
    assert s is not None
    assert plain is not None

    stored = stored_attribute(s.all_attributes["owner"])
    plain_def = stored_typedef(plain.struct_def, plain)

    assert [(c.type, c.params) for c in stored.constraints or []] == [("inverseRef", {"attribute": "parts"})]
    assert type(plain_def) is AtlasStructDef
    assert [a.name for a in plain_def.attribute_defs] == ["a"]


@pytest.mark.covers("aurelius_atlas_core.stored_form.stored_typedef", rules=["TDS-05"])
def test__an_enum_is_stored_with_values_ordinals_and_descriptions() -> None:
    """``AtlasEnumDefStoreV2.toVertex``: a blank element description is not stored."""
    enum = AtlasEnumDef(
        name="e",
        element_defs=[
            AtlasEnumElementDef(value="A", ordinal=1, description=" "),
            AtlasEnumElementDef(value="B", ordinal=2, description="b"),
        ],
        default_value="B",
    )

    stored = stored_typedef(enum, None)

    assert isinstance(stored, AtlasEnumDef)
    assert [(e.value, e.ordinal, e.description) for e in stored.element_defs] == [("A", 1, None), ("B", 2, "b")]
    assert (stored.default_value, stored.version) == ("B", 0)


@pytest.mark.covers("aurelius_atlas_core.stored_form.stamp_created", rules=["TDS-03"])
def test__a_created_definition_keeps_what_it_was_given() -> None:
    """``createTypeVertex`` fills in only what is missing; the user is always the current one."""
    typedef = AtlasEntityDef(name="t", version=7, create_time=T0, update_time=T0, created_by="someone")

    stamp_created(typedef, T1, "admin")

    assert (typedef.version, typedef.create_time, typedef.update_time) == (7, T0, T0)
    assert (typedef.created_by, typedef.updated_by, typedef.description) == ("admin", "admin", "t")


@pytest.mark.covers("aurelius_atlas_core.stored_form.stamp_updated", rules=["TDS-07"])
def test__an_updated_definition_keeps_identity_and_creation() -> None:
    """``updateTypeVertex``: blank fields keep their stored value; ``markVertexUpdated`` bumps the version."""
    stored = AtlasEntityDef(
        name="t",
        guid="g",
        description="d",
        type_version="1.0",
        service_type="svc",
        version=None,
        created_by="a",
        create_time=T0,
    )
    update = AtlasEntityDef(name="renamed", guid=" ", type_version="2.0")

    stamp_updated(update, stored, T1, "b")

    assert (update.name, update.guid, update.description, update.type_version, update.service_type) == (
        "t",
        "g",
        "d",
        "2.0",
        "svc",
    )
    assert (update.created_by, update.create_time, update.updated_by, update.update_time, update.version) == (
        "a",
        T0,
        "b",
        T1,
        1,
    )


@pytest.mark.covers("aurelius_atlas_core.stored_form.java_end_string", rules=["TDS-08"])
def test__an_end_is_written_as_java_writes_it() -> None:
    """``AtlasRelationshipEndDef.toString``; a missing end is ``null``."""
    end = AtlasRelationshipEndDef(type="t", name="n", description="d", is_container=True, cardinality=None)

    assert java_end_string(end) == (
        "AtlasRelationshipEndDef{type='t', name==>'n', description==>'d', isContainer==>'true', "
        "cardinality==>'null', isLegacyAttribute==>'false'}"
    )
    assert java_end_string(None) == "null"
