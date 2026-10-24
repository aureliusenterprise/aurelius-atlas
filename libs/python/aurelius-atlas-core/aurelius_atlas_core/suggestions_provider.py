"""``SuggestionsProviderImpl``: terms suggested for a prefix (SUG-01, SUG-02, DD-094).

Atlas's ``SuggestionsProviderImpl`` with the terms handler of ``AtlasJanusGraphIndexClient.getSuggestions`` and
``getTopTerms``, over the fields ``SolrIndexHelper`` gives it: the entity documents read the terms.
"""

from aurelius_atlas_model.discovery import AtlasSuggestionsResult
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.entity_type import ENTITY_ROOT
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.struct_type import StructType

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.free_text import suggestion_fields, top_terms
from aurelius_atlas_core.search_fields import KEYWORD, field_name


class SuggestionsProvider:
    """Suggestions from the entities of ``store``."""

    def __init__(self, store: EntityStore) -> None:
        self._store = store

    async def suggestions(self, prefix_string: str | None, field_name_: str | None) -> AtlasSuggestionsResult:
        """``getSuggestions``: up to 5 terms beginning with the prefix, most frequent first (SUG-01, SUG-02)."""
        result = AtlasSuggestionsResult(prefix_string=prefix_string, field_name=field_name_)
        named = None if field_name_ is None else index_field(self._store.registry, field_name_)
        if named is None:
            fields = suggestion_fields(self._store.registry)
        else:
            fields = [named] if named.startswith(f"{KEYWORD}.") else []
        result.suggestions = top_terms(await self._store.terms(fields, prefix_string or "")) if fields else []
        return result


def index_field(registry: TypeRegistry, name: str) -> str | None:
    """``getIndexFieldName``: the search field of a system attribute, or of ``<type>.<attribute>`` for a primitive
    attribute the type defines; None for any other name (SUG-02).
    """  # noqa: D205 - one sentence
    attribute: AtlasAttribute | None = ENTITY_ROOT.all_attributes.get(name)
    if attribute is None:
        type_name, _, attribute_name = name.rpartition(".")
        defining = registry.get_type(type_name) if registry.is_registered(type_name) else None
        attribute = defining.attribute(attribute_name) if isinstance(defining, StructType) else None
        if attribute is None or attribute.qualified_name != name:
            return None
    if attribute.attribute_type.category is not TypeCategory.PRIMITIVE:
        return None
    return field_name(attribute)
