"""Free text: which search fields it searches, with which weight, and what a query asks (FTX-01 to FTX-03).

Atlas's ``SolrIndexHelper`` gives its Solr ``/freetext`` handler the string attributes of the non-internal entity
types as ``qf``, weighted by their ``searchWeight``, and four system fields with weights of their own; the query
is prepared as ``EntityDiscoveryService.searchWithParameters`` and ``AtlasAttribute.hastokenizeChar`` do (DD-092).
"""

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from aurelius_atlas_model.typedef import ATLAS_TYPE_STRING, TypeCategory
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.search_fields import KEYWORD, field_name

MAX_QUERY_LENGTH = 4096
"""``atlas.graph.fulltext-max-query-str-length``'s default."""

DEFAULT_SEARCH_WEIGHT = -1
DEFAULT_SEARCH_WEIGHT_FOR_STRINGS = 3
SYSTEM_WEIGHTS = {"__classificationsText": 10, "__labels": 10, "__customAttributes": 3, "__typeName": 1}
"""``SEARCHWEIGHT_FOR_CLASSIFICATIONS``, ``_LABELS``, ``_CUSTOM_ATTRS`` and ``_TYPENAME``."""

_TOKENISING_NEXT_TO_LETTERS = ".:'"
_WORD = re.compile(r"\w+")
_QUERY_WORD = re.compile(r"\w+\*?")


@dataclass(frozen=True)
class TextQuery:
    """A free-text query and the search fields it searches, each with its weight (DD-092)."""

    text: str
    fields: Mapping[str, int]


def weighted_fields(registry: TypeRegistry) -> dict[str, int]:
    """``geIndexFieldNamesWithSearchWeights``: the searched fields and their weights (FTX-02).

    The string attributes each non-internal entity type defines, by ``searchWeight`` when 1 to 10, else 3; then
    the classification text, labels, custom attributes and type name.
    """
    weights: dict[str, int] = {}
    for name, weight in SYSTEM_WEIGHTS.items():
        weights[f"{KEYWORD}.{name}"] = weight
    for entity_type in registry.types(TypeCategory.ENTITY):
        if not isinstance(entity_type, EntityType) or entity_type.is_internal:
            continue
        for attribute_def in entity_type.entity_def.attribute_defs:
            attribute = entity_type.attribute(attribute_def.name)
            if attribute is None or str(attribute.attribute_type.type_name) != ATLAS_TYPE_STRING:
                continue
            field = field_name(attribute)
            if field is not None:
                weights[field] = _weight(attribute_def.search_weight)
    return weights


def _weight(search_weight: int | None) -> int:
    """``isValidSearchWeight``: 1 to 10; the default and any other value weigh 3."""
    if search_weight is not None and search_weight != DEFAULT_SEARCH_WEIGHT and 1 <= search_weight <= 10:  # noqa: PLR2004
        return search_weight
    return DEFAULT_SEARCH_WEIGHT_FOR_STRINGS


def has_tokenize_char(value: str) -> bool:
    """``hastokenizeChar``: a character other than letters, digits and ``_`` (``.``, ``:`` and ``'`` only next to a
    non-letter), or a CJK character (FTX-01).
    """  # noqa: D205 - one sentence
    for index, character in enumerate(value):
        if _is_cjk(character):
            return True
        if character.isalnum() or character == "_":
            continue
        if character not in _TOKENISING_NEXT_TO_LETTERS:
            return True
        before = value[index - 1] if index > 0 else None
        after = value[index + 1] if index < len(value) - 1 else None
        if (before is not None and not before.isalpha()) or (after is not None and not after.isalpha()):
            return True
    return False


def _is_cjk(character: str) -> bool:
    """``hasCJKChar``: in the CJK unified ideographs, their extension A, the compatibility ideographs or hiragana."""
    return any(low <= ord(character) <= high for low, high in _CJK_BLOCKS)


_CJK_BLOCKS = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF), (0x3040, 0x309F))


def basic_query(query: str) -> str:
    """``searchWithParameters``: the query without ``*`` at its ends when that holds a tokenising character (FTX-01)."""
    stripped = query.strip("*")
    return stripped if has_tokenize_char(stripped) else query


def text_matches(query: str, values: Mapping[str, object], fields: Mapping[str, int]) -> int:
    """The weight with which search field values match a query, 0 for none: the in-memory reading of DD-092.

    A field matches when one of its words, in any case, is one of the query's, or begins with one ending in ``*``.
    """
    terms = [term.lower() for term in _QUERY_WORD.findall(query)]
    score = 0
    for field, weight in fields.items():
        value = values.get(field)
        items = value if isinstance(value, list) else [] if value is None else [value]
        words = {word.lower() for item in items for word in _WORD.findall(str(item))}
        if any(_term_matches(term, words) for term in terms):
            score += weight
    return score


MIN_SUGGESTION_WEIGHT = 8
"""``MIN_SEARCH_WEIGHT_FOR_SUGGESTIONS``: the least weight of a field suggestions read (SUG-01)."""
TERM_COUNT = 5
"""``terms.limit`` and ``DEFAULT_SUGGESTION_COUNT``: the terms read per field, and suggested (SUG-01)."""


def suggestion_fields(registry: TypeRegistry) -> list[str]:
    """``getIndexFieldNamesForSuggestions``: the searched fields weighted 8 or more (SUG-01)."""
    return [name for name, weight in weighted_fields(registry).items() if weight >= MIN_SUGGESTION_WEIGHT]


def field_terms(found: Sequence[Mapping[str, object]], field: str, prefix: str) -> list[tuple[str, int]]:
    """The words of a field beginning with ``prefix``, with how many entities hold each, the 5 most first and
    then by word: the in-memory reading of a field's terms (DD-094).
    """  # noqa: D205 - one sentence
    tally: Counter[str] = Counter()
    for values in found:
        value = values.get(field)
        items = value if isinstance(value, list) else [] if value is None else [value]
        tally.update({word.lower() for item in items for word in _WORD.findall(str(item))})
    matching = [(term, count) for term, count in tally.items() if term.startswith(prefix)]
    return sorted(matching, key=lambda item: (-item[1], item[0]))[:TERM_COUNT]


def top_terms(per_field: Mapping[str, Sequence[tuple[str, int]]]) -> list[str]:
    """``getTopTerms``: the fields' terms with their frequencies summed, the 5 most frequent, then by term (DV-81)."""
    summed: Counter[str] = Counter()
    for terms in per_field.values():
        for term, count in terms:
            summed[term] += count
    return [term for term, _ in sorted(summed.items(), key=lambda item: (-item[1], item[0]))[:TERM_COUNT]]


def _term_matches(term: str, words: set[str]) -> bool:
    if term.endswith("*"):
        return any(word.startswith(term[:-1]) for word in words)
    return term in words
