"""The glossary models (GLS-01, GLS-03, GCT-01, GCT-05).

Read from ``AtlasGlossary``, ``AtlasGlossaryCategory`` and their headers in Apache Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryHeader,
    AtlasRelatedCategoryHeader,
    AtlasRelatedTermHeader,
)

G = "aurelius_atlas_model.glossary"


@pytest.mark.covers(
    f"{G}.AtlasGlossary.set_attribute", f"{G}.AtlasGlossaryCategory.set_attribute", rules=["GLS-03", "GCT-05"]
)
def test__partial_updates_set_the_named_attributes_only() -> None:
    """A glossary takes name, descriptions, language and usage; a category name and descriptions."""
    glossary, category = AtlasGlossary(), AtlasGlossaryCategory()
    for name in ("name", "shortDescription", "longDescription", "language", "usage"):
        glossary.set_attribute(name, name)
    for name in ("name", "shortDescription", "longDescription"):
        category.set_attribute(name, name)
    assert (glossary.short_description, glossary.usage, category.long_description) == (
        "shortDescription",
        "usage",
        "longDescription",
    )
    with pytest.raises(ValueError, match="Invalid attribute 'qualifiedName' for object AtlasGlossary"):
        glossary.set_attribute("qualifiedName", "x")
    with pytest.raises(ValueError, match="Invalid attribute 'language' for object AtlasGlossaryCategory"):
        category.set_attribute("language", "x")


@pytest.mark.covers(
    f"{G}.AtlasGlossary.same_as",
    f"{G}.AtlasGlossaryCategory.same_as",
    f"{G}.AtlasGlossaryHeader.same_as",
    f"{G}.AtlasRelatedCategoryHeader.key",
    f"{G}.AtlasRelatedTermHeader.key",
    f"{G}.AtlasGlossaryBaseObject.base_key",
    rules=["GLS-03", "GCT-04"],
)
def test__equality_ignores_guids_display_texts_and_header_order() -> None:
    """``equals``: the fields and the headers as sets, not the GUID or the display text."""
    terms = [AtlasRelatedTermHeader(term_guid="t", display_text="T")]
    first = AtlasGlossary(guid="1", name="g", terms=terms, categories=[AtlasRelatedCategoryHeader(category_guid="a")])
    second = AtlasGlossary(
        guid="2",
        name="g",
        terms=[AtlasRelatedTermHeader(term_guid="t")],
        categories=[AtlasRelatedCategoryHeader(category_guid="a", display_text="A")],
    )
    assert first.same_as(second)
    assert not first.same_as(AtlasGlossary(name="g"))
    anchor = AtlasGlossaryHeader(glossary_guid="g", relation_guid="r")
    one = AtlasGlossaryCategory(name="c", anchor=anchor, parent_category=AtlasRelatedCategoryHeader(category_guid="p"))
    two = AtlasGlossaryCategory(
        name="c", anchor=anchor.model_copy(), parent_category=AtlasRelatedCategoryHeader(category_guid="p")
    )
    assert one.same_as(two)
    assert not one.same_as(AtlasGlossaryCategory(name="c", anchor=AtlasGlossaryHeader(glossary_guid="g")))
    assert not anchor.same_as(None)


def test__a_new_object_has_a_negative_guid_and_nulls_are_left_out() -> None:
    """``AtlasBaseModelObject.init``; Jackson's ``NON_NULL`` (GLS-01)."""
    first, second = AtlasGlossary(name="a"), AtlasGlossary(name="b")
    assert first.guid.startswith("-")
    assert first.guid != second.guid
    assert AtlasGlossaryCategory(guid="x", name="c").to_json() == {"guid": "x", "name": "c"}
