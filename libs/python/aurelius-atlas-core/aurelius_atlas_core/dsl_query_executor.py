"""``TraversalBasedExecutor``: a DSL query parsed, composed and searched; its entities or rows answered.

Atlas translates the query to a graph traversal and walks it; here the composed plan is searched in steps
(DD-242, DD-243): the conditions on referred entities and classification attributes resolved to GUIDs first, then
each move to referred entities, then the final entities, answered as headers, a ``select``'s rows or groups.
Atlas's translation cache is not ported.
"""

from collections.abc import Iterable
from dataclasses import replace
from typing import Any

from aurelius_atlas_dsl.atlas_dsl import QueryMetadata, parse
from aurelius_atlas_model.discovery import AtlasQueryType, AtlasSearchResult, AttributeSearchResult, Condition
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

from aurelius_atlas_core.dsl_query_composer import Classified, DslPlan, DslQueryComposer, Referring, UnsupportedError
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.graph_helper import other_end
from aurelius_atlas_core.search_fields import CLASSIFICATION_GUIDS, classification_fields
from aurelius_atlas_core.search_query import GUID_FIELD, Criterion, Filter, Group, SearchQuery, Test, matches
from aurelius_atlas_core.select_clause_projections import get_sublist_for_group_by, projection_rows
from aurelius_atlas_core.stored_entity import StoredEntity

DSL_KEYWORD_LIMIT = "limit"
DSL_KEYWORD_OFFSET = "offset"
MAX_STEP_ENTITIES = 10_000
"""The most entities a step that reads them all reads (DSP-09, DV-98)."""


class DslQueryExecutor:
    """Answers DSL queries from the entities of ``store``."""

    def __init__(self, store: EntityStore) -> None:
        self._store = store
        self._retriever = EntityRetriever(store)

    async def execute(self, dsl_query: str, limit: int, offset: int) -> AtlasSearchResult:
        """``execute``: the entities the query finds, or its ``select``'s rows (DSE-13, DSP-01, DSP-05).

        Args:
            dsl_query: The query as ``getDslQueryUsingTypeNameClassification`` built it (DSE-02).
            limit: The normalised limit, used unless the query names its own (DSE-03).
            offset: The normalised offset, likewise.

        Returns:
            A ``DSL`` result of ``dsl_query`` with the entities found, or a result with only ``attributes``.

        Raises:
            AtlasError: ``INVALID_DSL_QUERY`` for a query that does not parse (DSL-04), with semantic errors
                (DSE-14, DSP-04) or of a form not searched (DSE-15).
        """
        query = translatable(dsl_query, limit, offset)
        tree = parse(query)
        composer = DslQueryComposer(self._store.registry, QueryMetadata.of(tree), limit, offset)
        try:
            plan = composer.compose(tree)
        except UnsupportedError as unsupported:
            raise AtlasError(AtlasErrorCode.INVALID_DSL_QUERY, query, str(unsupported)) from unsupported
        if composer.errors:
            raise AtlasError(AtlasErrorCode.INVALID_DSL_QUERY, query, ", ".join(composer.errors))
        result = AtlasSearchResult(query_type=AtlasQueryType.DSL, query_text=dsl_query)
        search = await self._final(plan)
        if plan.group_by is not None:
            return await self._grouped(plan, search, result)
        select = plan.select
        if select is not None and not select.is_select_noop:
            found = await self._all(search) if select.has_aggregators else (await self._store.search(search)).entities
            if not found:
                return result
            rows = await projection_rows(found, select, self._retriever)
            return AtlasSearchResult(attributes=AttributeSearchResult(name=select.labels, values=rows))
        await self._add_headers(result, (await self._store.search(search)).entities)
        return result

    async def _final(self, plan: DslPlan) -> SearchQuery:
        """The search for the final entities: each step's entities found, and the query moved on (DSP-06)."""
        restriction: Filter | None = None
        for step in plan.steps:
            sources = await self._all(
                SearchQuery(type_names=None, filter=await self._resolved(_and(step.filter, restriction)))
            )
            referred: set[str] = set()
            for stored in sources:
                referred.update(await self._referred(stored, step.attribute_name))
            restriction = _guids_criterion(GUID_FIELD, referred)
        return replace(plan.search, filter=await self._resolved(_and(plan.search.filter, restriction)))

    async def _grouped(self, plan: DslPlan, search: SearchQuery, result: AtlasSearchResult) -> AtlasSearchResult:
        """``groupby``: the groups' rows, Atlas's sublist of them, or the entities of every group (DSP-05)."""
        field = str(plan.group_by)
        groups: dict[Any, list[StoredEntity]] = {}
        for stored in await self._all(search):
            value = (stored.search or {}).get(field)
            groups.setdefault(tuple(value) if isinstance(value, list) else value, []).append(stored)
        ordered = [groups[key] for key in sorted(groups, key=lambda key: (type(key).__name__, key))]
        select = plan.select
        if select is None or select.is_select_noop:
            for group in ordered:
                await self._add_headers(result, group)
            return result
        if not ordered:
            return result
        rows = [row for group in ordered for row in await projection_rows(group, select, self._retriever)]
        values = get_sublist_for_group_by(rows, plan.metadata)
        return AtlasSearchResult(attributes=AttributeSearchResult(name=select.labels, values=values))

    async def _all(self, search: SearchQuery) -> list[StoredEntity]:
        """Every entity a search finds, in its order, at most ``MAX_STEP_ENTITIES`` (DSP-09)."""
        return (await self._store.search(replace(search, offset=0, size=MAX_STEP_ENTITIES))).entities

    async def _resolved(self, node: Filter | None) -> Filter | None:
        """The filter with its conditions on referred entities and classification attributes as GUIDs (DD-243)."""
        if node is None:
            return None
        if isinstance(node, Group):
            return Group(
                node.condition, tuple([found for child in node.criteria if (found := await self._resolved(child))])
            )
        if isinstance(node.value, Referring):
            return _guids_criterion(GUID_FIELD, await self._referring(node.value))
        if isinstance(node.value, Classified):
            return _guids_criterion(CLASSIFICATION_GUIDS, await self._classified(node.value))
        return node

    async def _referring(self, referring: Referring) -> set[str]:
        """The entities whose attribute refers to an entity the filter finds, by reference or relationship (DSP-07)."""
        matched = await self._all(SearchQuery(type_names=None, filter=await self._resolved(referring.filter)))
        targets = {stored.guid for stored in matched}
        candidates = {versioned.entity.guid for versioned in await self._store.referring(sorted(targets))}
        listed = [guid for stored in matched for guid in stored.relationship_guids or []]
        for versioned in (await self._store.get_relationships(listed)).values():
            relationship = versioned.relationship
            candidates.update(
                other_end(relationship, end)
                for end in (relationship.end1_guid, relationship.end2_guid)
                if end in targets
            )
        found = await self._store.get_many(sorted(candidates))
        return {
            guid
            for guid, versioned in found.items()
            if targets & await self._referred(versioned.entity, referring.attribute_name)
        }

    async def _classified(self, classified: Classified) -> set[str]:
        """The classification instances of the types whose attributes meet the filter (DSP-08, DD-090)."""
        guids = set()
        for instance in await self._store.classifications_of_types(classified.type_names):
            classification_type = self._store.registry.classification_type(instance.type_name)
            if classification_type is not None and matches(
                classified.filter, classification_fields(instance, classification_type)
            ):
                guids.add(instance.guid)
        return guids

    async def _referred(self, stored: StoredEntity, attribute_name: str) -> set[str]:
        """The GUIDs the entity's attribute of that name refers to, a plain reference or a relationship end."""
        entity_type = self._store.registry.entity_type(stored.type_name)
        if entity_type is None:
            return set()
        attribute = entity_type.attribute(attribute_name) or entity_type.relationship_attribute(attribute_name)
        if attribute is None:
            return set()
        return set(_guids(await self._retriever.entity_attribute(stored, attribute)))

    async def _add_headers(self, result: AtlasSearchResult, found: Iterable[StoredEntity]) -> None:
        """``processVertices``: each entity's header with its classifications (DSE-13)."""
        for stored in found:
            header = await self._retriever.header_with_attributes(stored, [])
            header.classifications = await self._retriever.classifications(stored.guid)
            result.add_entity(header)


def translatable(dsl_query: str, limit: int, offset: int) -> str:
    """``getStringWithLimitOffset``: the limit and offset appended unless the text holds either word (DSE-03)."""
    if DSL_KEYWORD_LIMIT in dsl_query or DSL_KEYWORD_OFFSET in dsl_query:
        return dsl_query
    return f"{dsl_query} limit {limit} offset {offset}"


def _and(node: Filter | None, restriction: Filter | None) -> Filter | None:
    if node is None or restriction is None:
        return node or restriction
    return Group(Condition.AND, (node, restriction))


def _guids_criterion(field: str, guids: set[str]) -> Criterion:
    if not guids:
        return Criterion(field, Test.NOTHING)
    return Criterion(field, Test.ANY_OF, frozenset(guids), array=field == CLASSIFICATION_GUIDS)


def _guids(value: Any) -> Iterable[str]:  # noqa: ANN401 - an attribute value as Atlas answers it
    """The GUIDs of an object id, a related object id, or an array or map of them."""
    items = (
        value.values()
        if isinstance(value, dict) and "guid" not in value
        else value
        if isinstance(value, list)
        else [value]
    )
    for item in items:
        guid = item.get("guid") if isinstance(item, dict) else getattr(item, "guid", None)
        if isinstance(guid, str):
            yield guid
