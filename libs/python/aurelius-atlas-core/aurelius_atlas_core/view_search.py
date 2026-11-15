"""``view_search``: the search door of the view family (AVR-02..09, AVR-11, AVR-13, DD-584 to DD-587).

One door over the entity index for every active entity (DD-586): the 14.4 engine's machinery — its field
table idea, filter, facet and sort composition (DD-523, DD-525) — pointed at the view's field names
(AVR-03) instead of the engine's. The request is the door's own: flat values, ``limit``/``offset`` paging,
``{cards, facets, total}`` out (AVR-08); the wire the engine keeps for legacy parity is not reused (DD-584).
Each hit's stored document becomes a 16.1 card, so a card holds the entity's own values plus what the
indexer stored; a card of an entity without a document has empty derived fields (AVR-11, AVS-02).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NoReturn

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_model.views import EntityCard
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.app_search_document import APP_SEARCH_FIELD, QUALITY_TOTALS_FIELD
from aurelius_atlas_core.app_search_engine import (
    MAX_FACET_SIZE,
    Engine,
    EngineField,
    Errors,
    Facet,
    Kind,
    Search,
    filter_clauses,
    known,
    parse_sort,
    plain,
    query_body,
)
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.free_text import MAX_QUERY_LENGTH
from aurelius_atlas_core.search_aggregator import ASSET_ENTITY_TYPE, OWNER_ATTRIBUTE
from aurelius_atlas_core.search_fields import KEYWORD, field_name, kind_of
from aurelius_atlas_core.search_query import FACET_SIZE, MAX_NEAREST, VectorQuery
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.view_derivation import QUALITY_DIMENSIONS, card_of, view_of

VIEW_ENGINE = "view"
"""The door's population by name: every active entity, typed out by ``filters.typeName`` (AVR-11, DD-586)."""

HOLDS = ({"term": {"state": "ACTIVE"}},)
"""The door holds every active entity — not only the ones with a document, as the engine's population does
(AVR-11, DD-586); ``filters.typeName`` narrows as ASE-03's population did."""

DEFAULT_LIMIT = 10
MAX_LIMIT = 100
DEFAULT_OFFSET = 0
MAX_OFFSET = 10_000
"""``limit`` is 1 to 100 (10 by default) and ``offset`` 0 to 10,000 (0 by default), the window's end (AVR-07)."""

OPTION_NAMES = ("query", "filters", "facets", "sort", "limit", "offset", "mode")
"""The request's keys; any other is refused (AVR-02, ASV-01)."""

MODES = ("keyword", "semantic", "hybrid")
"""The door's modes (ASV-01): words alone, meaning alone, or both scored together (ADR 059, DD-595)."""

NEAREST_WINDOW = MAX_NEAREST
"""A meaning mode's window: ``offset + limit`` is at most 1,000, 11.4's rule of the same kNN search (ASV-08, DD-441)."""

_NAME_ATTRIBUTES = ("name", "qualifiedName", "definition")
"""The card fields matched as words, however many types store them under their own qualified name (AVR-04)."""

_MATCHED = (
    "typeName",
    "guid",
    "superTypeNames",
    "status",
    "createdBy",
    "updatedBy",
    "labels",
    "classificationNames",
)
"""The table's other text fields a query reaches: exact, as AVR-04 asks — a word matches a whole stored value."""

_TOTAL_PARTS = ("score", "count", "total")
"""The quality sub-fields a filter or facet names as ``quality.<dimension>.<part>`` (AVR-03)."""

SERVICE_TYPE = "serviceType"
OWNER = "owner"
"""The door's facet names that may count no field of the index (VSR-01, DD-599).

``serviceType`` is DD-093's ``ServiceTypeAggregator`` over the type counts, so it counts every matched
entity's type and not only the page of cards; ``owner`` counts ``Asset``'s owner attribute where the
registry defines one, and nothing where it does not. The aggregator itself stays for the wire's answers
until 16.6 (VSR-10).
"""


@dataclass
class DoorRequest:
    """A search request checked against the door's fields, ready to run (AVR-02, ASV-01)."""

    query: str = ""
    filters: list[dict[str, Any]] = field(default_factory=list)
    facets: dict[str, Facet] = field(default_factory=dict)
    sort: list[tuple[str, str]] = field(default_factory=list)
    limit: int = DEFAULT_LIMIT
    offset: int = DEFAULT_OFFSET
    mode: str = "keyword"
    """The door's mode (ASV-01): ``keyword``, or a meaning mode the caller embedded a query for (ASV-03, ASV-05)."""


def name_paths(registry: TypeRegistry) -> dict[str, tuple[str, ...]]:
    """The search paths of each name attribute, by bare name: every entity type's, sorted (AVR-04, DD-586).

    A value of ``name`` is stored under the qualified name of the type that defines it, so the field the door
    calls ``name`` is a set of index paths, one per defining type — ``filters.typeName`` of one type narrows
    it to its one path (DD-586).
    """
    paths: dict[str, set[str]] = {name: set() for name in _NAME_ATTRIBUTES}
    for found_type in registry.types(TypeCategory.ENTITY):
        if not isinstance(found_type, EntityType):
            continue
        for attribute in found_type.all_attributes.values():
            if str(attribute.name) in paths and kind_of(attribute.attribute_type) == KEYWORD:
                paths[str(attribute.name)].add(f"{KEYWORD}.{attribute.qualified_name}")
    return {name: tuple(f"search.{path}" for path in sorted(found)) for name, found in paths.items()}


def door_fields(registry: TypeRegistry, type_name: str | None = None) -> dict[str, EngineField]:
    """The door's field table (AVR-03): the card's fields, their stored paths, and the quality sub-fields.

    ``type_name`` narrows the per-type fields — ``name``, ``qualifiedName``, ``definition`` — to that type's
    own path when it defines them: a filter, facet or sort of one of them then reads a single index field
    (DD-586); without it they hold every type's paths and only filtering and matching reach them.
    """
    paths = name_paths(registry)
    fields: dict[str, EngineField] = {
        "guid": EngineField(Kind.TEXT, path="guid"),
        "typeName": EngineField(Kind.TEXT, path="typeName"),
        "superTypeNames": EngineField(Kind.TEXT, path="superTypeNames"),
        "status": EngineField(Kind.TEXT, path="state"),
        "createTime": EngineField(Kind.NUMBER, path="createTime"),
        "updateTime": EngineField(Kind.NUMBER, path="updateTime"),
        "createdBy": EngineField(Kind.TEXT, path="createdBy"),
        "updatedBy": EngineField(Kind.TEXT, path="updatedBy"),
        "labels": EngineField(Kind.TEXT, path="labels"),
        "classificationNames": EngineField(Kind.TEXT, path=f"search.{KEYWORD}.__traitNames"),
        "governed": EngineField(Kind.BOOL, path="governed", missing=False),
        "stale": EngineField(Kind.BOOL, path=f"{APP_SEARCH_FIELD}.stale", missing=False),
    }
    for name in _NAME_ATTRIBUTES:
        if type_name is None:
            fields[name] = EngineField(Kind.TEXT, paths=paths[name])
        else:
            single = _path_of(paths[name], type_name, registry)
            fields[name] = (
                EngineField(Kind.TEXT, path=single, text=f"{single}.text")
                if single is not None
                else EngineField(Kind.TEXT)
            )
    owner = None if (asset := registry.entity_type(ASSET_ENTITY_TYPE)) is None else asset.attribute(OWNER_ATTRIBUTE)
    owner_path = None if owner is None else field_name(owner)
    fields[OWNER] = EngineField(Kind.TEXT, path=None if owner_path is None else f"search.{owner_path}")
    fields[SERVICE_TYPE] = EngineField(Kind.TEXT)
    # ``Asset``'s owner attribute, however the registry stores it, and the service-type roll-up (VSR-01):
    # both names are always asked for, and count nothing where the registry holds nothing for them (DD-599).
    for dimension in QUALITY_DIMENSIONS:
        for part in _TOTAL_PARTS:
            path = f"{QUALITY_TOTALS_FIELD}.{dimension}.{part}"
            fields[f"quality.{dimension}.{part}"] = EngineField(Kind.NUMBER, path=path, missing=0.0)
    return fields


def _path_of(paths: tuple[str, ...], type_name: str, registry: TypeRegistry) -> str | None:
    """The one path of a name attribute that ``type_name``'s entities store, or none when it stores none."""
    entity_type = registry.entity_type(type_name)
    if entity_type is None:
        return None
    for name in _NAME_ATTRIBUTES:
        attribute = entity_type.attribute(name)
        if attribute is not None and kind_of(attribute.attribute_type) == KEYWORD:
            path = f"search.{KEYWORD}.{attribute.qualified_name}"
            return path if path in paths else None
    return None


def query_fields(registry: TypeRegistry) -> dict[str, float]:
    """The fields a query's words are matched in, with their weights (AVR-04, DD-525).

    The words go over every type's analysed name, qualified name and definition and over the classification
    names; the other text fields of the table are reached whole — a word matches a type name only by naming it
    exactly.
    """
    fields: dict[str, float] = dict.fromkeys(_MATCHED, 1.0)
    for paths in name_paths(registry).values():
        fields.update({f"{path}.text": 1.0 for path in paths})
    return fields


def parse(body: object, fields: Mapping[str, EngineField]) -> DoorRequest:
    """The request checked against the door's fields, one message per refusal (AVR-02, AVR-13).

    ``facets`` is a list of field names or an object of them with a ``size`` (1 to 250, 10 by default);
    ``sort`` is a field or ``_score`` with ``asc`` or ``desc``, or a list (AVR-05, AVR-06). A facet or sort of
    a field with no single stored value is refused (AVR-05), unless ``fields`` narrowed it (DD-586). A facet
    counts a quality score sub-field as a named field (DD-587); any other number field is refused (AVR-05).

    Raises:
        AtlasError: ``VIEW_REFUSED`` with every problem found.
    """
    if not isinstance(body, dict):
        _refuse(["The request body must be a JSON object"])
    errors = Errors(fields)
    for key in body:
        if key not in OPTION_NAMES:
            errors.add(f"The request holds an unknown option: {key}")
    request = DoorRequest(query=_query(body, errors))
    request.mode = _mode(body, errors)
    if (filters := body.get("filters")) is not None:
        request.filters = [filter_clauses(filters, errors, "Filters")]
    if (facets := body.get("facets")) is not None:
        request.facets = _facets(facets, fields, errors)
    request.sort = _sort(body, fields, errors)
    request.limit = _bounded(body, "limit", (1, MAX_LIMIT), DEFAULT_LIMIT, errors)
    request.offset = _bounded(body, "offset", (DEFAULT_OFFSET, MAX_OFFSET), DEFAULT_OFFSET, errors)
    if request.mode != "keyword":
        _checked_for_meaning(request, errors)
    if errors.messages:
        _refuse(errors.messages)
    return request


def _sort(body: dict[str, Any], fields: Mapping[str, EngineField], errors: Errors) -> list[tuple[str, str]]:
    """The requested sort; of a field with no single stored value, refused (AVR-05, DD-586)."""
    if (sort := body.get("sort")) is None:
        return []
    requested = parse_sort(sort, errors)
    for name, _direction in requested:
        if name != "_score" and fields[name].path is None:
            errors.add(f"Sort by {name} needs one stored value: filters.typeName must name one type")
    return requested


def _mode(body: dict[str, Any], errors: Errors) -> str:
    """The requested mode, ``keyword`` where the body leaves it out; any other value is refused (ASV-01)."""
    if (mode := body.get("mode")) is None:
        return "keyword"
    if not isinstance(mode, str) or mode not in MODES:
        errors.add(f"Mode must be one of: {', '.join(MODES)}")
        return "keyword"
    return mode


def _checked_for_meaning(request: DoorRequest, errors: Errors) -> None:
    """A meaning mode's own refusals, beside the shared ones (ASV-06, ASV-07, ASV-08).

    The query must carry words to embed, the order can only be by score, and the window stays
    inside 11.4's (DD-441): a kNN search cannot page past its own ``k``.
    """
    if not request.query.strip():
        errors.add(f"A {request.mode} search needs a query to embed")
    for name, direction in request.sort:
        if name != "_score" or direction != "desc":
            errors.add(f"A {request.mode} search answers by score descending only")
            break
    if request.offset + request.limit > NEAREST_WINDOW:
        errors.add(f"A {request.mode} search answers at most {NEAREST_WINDOW} entities: offset + limit is over it")


def _query(body: dict[str, Any], errors: Errors) -> str:
    """The query text, within the length limit; empty matches every document (AVR-02, AVR-04)."""
    if (query := body.get("query", "")) is None:
        return ""
    if not isinstance(query, str):
        errors.add("Query must be a string")
        return ""
    if len(query) > MAX_QUERY_LENGTH:
        errors.add(f"Query must be at most {MAX_QUERY_LENGTH} characters")
    return query


def _facets(facets: object, fields: Mapping[str, EngineField], errors: Errors) -> dict[str, Facet]:
    """Each asked field's facet, in request order; only fields with one stored value can be counted (AVR-05)."""
    if not isinstance(facets, (dict, list)):
        errors.add("Facets must be a list of field names or an object of them")
        return {}
    asked = facets.items() if isinstance(facets, dict) else ((name, {}) for name in facets)
    parsed: dict[str, Facet] = {}
    for name, options in asked:
        if known(name, errors, "Facets") is None:
            continue
        if name in (SERVICE_TYPE, OWNER) and fields[name].path is None:
            # Counted outside the index: ``serviceType`` is summed from the type counts in the answer and an
            # ``owner`` the registry never defined counts no one. Both are asked for and answered empty
            # rather than refused (VSR-01, DD-599).
            parsed[name] = Facet(_size(name, options, errors), {"_count": "desc"})
            continue
        if fields[name].kind is Kind.NUMBER and not name.startswith("quality."):
            errors.add(f"Facet for {name}: number fields hold no values to count")
            continue
        if fields[name].path is None:
            errors.add(f"Facet for {name}: the field holds no single value to count")
            continue
        parsed[name] = Facet(_size(name, options, errors), {"_count": "desc"})
    return parsed


def _size(name: object, options: object, errors: Errors) -> int:
    """A facet's asked size, the default kept with the problem named when it is no size (AVR-05)."""
    if not isinstance(options, dict):
        errors.add(f"Facet for {name} must be an object with a size")
        return 10
    size = options.get("size", 10)
    if not isinstance(size, int) or isinstance(size, bool) or not 1 <= size <= MAX_FACET_SIZE:
        errors.add(f"Facet size for {name} must be between 1 and {MAX_FACET_SIZE}")
        return 10
    return size


def _bounded(body: dict[str, Any], name: str, bounds: tuple[int, int], default: int, errors: Errors) -> int:
    """A page number of the body within its bounds, ``default`` where the body leaves it out (AVR-07)."""
    if (value := body.get(name)) is None:
        return default
    least, most = bounds
    if not isinstance(value, int) or isinstance(value, bool) or not least <= value <= most:
        errors.add(f"{name.title()} must be between {least} and {most}")
        return default
    return value


def _refuse(messages: list[str]) -> NoReturn:
    """Answer every problem found as the door's refusal (AVR-13): the Atlas shape, one message each.

    Raises:
        AtlasError: ``VIEW_REFUSED`` always.
    """
    raise AtlasError(AtlasErrorCode.VIEW_REFUSED, "; ".join(messages), messages=messages)


class ViewSearchEngine:
    """The search door over ``documents``' entity index, typed by ``registry`` (AVR-08, DD-584)."""

    def __init__(self, documents: ElasticsearchEntityDocuments, registry: TypeRegistry) -> None:
        """The door reading ``documents`` and naming attributes and fields through ``registry``."""
        self._documents = documents
        self._registry = registry

    async def search(
        self, body: object, *, vector: Sequence[float] | None = None, weight: float = 1.0
    ) -> dict[str, Any]:
        """The answer to a search request: ``{cards, facets, total}`` (AVR-08).

        In a meaning mode, ``vector`` is the query's embedding and the door answers the nearest
        among those it holds, the filters inside the kNN search (ASV-03, DD-596). ``weight`` is
        the hybrid score's (ASV-05, DD-442), 1 in the pure semantic mode as in 11.4. The answer's
        ``total`` and facets count the kNN search's hits, not the whole population (ASV-04, DD-597).

        Raises:
            AtlasError: ``VIEW_REFUSED`` for a request the door refuses (AVR-02, AVR-13).
        """
        fields = door_fields(self._registry, _single_type(body))
        request = parse(body, fields)
        search = Search(
            engine=Engine(VIEW_ENGINE, HOLDS, fields),
            query="" if request.mode == "semantic" else request.query,
            # The pure semantic mode matches no words, as in 11.4 (DD-441); the text still had to carry them (ASV-06).
            filters=request.filters,
            facets={name: [facet] for name, facet in request.facets.items()},
            sort=request.sort,
            size=request.limit,
            start=request.offset,
            search_fields=query_fields(self._registry),
            vector=None
            if vector is None or request.mode == "keyword"
            else VectorQuery(tuple(vector), request.offset + request.limit, weight),
        )
        response = await self._documents.search_app_search(**_asked(search, request))
        hits = response["hits"]
        aggregations = response.get("aggregations") or {}
        facets = _answered_facets(request.facets, aggregations)
        if SERVICE_TYPE in request.facets:
            feed = aggregations.get(_FEED, aggregations.get("typeName#0", {})).get("buckets", [])
            facets[SERVICE_TYPE] = _service_types(self._registry, feed)[: request.facets[SERVICE_TYPE].size]
        return {
            "cards": [_card(hit["_source"], self._registry).to_json() for hit in hits["hits"]],
            "facets": facets,
            "total": int(hits["total"]["value"]),
        }


_FEED = "$serviceTypes#0"
"""The door's private type count feeding ``serviceType``: DD-093's facet size of 100 values, asked only when
no asked facet is a wide enough type count (DD-599)."""


def _asked(search: Search, request: DoorRequest) -> dict[str, Any]:
    """The search's query body, with the whole type count bolted on when ``serviceType`` needs a feed of
    its own: the roll-up counts every matched entity's type, and a short asked type facet leaves some out
    (DD-093, DD-599).
    """  # noqa: D205 - one sentence
    body = query_body(search)
    if SERVICE_TYPE in request.facets:
        asked = request.facets.get("typeName")
        if (asked is None or asked.size < FACET_SIZE) and search.engine.fields["typeName"].path is not None:
            body["aggs"][_FEED] = {
                "terms": {"field": "typeName", "size": FACET_SIZE + 1, "order": [{"_count": "desc"}, {"_key": "asc"}]}
            }
    return body


def _service_types(registry: TypeRegistry, buckets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """``ServiceTypeAggregator``: the type counts added up by service type, those counted none left out
    (VSR-01, DD-093).
    """  # noqa: D205 - one sentence
    totals = dict.fromkeys(registry.all_service_types(), 0)
    for bucket in buckets:
        entity_type = registry.entity_type(plain(bucket["key"]))
        service = None if entity_type is None else entity_type.service_type
        if service in totals:
            totals[service] += bucket["doc_count"]
    return [
        {"value": service, "count": count}
        for service, count in sorted(
            ((service, count) for service, count in totals.items() if count), key=lambda item: (-item[1], item[0])
        )
    ]


def _single_type(body: object) -> str | None:
    """The one type ``filters.typeName`` names, through conjunctions only; None for a door over everything."""
    filters = body.get("filters") if isinstance(body, dict) else None
    if not isinstance(filters, dict):
        return None
    value = filters.get("typeName")
    if isinstance(value, str):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
        return value[0]
    nested = filters.get("all")
    for item in nested if isinstance(nested, list) else []:
        if (found := _single_type({"filters": item})) is not None:
            return found
    return None


def _card(source: Mapping[str, Any], registry: TypeRegistry) -> EntityCard:
    """One hit's card: the view of its stored document, projected (AVR-08); its type names the attributes."""
    stored = StoredEntity.model_validate(source)
    entity_type = registry.entity_type(stored.type_name)
    if entity_type is None:  # pragma: no cover - the store only holds entities of known types
        raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, f"the type {stored.type_name} of entity {stored.guid}")
    return card_of(view_of(stored, entity_type))


def _answered_facets(facets: Mapping[str, Facet], aggregations: Mapping[str, Any]) -> dict[str, list[Any]]:
    """Each asked field's ``{value, count}`` entries in request order, empty values left out (AVR-05, AVR-08)."""
    answered: dict[str, list[Any]] = {}
    for name, facet in facets.items():
        buckets = aggregations.get(f"{name}#0", {}).get("buckets", [])
        answered[name] = [
            {"value": plain(bucket["key"]), "count": bucket["doc_count"]}
            for bucket in buckets
            if bucket["key"] not in ("", None)
        ][: facet.size]
    return answered
