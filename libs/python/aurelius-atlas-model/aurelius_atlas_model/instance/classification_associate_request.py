"""``ClassificationAssociateRequest``: a classification to attach to many entities (CLS-01, CLS-07)."""

from typing import Any

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance.classification import AtlasClassification


class ClassificationAssociateRequest(AtlasModel):
    """The classification, and the entities by GUID, or by their type and sets of unique attribute values."""

    classification: AtlasClassification | None = None
    entity_guids: list[str] | None = None
    entities_unique_attributes: list[dict[str, Any]] | None = None
    entity_type_name: str | None = None
