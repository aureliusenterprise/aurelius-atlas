"""``ClassificationAssociator``: set entities' classifications to those their headers give (CLA-01 to CLA-04).

Atlas's ``ClassificationAssociator.Updater`` and ``ListOps``: each header finds its entity by unique attributes, its
classifications are matched with the entity's by type name, and the differences are deleted, updated and added
through 3.3a's operations, each changing the store at once; a summary line records each step.
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence

from aurelius_atlas_model.errors import AtlasError, java_string
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntityHeader
from aurelius_atlas_typesystem.entity_type import EntityType

from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore

QUALIFIED_NAME = "qualifiedName"
NO_UNIQUE_NAME = "<no unique name>"
DONE = "(Done)"
SKIPPED = "(Skipped)"
PARTIAL = "(Partial)"
ADD, UPDATE, DELETE = "Add", "Update", "Delete"


class ClassificationAssociator:
    """``Updater`` over the entities of ``store``, changing them as ``user``."""

    def __init__(self, store: EntityStore, *, user: str | None = None) -> None:
        self._store = store
        self._classifications = EntityClassifications(store, user=user)
        self._summary: list[str] = []

    async def set_classifications(self, headers: Mapping[str, AtlasEntityHeader] | None) -> str:
        """``setClassifications``: handle each header in order; the summaries as a JSON array (CLA-01, CLA-04).

        Java builds the array as text, each summary quoted as it is (``getJsonArray``).
        """
        for header in (headers or {}).values():
            await self._set(header)
        return "[" + ",".join(f'"{line}"' for line in self._summary) + "]"

    async def _set(self, header: AtlasEntityHeader) -> None:
        type_name = header.type_name
        entity_type = None if type_name is None else self._store.registry.entity_type(type_name)
        if entity_type is None:
            self._summary.append(f"{java_string(type_name)}: {SKIPPED}")
            return
        name = _unique_name(entity_type, header) or NO_UNIQUE_NAME
        found = await self._store.find_by_unique_attributes(entity_type, header.attributes or {})
        if found is None:
            self._summary.append(f"Entity:{entity_type.type_name}:{name}:[Not found]:{SKIPPED}")
            return
        guid = found.entity.guid
        current = await self._classifications.get_classifications(guid)
        incoming = _filter(header.guid, header.classifications)
        stored = _filter(guid, current)
        if not incoming and not stored:
            return
        prefix = (guid, str(type_name), name)
        deleted = _subtract(stored, incoming)
        updated = _intersect(incoming, stored)
        added = _subtract(incoming, stored)
        if deleted:
            await self._step(DELETE, prefix, deleted, *[self._deleter(guid, c) for c in deleted])
        if updated:
            await self._step(
                UPDATE, prefix, updated, lambda: self._classifications.update_classifications(guid, updated)
            )
        if added:
            await self._step(ADD, prefix, added, lambda: self._classifications.add_classifications(guid, added))

    def _deleter(self, guid: str, classification: AtlasClassification) -> Callable[[], Awaitable[None]]:
        return lambda: self._classifications.delete_classification(guid, str(classification.type_name))

    async def _step(
        self,
        operation: str,
        prefix: tuple[str, str, str],
        classifications: Sequence[AtlasClassification],
        *requests: Callable[[], Awaitable[None]],
    ) -> None:
        """Run the step's requests; ``(Partial)`` when one fails, which does not stop the others (CLA-03)."""
        status = DONE
        for request in requests:
            try:
                await request()
            except AtlasError:
                status = PARTIAL
        names = ", ".join(java_string(classification.type_name) for classification in classifications)
        guid, type_name, name = prefix
        self._summary.append(f"{operation}:{guid}:{type_name}:{name} -> {names}:{status}")


def _unique_name(entity_type: EntityType, header: AtlasEntityHeader) -> str | None:
    """``getUniqueAttributeName``: ``qualifiedName`` when the header has it, else the type's first unique attribute.

    None for a type without unique attributes (DV-36).
    """
    if QUALIFIED_NAME in (header.attributes or {}):
        return QUALIFIED_NAME
    return next((str(name) for name in entity_type.unique_attributes), None)


def _filter(guid: str | None, classifications: Sequence[AtlasClassification] | None) -> list[AtlasClassification]:
    """``ListOps.filter``: those attached to ``guid``, or to no entity, or all when there is no GUID (CLA-02)."""
    return [
        classification
        for classification in classifications or []
        if not guid or not classification.entity_guid or classification.entity_guid == guid
    ]


def _find(classifications: Sequence[AtlasClassification], check: AtlasClassification) -> AtlasClassification | None:
    return next((found for found in classifications if found.type_name == check.type_name), None)


def _subtract(left: Sequence[AtlasClassification], right: Sequence[AtlasClassification]) -> list[AtlasClassification]:
    """``ListOps.subtract``: those of ``left`` with no type name in ``right``."""
    return [classification for classification in left if _find(right, classification) is None]


def _intersect(left: Sequence[AtlasClassification], right: Sequence[AtlasClassification]) -> list[AtlasClassification]:
    """``ListOps.intersect``: for each of ``right``, in its order, the one of ``left`` with its type name."""
    return [found for classification in right if (found := _find(left, classification)) is not None]
