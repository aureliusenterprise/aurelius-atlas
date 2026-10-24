"""Dynamic attributes of an entity type: templates and their evaluation order (EWR-03, DD-054).

Read from ``AtlasEntityType`` (``parseDynAttributeTemplates``, ``templateSplit``, ``reorderDynAttributes``),
``AttributeToken``, ``ConstantToken`` and ``DependentToken`` of Apache Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_model.typedef import AtlasAttributeDef, AtlasEntityDef
from aurelius_atlas_typesystem.attribute_token import AttributeToken
from aurelius_atlas_typesystem.constant_token import ConstantToken
from aurelius_atlas_typesystem.dependent_token import DependentToken
from aurelius_atlas_typesystem.entity_type import EntityType, template_split
from aurelius_atlas_typesystem.registry import TypeRegistry

T = "aurelius_atlas_typesystem"


def entity_type(options: dict[str, str]) -> EntityType:
    """A registered entity type with string attributes ``a`` to ``d``, an int ``n`` and these options."""
    registry = TypeRegistry()
    attributes = [AtlasAttributeDef(name=name, type_name="string") for name in "abcd"]
    definition = AtlasEntityDef(
        name="dyn", attribute_defs=[*attributes, AtlasAttributeDef(name="n", type_name="int")], options=options
    )
    with registry.update() as transient:
        transient.add_type(definition)
    found = registry.entity_type("dyn")
    assert found is not None
    return found


@pytest.mark.covers(f"{T}.entity_type.template_split", rules=["EWR-03"])
def test__a_template_splits_into_constants_attributes_and_paths() -> None:
    """Text before a brace is a constant; ``{x}`` an attribute, ``{x.y}`` a path; trailing text is dropped."""
    assert template_split("db:{a}@{b.c}}x{{d}tail") == [
        ConstantToken("db:"),
        AttributeToken("a"),
        ConstantToken("@"),
        DependentToken("b.c"),
        ConstantToken("}x"),
        AttributeToken("d"),
    ]
    assert template_split("{open") == []
    assert DependentToken("x.y.z.").object_path == ["x", "y"]
    assert DependentToken("x.y.z.").attribute_name == "z"


@pytest.mark.covers(
    f"{T}.attribute_token.AttributeToken.eval",
    f"{T}.constant_token.ConstantToken.eval",
    f"{T}.dependent_token.DependentToken.eval",
    rules=["EWR-03"],
)
def test__tokens_evaluate_on_the_entity() -> None:
    """An attribute as Java's text, or None; a constant as it is; a path as ``TEMP``."""
    entity = AtlasEntity(type_name="dyn", attributes={"a": "x", "n": 3, "b": None})

    assert AttributeToken("a").eval(entity) == "x"
    assert AttributeToken("n").eval(entity) == "3"
    assert AttributeToken("b").eval(entity) is None
    assert ConstantToken("k").eval(entity) == "k"
    assert DependentToken("a.b").eval(entity) == "TEMP"


@pytest.mark.covers(rules=["EWR-03"])
def test__dynamic_attributes_are_ordered_so_that_what_a_template_reads_comes_first() -> None:
    """Only string attributes that exist; ``a`` reads ``b`` which reads ``c``: ``c``, ``b``, ``a`` (DD-054)."""
    found = entity_type(
        {
            "dynAttribute:a": "{b}-{d}",
            "dynAttribute:b": "{c}!",
            "dynAttribute:c": "fixed",
            "dynAttribute:n": "{a}",
            "dynAttribute:missing": "{a}",
            "other": "{a}",
        }
    )

    assert list(found.parsed_templates) == ["a", "b", "c"]
    assert [attribute.name for attribute in found.dyn_eval_attributes] == ["c", "b", "a"]
    assert [attribute.name for attribute in found.dyn_eval_trigger_attributes] == ["b", "d", "c"]
