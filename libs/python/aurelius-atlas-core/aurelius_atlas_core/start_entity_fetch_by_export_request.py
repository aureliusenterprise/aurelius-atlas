"""``StartEntityFetchByExportRequest``: the entities an export item starts from (EXP-03).

Atlas finds them with Gremlin over the graph's vertices, in any state; here over the stored entities of the types.
"""

import re
from collections.abc import Callable

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.impexp import (
    MATCH_TYPE_CONTAINS,
    MATCH_TYPE_ENDS_WITH,
    MATCH_TYPE_FOR_TYPE,
    MATCH_TYPE_MATCHES,
    MATCH_TYPE_STARTS_WITH,
    AtlasExportRequest,
)
from aurelius_atlas_model.instance import AtlasObjectId

from aurelius_atlas_core.entity_store import EntityStore

_TESTS: dict[str, Callable[[str, str], bool]] = {
    MATCH_TYPE_STARTS_WITH: lambda stored, given: stored.startswith(given),
    MATCH_TYPE_ENDS_WITH: lambda stored, given: stored.endswith(given),
    MATCH_TYPE_CONTAINS: lambda stored, given: given in stored,
    MATCH_TYPE_MATCHES: lambda stored, given: re.fullmatch(given, stored) is not None,
}
"""The Gremlin filters of the match types on a text value: ``startsWith``, ``endsWith``, ``contains``, ``matches``."""


class StartEntityFetchByExportRequest:
    """``StartEntityFetchByExportRequest`` over the entities of ``store``."""

    def __init__(self, store: EntityStore) -> None:
        self._store = store

    async def get(self, request: AtlasExportRequest, item: AtlasObjectId) -> list[str]:
        """``get``: the item's GUID; with ``forType``, every entity of its types; else those of its type holding its
        values. An unknown type finds none (EXP-03).
        """  # noqa: D205 - one sentence
        match_type = request.match_type()
        if item.guid:
            return [item.guid]
        try:
            if (match_type or "").lower() == MATCH_TYPE_FOR_TYPE.lower() and item.type_name:
                names = [name for name in item.type_name.split(",") if name]
                return [entity.guid for entity in await self._store.of_types(names)]
            if item.type_name and item.unique_attributes:
                return await self._by_attributes(item, match_type)
        except AtlasError:
            return []
        return []

    async def _by_attributes(self, item: AtlasObjectId, match_type: str | None) -> list[str]:
        """``getEntitiesForMatchTypeUsingUniqueAttributes``: the entities of exactly the type matching any value.

        Raises:
            AtlasError: ``UNKNOWN_TYPENAME``.
        """
        entity_type = self._store.registry.entity_type(item.type_name)
        if entity_type is None:
            raise AtlasError(AtlasErrorCode.UNKNOWN_TYPENAME, item.type_name)
        test = _TESTS.get(match_type or "")
        found: dict[str, None] = {}
        entities = await self._store.of_types([str(item.type_name)])
        for name, value in (item.unique_attributes or {}).items():
            attribute = entity_type.attribute(name)
            if attribute is None or value is None:
                continue
            for entity in entities:
                stored = entity.attributes.get(attribute.qualified_name)
                if test is None:
                    matched = stored is not None and stored == value
                else:
                    matched = isinstance(stored, str) and isinstance(value, str) and _safely(test, stored, value)
                if matched:
                    found[entity.guid] = None
        return list(found)


def _safely(test: Callable[[str, str], bool], stored: str, given: str) -> bool:
    """The test, false for a pattern that does not compile (Gremlin's script failing finds none)."""
    try:
        return test(stored, given)
    except re.error:
        return False
