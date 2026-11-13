"""The JSON-array request bodies where Java declares no class for them (DV-10).

Each is a list of one thing, read from the request as it arrives; the model owns its shape rule, so a
body of none of it fails with the endpoint's ``BAD_REQUEST`` text — the same text the endpoints answered
before the rules moved here.

``ClassificationsList`` keeps no rule of its own: its element model (``AtlasClassification``) already
validates each item, and the endpoint names its error after the list Java reads.
"""

from pydantic import RootModel, field_validator

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import AtlasGlossaryCategory, AtlasGlossaryTerm
from aurelius_atlas_model.instance import AtlasClassification, AtlasRelatedObjectId

NO_LABELS_BODY = "Invalid body: a JSON array of labels is expected"
"""``setLabels``/``addLabels``/``removeLabels`` of a body that is no array of strings (LBL-01, DV-10)."""

NO_GUIDS_BODY = "Invalid body: a JSON array of GUIDs is expected"
"""``purgeByIds`` of a body that is no array of strings (EDL-01, DV-10)."""

NO_RELATED_BODY = "Invalid body: a JSON array of related object ids is expected"
"""``assignTermToEntities`` of a body that is no array of related-object ids (GTA-01, DV-10)."""


class Labels(RootModel[list[str]]):
    """A JSON array of labels (LBL-01).

    Java reads the body as a ``List<String>``; anything else is refused as the endpoint refused it.
    """

    @field_validator("root", mode="before")
    @classmethod
    def _json_array_of_labels(cls, value: object) -> object:
        if not isinstance(value, list) or not all(isinstance(label, str) for label in value):
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_LABELS_BODY)
        return value


class Guids(RootModel[list[str]]):
    """A JSON array of GUIDs (EDL-01).

    Java reads the body as a ``List<String>``; anything else is refused as the endpoint refused it.
    """

    @field_validator("root", mode="before")
    @classmethod
    def _json_array_of_guids(cls, value: object) -> object:
        if not isinstance(value, list) or not all(isinstance(guid, str) for guid in value):
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_GUIDS_BODY)
        return value


class ClassificationsList(RootModel[list[AtlasClassification]]):
    """A JSON array of classifications, each validated by ``AtlasClassification`` (CLS-04)."""


class RelatedObjectIds(RootModel[list[AtlasRelatedObjectId]]):
    """A JSON array of related-object ids, each validated by ``AtlasRelatedObjectId`` (GTA-01).

    Java reads the body as a ``List<AtlasRelatedObjectId>``; anything else is refused as a bad body.
    """

    @field_validator("root", mode="before")
    @classmethod
    def _json_array_of_related_ids(cls, value: object) -> object:
        if not isinstance(value, list):
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_RELATED_BODY)
        return value


class GlossaryTerms(RootModel[list[AtlasGlossaryTerm]]):
    """A JSON array of glossary terms, each validated by ``AtlasGlossaryTerm`` (GTM-02)."""


class GlossaryCategories(RootModel[list[AtlasGlossaryCategory]]):
    """A JSON array of glossary categories, each validated by ``AtlasGlossaryCategory`` (GCT-02)."""
