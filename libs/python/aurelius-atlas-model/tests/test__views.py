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
    CardVerdict,
    ClassificationSource,
    EntityCard,
    EntityRelation,
    EntityView,
    RelationEntity,
    RuleScore,
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
        "typeAlias",
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
        "verdicts",
        "governed",
        "stale",
        "hasParent",
        "propagatedClassifications",
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
    assert [str(info.alias) for info in RelationEntity.model_fields.values()] == [
        "guid",
        "name",
        "typeName",
        "status",
        "breadcrumb",
    ]
    assert [str(info.alias) for info in ClassificationSource.model_fields.values()] == ["typeName", "entities"]
    assert [str(info.alias) for info in CardVerdict.model_fields.values()] == ["rule", "name", "message"]


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["AVS-04"])
def test__a_view_is_a_card_plus_its_own_values_its_metadata_its_sections_and_its_rule_scores() -> None:
    """The card's fields plus attributes, businessMetadata, sections and ruleScores (AVS-04, AVS-13)."""
    card = set(EntityCard.model_fields)
    extra = [str(info.alias) for name, info in EntityView.model_fields.items() if name not in card]
    assert extra == ["attributes", "businessMetadata", "sections", "ruleScores"]
    assert [str(info.alias) for info in RuleScore.model_fields.values()] == [
        "rule",
        "name",
        "dimension",
        "score",
    ]


@pytest.mark.covers(f"{V}.EntityCard.of", rules=["AVS-04"])
def test__the_card_of_a_view_keeps_the_shared_fields_and_drops_the_own_ones() -> None:
    """The projection keeps the entity's own values and derived fields, and leaves out the view's own four."""
    card = EntityCard.of(
        view(
            name="N",
            classificationNames=["PII"],
            breadcrumb=[{"guid": "d", "name": "Domain"}],
            attributes={"description": "kept out"},
            businessMetadata={"cost": {"centre": "C"}},
            sections=[{"attribute": "fields", "entities": [{"guid": "f"}]}],
            propagatedClassifications=[{"typeName": "PII", "entities": [{"guid": "s"}]}],
            ruleScores=[{"rule": "r-1", "name": "Alpha rule", "dimension": "Accuracy", "score": 0.9}],
        )
    )
    written = card.to_json()

    assert (card.name, [crumb.name for crumb in card.breadcrumb]) == ("N", ["Domain"])
    # a result line names the propagation too, so the card keeps the field with its sources (VDR-12, DD-836)
    assert written["propagatedClassifications"] == [{"typeName": "PII", "entities": [{"guid": "s"}]}]
    assert not {"attributes", "businessMetadata", "sections", "ruleScores"} & set(written)


@pytest.mark.covers("aurelius_atlas_model.base.AtlasModel.to_json", rules=["AVS-05"])
def test__a_card_writes_camel_case_names_and_no_null_keys() -> None:
    """Absent fields are left out; times write epoch millis; a list field stays even when empty (AVS-05)."""
    written = EntityCard.model_validate(
        {
            "guid": "g",
            "typeName": "t",
            "displayText": "d",
            "typeAlias": "Data Set",
            "createTime": 1700000000000,
            "status": "DELETED",
        }
    ).to_json()

    assert written == {
        "guid": "g",
        "typeName": "t",
        "superTypeNames": [],
        "displayText": "d",
        "typeAlias": "Data Set",
        "status": EntityStatus.DELETED,
        "createTime": 1700000000000,
        "classificationNames": [],
        "labels": [],
        "breadcrumb": [],
        "relations": [],
        "quality": [],
        "verdicts": [],
        "stale": False,
        "hasParent": False,
        "propagatedClassifications": [],
    }
    # No alias: the key is absent, as every unset field is (AVS-01, MMS-09).
    assert "typeAlias" not in EntityCard(guid="g", type_name="t").to_json()


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
