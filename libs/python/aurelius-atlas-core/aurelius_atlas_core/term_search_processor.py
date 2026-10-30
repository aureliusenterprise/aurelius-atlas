"""``TermSearchProcessor``: the entities a glossary term is assigned to, as a search criterion (GTA-06, GTA-07).

A basic search's ``termName`` names an active term by qualified name; the DSL's ``hasTerm`` names terms by name or
qualified name. Either way the entities are those the terms' semantic assignments reach, in any state, as Atlas's
edges reach them.
"""

from collections.abc import Iterable

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import EntityStatus

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.search_fields import field_name
from aurelius_atlas_core.search_query import GUID_FIELD, Criterion, SearchQuery, Test

TERM_TYPE = "AtlasGlossaryTerm"
TERM_ASSIGNMENT = "AtlasGlossarySemanticAssignment"
MAX_TERMS = 10_000
"""The most terms of one name ``hasTerm`` reads (the search's window)."""


async def term_criterion(store: EntityStore, term_name: str) -> Criterion:
    """``SearchContext``'s term: the entities the active term of the qualified name is assigned to (GTA-06).

    Raises:
        AtlasError: ``UNKNOWN_GLOSSARY_TERM`` when no active term has the name.
    """
    term_type = store.registry.entity_type(TERM_TYPE)
    found = None
    if term_type is not None:
        found = await store.find_by_unique_attributes(term_type, {"qualifiedName": term_name})
    if found is None or found.entity.state is not EntityStatus.ACTIVE:
        raise AtlasError(AtlasErrorCode.UNKNOWN_GLOSSARY_TERM, term_name)
    return guids_criterion(await assigned_entity_guids(store, [found.entity.guid]))


async def has_term_guids(store: EntityStore, attribute: str, value: str) -> set[str]:
    """``GremlinClause.TERM``: the entities assigned a term, in any state, whose attribute has the value (GTA-07)."""
    term_type = store.registry.entity_type(TERM_TYPE)
    found = None if term_type is None else term_type.attribute(attribute)
    field = None if found is None else field_name(found)
    if field is None:
        return set()
    hits = await store.search(
        SearchQuery(type_names=frozenset({TERM_TYPE}), filter=Criterion(field, Test.EQ, value), size=MAX_TERMS)
    )
    return await assigned_entity_guids(store, [stored.guid for stored in hits.entities])


async def assigned_entity_guids(store: EntityStore, term_guids: Iterable[str]) -> set[str]:
    """``getAssignedEntities``: the entities the terms are assigned to, by assignments in any state (GTA-06)."""
    terms = await store.get_many(list(term_guids))
    listed = [guid for versioned in terms.values() for guid in versioned.entity.relationship_guids or []]
    return {
        versioned.relationship.end2_guid
        for versioned in (await store.get_relationships(listed)).values()
        if versioned.relationship.type_name == TERM_ASSIGNMENT and versioned.relationship.end1_guid in terms
    }


def guids_criterion(guids: Iterable[str]) -> Criterion:
    """The entities of these GUIDs; none when there are none."""
    found = frozenset(guids)
    return Criterion(GUID_FIELD, Test.ANY_OF, found) if found else Criterion(GUID_FIELD, Test.NOTHING)
