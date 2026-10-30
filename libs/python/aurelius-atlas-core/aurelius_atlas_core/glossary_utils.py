"""``GlossaryUtils``: what the category and term utilities share (GCT-02, GTM-03).

The skeletons a glossary object is loaded by, the relationship operations, and the relationships between glossary
objects: created unless one of the type joins the ends already, and removed for good.
"""

from collections.abc import Iterable
from enum import Enum

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryTerm,
    AtlasRelatedTermHeader,
)
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelationship

from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.glossary_dto import DataAccess
from aurelius_atlas_core.relationship_store import RelationshipStore


class RelationshipOperation(Enum):
    """``GlossaryUtils.RelationshipOperation``."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


def glossary_skeleton(guid: str | None) -> AtlasGlossary:
    """``getGlossarySkeleton``."""
    glossary = AtlasGlossary()
    glossary.guid = guid or ""
    return glossary


def category_skeleton(guid: str | None) -> AtlasGlossaryCategory:
    """``getAtlasGlossaryCategorySkeleton``."""
    category = AtlasGlossaryCategory()
    category.guid = guid or ""
    return category


def term_skeleton(guid: str | None) -> AtlasGlossaryTerm:
    """``getAtlasGlossaryTermSkeleton``."""
    term = AtlasGlossaryTerm()
    term.guid = guid or ""
    return term


def relationship(type_name: str, end1: str | None, end2: str | None) -> AtlasRelationship:
    """A relationship of the type from ``end1`` to ``end2``."""
    return AtlasRelationship(
        type_name=type_name, end1=AtlasObjectId(guid=end1), end2=AtlasObjectId(guid=end2), attributes={}
    )


def term_relation_attributes(found: AtlasRelationship, header: AtlasRelatedTermHeader) -> None:
    """``updateRelationshipAttributes`` of a term relation: the header's attributes, its status when it has one."""
    for name in ("expression", "description", "steward", "source"):
        found.set_attribute(name, getattr(header, name))
    if header.status is not None:
        found.set_attribute("status", header.status.value)


class GlossaryUtils:
    """The relationships of ``store`` between glossary objects, the objects loaded through ``data_access``."""

    def __init__(self, store: EntityStore, data_access: DataAccess, *, user: str | None = None) -> None:
        self._store = store
        self._data_access = data_access
        self._relationships = RelationshipStore(store, user=user)

    async def _get_or_create(self, found: AtlasRelationship) -> None:
        """``createRelationship``: a relationship of the type between the ends exists already, or is created."""
        try:
            await self._relationships.create(found)
        except AtlasError as error:
            if error.code is not AtlasErrorCode.RELATIONSHIP_ALREADY_EXISTS:
                raise

    async def _delete(self, guid: str | None) -> None:
        """``deleteById(guid, true)``: the relationship removed for good."""
        if guid:
            await self._relationships.delete_by_id(guid, DeleteType.HARD)

    async def _delete_all(self, guids: Iterable[str | None]) -> None:
        for guid in list(guids):
            await self._delete(guid)
