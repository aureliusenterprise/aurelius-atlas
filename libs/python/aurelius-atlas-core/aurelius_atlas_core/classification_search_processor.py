"""``ClassificationSearchProcessor``: what a search's classifications ask of an entity (CSR-01 to CSR-04, DD-090).

Atlas's ``ClassificationSearchProcessor`` and the classification filter of ``EntitySearchProcessor``
(``buildTraitPredict``): without tag filters, a test of the entity's classification names; with them, of the
instances it lists, found first among those of the types named.
"""

from typing import TYPE_CHECKING

from aurelius_atlas_model.discovery import Condition

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.search_context import ClassificationMode, SearchContext
from aurelius_atlas_core.search_fields import (
    CLASSIFICATION_GUIDS,
    PROPAGATED_TRAIT_NAMES,
    TRAIT_NAMES,
    classification_fields,
)
from aurelius_atlas_core.search_query import Criterion, Filter, Group, Test, matches

if TYPE_CHECKING:
    from aurelius_atlas_core.entity_search_processor import SearchFilters


class ClassificationSearchProcessor:
    """The classification criterion of a search's context; ``filters`` builds its tag filters."""

    def __init__(self, context: SearchContext, filters: SearchFilters) -> None:
        self._context = context
        self._filters = filters

    async def criterion(self, store: EntityStore) -> Filter | None:
        """The criterion an entity must meet, or None for a search without classifications (CSR-02, CSR-03)."""
        context = self._context
        mode = context.classification_mode
        if mode is None:
            return None
        if mode is ClassificationMode.NONE:
            return _both(Test.IS_NULL, None, Condition.AND)
        if context.has_tag_filters:
            return await self._tagged(store)
        if mode is ClassificationMode.ANY:
            return _both(Test.NOT_NULL, None, Condition.OR)
        if mode is ClassificationMode.WILDCARD:
            tests = [Criterion(field, Test.MATCHES, name) for name in context.classification_names for field in _NAMES]
            return Group(Condition.OR, tuple(tests))
        return _both(Test.ANY_OF, context.classification_type_names, Condition.OR)

    async def _tagged(self, store: EntityStore) -> Filter:
        """The instances of the types matching the tag filters, among those the entity lists (DD-090)."""
        context = self._context
        tag_filter = self._filters.filter(context.parameters.tag_filters, context.tag_types)
        any_type = context.classification_mode is ClassificationMode.ANY
        instances = await store.classifications_of_types(None if any_type else context.classification_type_names)
        guids: list[str] = []
        for instance in instances:
            classification_type = store.registry.classification_type(instance.type_name)
            if classification_type is None:
                continue
            if tag_filter is None or matches(tag_filter, classification_fields(instance, classification_type)):
                guids.append(instance.guid)
        if not guids:
            return Criterion(CLASSIFICATION_GUIDS, Test.NOTHING)
        return Criterion(CLASSIFICATION_GUIDS, Test.ANY_OF, frozenset(guids), array=True)


_NAMES = (TRAIT_NAMES, PROPAGATED_TRAIT_NAMES)


def _both(test: Test, value: object, condition: Condition) -> Group:
    """A test of both the attached and the propagated classification names."""
    return Group(condition, tuple(Criterion(field, test, value, array=True) for field in _NAMES))
