"""The card and the view: their field sets, their JSON, and the freshness fields (AVS-01, AVS-03..07).

The derivation of the stored fields is `aurelius-atlas-core`'s (``view_derivation``, AVS-02, AVS-08); these tests
hold the shape itself: the names a server, a Python client and the webapp's mirrored Angular models all share
(AVS-07), and the one JSON every Atlas model writes (AVS-05).
"""

import pytest
from aurelius_atlas_model.instance import EntityStatus
from aurelius_atlas_model.views import (
    CardBreadcrumb,
    CardQuality,
    EntityCard,
    EntityRelation,
    EntityView,
    RelationEntity,
)

V = "aurelius_atlas_model.views"


def view(**fields: object) -> EntityView:
    """A view of ``fields``, GUID and type filled in."""
    return EntityView.model_validate({"guid": "g", "typeName": "t"} | fields)


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["AVS-01"])
def test__a_card_holds_the_identity_the_derived_trail_the_relations_and_the_quality() -> None:
    """Every field AVS-01 names, under its wire name, and nothing else."""
    assert [str(info.alias) for info in EntityCard.model_fields.values()] == [
        "guid",
        "typeName",
        "superTypeNames",
        "name",
        "qualifiedName",
        "displayText",
        "definition",
        "status",
        "createTime",
        "updateTime",
        "createdBy",
        "updatedBy",
        "classificationNames",
        "labels",
        "breadcrumb",
        "relations",
        "quality",
        "governed",
        "stale",
    ]
    assert [str(info.alias) for info in CardBreadcrumb.model_fields.values()] == ["guid", "name", "typeName"]
    assert [str(info.alias) for info in CardQuality.model_fields.values()] == [
        "dimension",
        "score",
        "count",
        "total",
        "ruleGuids",
    ]
    assert [str(info.alias) for info in EntityRelation.model_fields.values()] == ["attribute", "entities"]
    assert [str(info.alias) for info in RelationEntity.model_fields.values()] == ["guid", "name", "typeName", "status"]


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["AVS-04"])
def test__a_view_is_a_card_plus_its_own_values_its_metadata_and_its_sections() -> None:
    """The card's fields plus attributes, businessMetadata and sections, nothing else (AVS-04)."""
    card = set(EntityCard.model_fields)
    extra = [str(info.alias) for name, info in EntityView.model_fields.items() if name not in card]
    assert extra == ["attributes", "businessMetadata", "sections"]


@pytest.mark.covers(f"{V}.EntityCard.of", rules=["AVS-04"])
def test__the_card_of_a_view_keeps_the_shared_fields_and_drops_the_own_ones() -> None:
    """The projection keeps the entity's own values and derived fields, and leaves out the view's three."""
    card = EntityCard.of(
        view(
            name="N",
            classificationNames=["PII"],
            breadcrumb=[{"guid": "d", "name": "Domain"}],
            attributes={"description": "kept out"},
            businessMetadata={"cost": {"centre": "C"}},
            sections=[{"attribute": "fields", "entities": [{"guid": "f"}]}],
        )
    )
    written = card.to_json()

    assert (card.name, [crumb.name for crumb in card.breadcrumb]) == ("N", ["Domain"])
    assert not {"attributes", "businessMetadata", "sections"} & set(written)


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["AVS-05"])
def test__a_card_writes_camel_case_names_and_no_null_keys() -> None:
    """Absent fields are left out; times write epoch millis; a list field stays even when empty (AVS-05)."""
    written = EntityCard.model_validate(
        {"guid": "g", "typeName": "t", "displayText": "d", "createTime": 1700000000000, "status": "DELETED"}
    ).to_json()

    assert written == {
        "guid": "g",
        "typeName": "t",
        "superTypeNames": [],
        "displayText": "d",
        "status": EntityStatus.DELETED,
        "createTime": 1700000000000,
        "classificationNames": [],
        "labels": [],
        "breadcrumb": [],
        "relations": [],
        "quality": [],
        "stale": False,
    }


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["AVS-03"])
def test__display_text_defaults_to_empty_text_and_a_card_needs_only_its_identity() -> None:
    """The rule's derivation is core's (AVS-02); the shape holds displayText as text, empty by default."""
    assert view().display_text == ""


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["AVS-06"])
def test__freshness_is_the_stale_mark_and_the_update_time_only() -> None:
    """Both freshness fields read from input; there is no other freshness claim in the shape (AVS-06)."""
    card = EntityCard.model_validate({"guid": "g", "typeName": "t", "stale": True, "updateTime": 42})

    assert (card.stale, card.to_json()["updateTime"]) == (True, 42)
    assert not {"freshness", "asOf", "indexedAt"} & set(EntityCard.model_fields)


@pytest.mark.covers(f"{V}.EntityCard.of", rules=["AVS-07"])
def test__the_models_are_the_shared_definition_the_doors_and_the_client_import() -> None:
    """They live in aurelius_atlas_model.views, the one definition every consumer mirrors (AVS-07)."""
    assert EntityCard.__module__ == "aurelius_atlas_model.views"
    assert EntityView.__module__ == "aurelius_atlas_model.views"
    assert issubclass(EntityView, EntityCard)
