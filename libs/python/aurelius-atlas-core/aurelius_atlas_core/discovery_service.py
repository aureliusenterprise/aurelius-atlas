"""``EntityDiscoveryService``: a basic search and its answer (SRC-07 to SRC-10).

Atlas's ``EntityDiscoveryService.searchWithParameters`` and ``searchWithSearchContext`` with
``QueryParams.getNormalizedParams``, for the entity search of 4.1a (DD-087), with the free text of 4.2a and
``searchUsingFullTextQuery`` (DD-091), the quick search of 4.2b, and DSL search (4.4a).
"""

from collections.abc import Iterable
from typing import Any

from aurelius_atlas_model.discovery import (
    AtlasFullTextResult,
    AtlasQueryType,
    AtlasQuickSearchResult,
    AtlasSearchResult,
    AttributeSearchResult,
    QuickSearchParameters,
    SearchParameters,
)
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntityHeader, AtlasObjectId
from aurelius_atlas_model.profile import AtlasUserSavedSearch, SavedSearchType
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import resolved
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.entity_type import EntityType

from aurelius_atlas_core.authorization import ALLOW_ALL, Authorizer, scrub_search_results
from aurelius_atlas_core.dsl_query_executor import DslQueryExecutor
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_search_processor import EntitySearchProcessor
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.free_text import TextQuery, basic_query, has_tokenize_char, weighted_fields
from aurelius_atlas_core.search_aggregator import SearchAggregator
from aurelius_atlas_core.search_context import SearchContext, encode_marker
from aurelius_atlas_core.search_fields import vertex_property
from aurelius_atlas_core.search_query import SearchQuery
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.user_profile_service import UserProfileService

DEFAULT_LIMIT = 100
"""``atlas.search.defaultlimit``."""
MAX_LIMIT = 10_000
"""``atlas.search.maxlimit``."""


def normalized(limit: int, offset: int) -> tuple[int, int]:
    """``getNormalizedParams``: a limit of 1 to 10,000, else 100; an offset of at least 0 (SRC-07)."""
    return (limit if 0 < limit <= MAX_LIMIT else DEFAULT_LIMIT), max(offset, 0)


INVALID_DATA = "invalid data"
"""What a saved search of another user, or a read naming another user, fails with (SVS-02, SVS-04)."""


class EntityDiscoveryService:
    """Basic search over the entities of ``store``; ``authorizer`` checks the saved searches read and written,
    and scrubs the results of entities the user may not read.

    AUZ-10, AUZ-12.
    """  # noqa: D205 - one sentence

    def __init__(self, store: EntityStore, *, authorizer: Authorizer = ALLOW_ALL) -> None:
        self._store = store
        self._authorizer = authorizer

    async def search_with_parameters(self, parameters: SearchParameters) -> AtlasSearchResult:
        """``searchWithParameters``: the entities a search finds, as ``searchWithSearchContext`` answers them.

        The answer shows the parameters with their limit and offset as used (SRC-07).

        Raises:
            AtlasError: As ``SearchContext`` checks; ``INVALID_SEARCH_PARAMS`` for a search of no type,
                classification, query or term (DV-46).
        """
        parameters = parameters.model_copy(deep=True)
        if parameters.query:
            parameters.query = basic_query(parameters.query)
        result, _ = await self._search_with_search_context(parameters, ())
        return result

    async def quick_search(self, parameters: QuickSearchParameters) -> AtlasQuickSearchResult:
        """``quickSearch``: a basic search of the parameters, ``*`` appended to a query without a tokenising
        character, and its facets (QSR-02 to QSR-04).

        Raises:
            AtlasError: As ``search_with_parameters`` does.
        """  # noqa: D205 - one sentence
        query = parameters.query
        if query and not has_tokenize_char(query):
            query = f"{query}*"
        search = parameters.model_copy(update={"query": query}).search_parameters()
        aggregator = SearchAggregator(self._store.registry)
        result, counts = await self._search_with_search_context(search, tuple(aggregator.fields.values()))
        return AtlasQuickSearchResult(search_results=result, aggregation_metrics=aggregator.aggregated_metrics(counts))

    async def _search_with_search_context(
        self, parameters: SearchParameters, facets: tuple[str, ...]
    ) -> tuple[AtlasSearchResult, dict[str, list[tuple[str, int]]]]:
        """``searchWithSearchContext``: the answer to the parameters, and the counts of ``facets`` (DD-093).

        Raises:
            AtlasError: As ``SearchContext`` checks; ``INVALID_SEARCH_PARAMS`` for a search of no type,
                classification, query or term (DV-46).
        """
        context = SearchContext(parameters, self._store.registry)
        if (
            not context.entity_types
            and context.classification_mode is None
            and context.text is None
            and not parameters.term_name
        ):
            raise AtlasError(AtlasErrorCode.INVALID_SEARCH_PARAMS)
        result = AtlasSearchResult(
            query_type=AtlasQueryType.BASIC, query_text=parameters.query, search_parameters=parameters
        )
        parameters.limit, parameters.offset = normalized(parameters.limit, parameters.offset)
        processor = EntitySearchProcessor(context, self._store.now, facets)
        found = await processor.execute(self._store)
        result.approximate_count = processor.result_count
        result.next_marker = encode_marker(parameters, processor.next_offset)
        if context.exclude_header_attributes():
            result.attributes = _table(context, found)
        else:
            await self._headers(context, found, result)
        scrub_search_results(self._authorizer, result)
        return result, processor.facets

    async def search_using_full_text(
        self, query: str, *, exclude_deleted_entities: bool, limit: int, offset: int
    ) -> AtlasSearchResult:
        """``searchUsingFullTextQuery``: each entity matching ``query``, best first, with its score (FTX-05).

        At most ``limit`` of them, normalised; ``offset`` is not used, as in Atlas. The count is of every entity
        matching, deleted ones too (DV-49).
        """
        limit, _ = normalized(limit, offset)
        text = TextQuery(query, weighted_fields(self._store.registry))
        hits = await self._store.search(
            SearchQuery(type_names=None, active_only=exclude_deleted_entities, size=limit, text=text)
        )
        total = hits.total
        if exclude_deleted_entities:
            total = (await self._store.search(SearchQuery(type_names=None, size=0, text=text))).total
        retriever = EntityRetriever(self._store)
        found = [
            AtlasFullTextResult(entity=await retriever.header_with_attributes(stored, []), score=score)
            for stored, score in zip(hits.entities, hits.scores, strict=True)
        ]
        result = AtlasSearchResult(
            query_type=AtlasQueryType.FULL_TEXT, query_text=query, full_text_result=found, approximate_count=total
        )
        scrub_search_results(self._authorizer, result)
        return result

    async def search_using_dsl_query(self, dsl_query: str, limit: int, offset: int) -> AtlasSearchResult:
        """``searchUsingDslQuery``: the entities a DSL query finds, its limit and offset normalised (DSE-01, DSE-03).

        Raises:
            AtlasError: ``INVALID_DSL_QUERY``, as ``DslQueryExecutor.execute`` raises it.
        """
        limit, offset = normalized(limit, offset)
        result = await DslQueryExecutor(self._store).execute(dsl_query, limit, offset)
        scrub_search_results(self._authorizer, result)
        return result

    @staticmethod
    def get_dsl_query_using_type_name_classification(
        query: str | None, type_name: str | None, classification: str | None
    ) -> str:
        """``getDslQueryUsingTypeNameClassification``: the type in backticks before the query, and ``isa`` the
        classification after a type without a query (DSE-02).
        """  # noqa: D205 - one sentence
        query_str = query or ""
        if type_name:
            escaped = type_name if type_name.startswith("`") and type_name.endswith("`") else f"`{type_name}`"
            query_str = f"{escaped} {query_str}"
        if classification and not query:
            query_str += f" isa {classification}"
        return query_str

    async def add_saved_search(
        self, current_user: str | None, saved_search: AtlasUserSavedSearch
    ) -> AtlasUserSavedSearch:
        """``addSavedSearch``: owned by the current user unless it names its owner, which must be them (SVS-02).

        Raises:
            AtlasError: ``BAD_REQUEST`` for another owner, or as ``UserProfileService.add_saved_search``.
        """
        _own(current_user, saved_search)
        return await self._profiles(current_user).add_saved_search(saved_search)

    async def update_saved_search(
        self, current_user: str | None, saved_search: AtlasUserSavedSearch
    ) -> AtlasUserSavedSearch:
        """``updateSavedSearch``: as ``add_saved_search`` checks its owner (SVS-03)."""
        _own(current_user, saved_search)
        return await self._profiles(current_user).update_saved_search(saved_search)

    async def get_saved_searches(
        self, current_user: str | None, user_name: str | None
    ) -> list[AtlasUserSavedSearch] | None:
        """``getSavedSearches``: the current user's; another user's fail with ``BAD_REQUEST`` (SVS-04)."""
        user_name = _of_current(current_user, user_name)
        return await self._profiles(current_user).get_saved_searches(user_name)

    async def get_saved_search_by_name(
        self, current_user: str | None, user_name: str | None, search_name: str
    ) -> AtlasUserSavedSearch:
        """``getSavedSearchByName``: the current user's of the name (SVS-04)."""
        user_name = _of_current(current_user, user_name)
        return await self._profiles(current_user).get_saved_search_by_name(user_name, search_name)

    async def get_saved_search_by_guid(self, current_user: str | None, guid: str) -> AtlasUserSavedSearch:
        """``getSavedSearchByGuid``: the search, if the current user owns it (SVS-04)."""
        found = await self._profiles(current_user).get_saved_search(guid)
        _check_ownership(current_user, found)
        return found

    async def delete_saved_search(self, current_user: str | None, guid: str) -> None:
        """``deleteSavedSearch``: the search, if the current user owns it (SVS-05)."""
        service = self._profiles(current_user)
        _check_ownership(current_user, await service.get_saved_search(guid))
        await service.delete_saved_search(guid)

    def _profiles(self, current_user: str | None) -> UserProfileService:
        return UserProfileService(self._store, user=current_user, authorizer=self._authorizer)

    async def execute_saved_search(self, saved_search: AtlasUserSavedSearch) -> AtlasSearchResult:
        """``executeSavedSearch``: an ``ADVANCED`` search as its DSL query, any other as its basic search (SVS-06).

        Raises:
            AtlasError: ``BAD_REQUEST`` for a search without parameters (DV-110).
        """
        parameters = saved_search.search_parameters
        if parameters is None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "The saved search has no search parameters")
        if saved_search.search_type is SavedSearchType.ADVANCED:
            query = self.get_dsl_query_using_type_name_classification(
                parameters.query, parameters.type_name, parameters.classification
            )
            return await self.search_using_dsl_query(query, parameters.limit, parameters.offset)
        return await self.search_with_parameters(parameters)

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
    rows = [[vertex_property(stored, attribute) for attribute in attributes] for stored in found]
    return AttributeSearchResult(name=names, values=rows)


def _own(current_user: str | None, saved_search: AtlasUserSavedSearch) -> None:
    """The current user as the owner of a search naming none; ``checkSavedSearchOwnership`` (SVS-02)."""
    if not saved_search.owner_name:
        saved_search.owner_name = current_user
    _check_ownership(current_user, saved_search)


def _of_current(current_user: str | None, user_name: str | None) -> str | None:
    """The user a read is of: the current user, named or not (SVS-04).

    Raises:
        AtlasError: ``BAD_REQUEST`` ``invalid data`` for another user.
    """
    if not user_name:
        return current_user
    if user_name != current_user:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, INVALID_DATA)
    return user_name


def _check_ownership(current_user: str | None, saved_search: AtlasUserSavedSearch) -> None:
    """``checkSavedSearchOwnership``: another user's search fails with ``BAD_REQUEST`` ``invalid data``."""
    if saved_search.owner_name != current_user:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, INVALID_DATA)
