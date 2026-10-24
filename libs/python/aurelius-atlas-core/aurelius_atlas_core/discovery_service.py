"""``EntityDiscoveryService``: a basic search and its answer (SRC-07 to SRC-10).

Atlas's ``EntityDiscoveryService.searchWithParameters`` and ``searchWithSearchContext`` with
``QueryParams.getNormalizedParams``, for the entity search of 4.1a (DD-087).
"""

from collections.abc import Iterable
from typing import Any

from aurelius_atlas_model.discovery import AtlasQueryType, AtlasSearchResult, AttributeSearchResult, SearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntityHeader, AtlasObjectId
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import resolved
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.entity_type import EntityType

from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_search_processor import EntitySearchProcessor
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.search_context import SearchContext, encode_marker
from aurelius_atlas_core.search_fields import field_name
from aurelius_atlas_core.stored_entity import StoredEntity

DEFAULT_LIMIT = 100
"""``atlas.search.defaultlimit``."""
MAX_LIMIT = 10_000
"""``atlas.search.maxlimit``."""


def normalized(limit: int, offset: int) -> tuple[int, int]:
    """``getNormalizedParams``: a limit of 1 to 10,000, else 100; an offset of at least 0 (SRC-07)."""
    return (limit if 0 < limit <= MAX_LIMIT else DEFAULT_LIMIT), max(offset, 0)


class EntityDiscoveryService:
    """Basic search over the entities of ``store``."""

    def __init__(self, store: EntityStore) -> None:
        self._store = store

    async def search_with_parameters(self, parameters: SearchParameters) -> AtlasSearchResult:
        """``searchWithParameters``: the entities a search finds, as ``searchWithSearchContext`` answers them.

        The answer shows the parameters with their limit and offset as used (SRC-07).

        Raises:
            AtlasError: As ``SearchContext`` checks; ``INVALID_SEARCH_PARAMS`` for a search of no type (DV-46).
        """
        parameters = parameters.model_copy(deep=True)
        context = SearchContext(parameters, self._store.registry)
        if not context.entity_types and context.classification_mode is None:
            raise AtlasError(AtlasErrorCode.INVALID_SEARCH_PARAMS)
        result = AtlasSearchResult(
            query_type=AtlasQueryType.BASIC, query_text=parameters.query, search_parameters=parameters
        )
        parameters.limit, parameters.offset = normalized(parameters.limit, parameters.offset)
        processor = EntitySearchProcessor(context, self._store.now)
        found = await processor.execute(self._store)
        result.approximate_count = processor.result_count
        result.next_marker = encode_marker(parameters, processor.next_offset)
        if context.exclude_header_attributes():
            result.attributes = _table(context, found)
            return result
        await self._headers(context, found, result)
        return result

    async def _headers(self, context: SearchContext, found: list[StoredEntity], result: AtlasSearchResult) -> None:
        """Each entity's header with the result attributes, and the headers of the entities they refer to (SRC-09)."""
        parameters = context.parameters
        names: list[str] = list(dict.fromkeys([*(parameters.attributes or []), *context.entity_attributes]))
        first = context.first_type
        references = [name for name in names if first is not None and _refers(first, name)]
        retriever = EntityRetriever(self._store)
        referred: dict[str, AtlasEntityHeader] = {}
        for stored in found:
            header = await retriever.header_with_attributes(stored, names)
            if parameters.include_classification_attributes:
                header.classifications = await retriever.classifications(stored.guid)
            result.add_entity(header)
            for name in references:
                for guid in _guids(header.get_attribute(name)):
                    if guid not in referred:
                        referred[guid] = await retriever.header(guid, classifications=False)
        if referred:
            result.referred_entities = referred


def _refers(entity_type: EntityType, name: str) -> bool:
    """Whether the attribute, or relationship attribute, holds entities or arrays of them."""
    attribute = entity_type.attribute(name) or entity_type.relationship_attribute(name)
    if attribute is None:
        return False
    attribute_type = attribute.attribute_type
    if isinstance(attribute_type, ArrayType):
        attribute_type = resolved(attribute_type.element_type)
    return attribute_type.category in {TypeCategory.OBJECT_ID_TYPE, TypeCategory.ENTITY}


def _guids(value: Any) -> Iterable[str]:  # noqa: ANN401 - an attribute value
    items = value if isinstance(value, list) else [value]
    for item in items:
        if isinstance(item, AtlasObjectId) and item.guid:
            yield item.guid


def _table(context: SearchContext, found: list[StoredEntity]) -> AttributeSearchResult:
    """``excludeHeaderAttributes``: per entity, the first type's attributes as stored, ``""`` for none (SRC-10)."""
    names = list(context.parameters.attributes or [])
    first = context.first_type
    attributes: list[AtlasAttribute | None] = [None if first is None else first.attribute(name) for name in names]
    rows = [[_stored(stored, attribute) for attribute in attributes] for stored in found]
    return AttributeSearchResult(name=names, values=rows)


def _stored(stored: StoredEntity, attribute: AtlasAttribute | None) -> Any:  # noqa: ANN401 - a vertex property
    """``vertex.getProperty``: the stored value, a system attribute's from its search field; ``""`` for none."""
    if attribute is None:
        return ""
    value = stored.attributes.get(attribute.qualified_name)
    if value is None:
        name = field_name(attribute)
        value = None if name is None else (stored.search or {}).get(name)
    return "" if value is None else value
