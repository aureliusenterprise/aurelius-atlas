"""``TraversalBasedExecutor``: a DSL query parsed, composed and searched, its entities answered (DSE-03, DSE-13).

Atlas translates the query to a graph traversal and walks it; here the composed ``SearchQuery`` is one search of the
entity documents (DD-242). Atlas's translation cache is not ported.
"""

from aurelius_atlas_dsl.atlas_dsl import QueryMetadata, parse
from aurelius_atlas_model.discovery import AtlasQueryType, AtlasSearchResult
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

from aurelius_atlas_core.dsl_query_composer import DslQueryComposer, UnsupportedError
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore

DSL_KEYWORD_LIMIT = "limit"
DSL_KEYWORD_OFFSET = "offset"


class DslQueryExecutor:
    """Answers DSL queries from the entities of ``store``."""

    def __init__(self, store: EntityStore) -> None:
        self._store = store

    async def execute(self, dsl_query: str, limit: int, offset: int) -> AtlasSearchResult:
        """``execute``: the headers of the entities the query finds, with their classifications (DSE-13).

        Args:
            dsl_query: The query as ``getDslQueryUsingTypeNameClassification`` built it (DSE-02).
            limit: The normalised limit, used unless the query names its own (DSE-03).
            offset: The normalised offset, likewise.

        Returns:
            A ``DSL`` result of ``dsl_query``, without entities when none is found.

        Raises:
            AtlasError: ``INVALID_DSL_QUERY`` for a query that does not parse (DSL-04), with semantic errors
                (DSE-14) or of a form not searched (DSE-15).
        """
        query = translatable(dsl_query, limit, offset)
        tree = parse(query)
        composer = DslQueryComposer(self._store.registry, QueryMetadata.of(tree), limit, offset)
        try:
            search = composer.compose(tree)
        except UnsupportedError as unsupported:
            raise AtlasError(AtlasErrorCode.INVALID_DSL_QUERY, query, str(unsupported)) from unsupported
        if composer.errors:
            raise AtlasError(AtlasErrorCode.INVALID_DSL_QUERY, query, ", ".join(composer.errors))
        result = AtlasSearchResult(query_type=AtlasQueryType.DSL, query_text=dsl_query)
        hits = await self._store.search(search)
        retriever = EntityRetriever(self._store)
        for stored in hits.entities:
            header = await retriever.header_with_attributes(stored, [])
            header.classifications = await retriever.classifications(stored.guid)
            result.add_entity(header)
        return result


def translatable(dsl_query: str, limit: int, offset: int) -> str:
    """``getStringWithLimitOffset``: the limit and offset appended unless the text holds either word (DSE-03)."""
    if DSL_KEYWORD_LIMIT in dsl_query or DSL_KEYWORD_OFFSET in dsl_query:
        return dsl_query
    return f"{dsl_query} limit {limit} offset {offset}"
