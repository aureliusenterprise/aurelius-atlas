"""Request query parameters as models: every parameter of an endpoint in one model, checks included.

Atlas reads its query parameters through JAX-RS: the first value of a name, a number as Java's
``Short``/``Integer``/``Long`` parse it, an enum by its name, and a text over 4,096 characters refused
before anything else (DV-39). The markers below read a request's parameters that way, ``read_params``
fills a model with them, and the model's own checks hold the endpoint's rules — a value of none of its
type fails with the same ``BAD_REQUEST`` text as the hand-written code it replaces.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Annotated, Any

from pydantic import BaseModel
from pydantic.alias_generators import to_camel

from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.discovery import SortOrder
from aurelius_atlas_model.errors import (
    AtlasError,
    AtlasErrorCode,
    java_string,
    validate_guid,
    validate_param_length,
    validate_query_length,
)
from aurelius_atlas_model.lineage import LineageDirection

INT_RANGE = (-(2**31), 2**31 - 1)
"""A Java ``int``'s values."""

LONG_RANGE = (-(2**63), 2**63 - 1)
"""A Java ``long``'s values."""

SHORT_RANGE = (-(2**15), 2**15 - 1)
"""A Java ``short``'s values."""

INVALID_PARAMETER = "Invalid value {value} for query parameter {name}"
"""The ``BAD_REQUEST`` text of a parameter that is no value of its type (DV-39)."""

START_AFTER_END = "fromTimestamp should be less than toTimestamp"
"""``getEntityHeaders`` refuses a start after now (CAU-07, DV-41)."""

NO_ATTRIBUTE_SEARCH = "attrName : {name}, attrValue: {value} for attribute search."
"""``searchUsingAttribute`` without its attribute and prefix (SRC-11)."""

NO_TIME = "startTime or endTime is null/empty."
"""The metrics history of a range whose times are missing (MHS-03, DV-136)."""

NEGATIVE_PAGE = "Limit/offset should be non-negative"
"""A search paged with a negative ``limit`` or ``offset`` (SRC-02, QSR-01, SBM-04)."""

FILTERS_WITHOUT_TYPE = "EntityFilters specified without Type name"
"""A search with entity filters but no type named (SRC-02, QSR-01, SBM-04)."""

MAX_DSL_QUERY_LENGTH = 4096
"""``atlas.graph.dsl-max-query-str-length``'s default (DSE-01)."""

DSL_LENGTH_SETTING = "atlas.graph.dsl-max-query-str-length"
"""The setting that raises the DSL query limit."""

AUDIT_COUNT_DEFAULT = 100
"""``getAuditEvents``' ``count`` when the request gives none (AUD-09)."""


def parse_number(name: str, value: str, bounds: tuple[int, int] = INT_RANGE) -> int:
    """``Short``/``Integer``/``Long`` ``valueOf`` of a parameter: digits within the type's range (DV-39).

    Raises:
        AtlasError: ``BAD_REQUEST`` for text that is no number of the type.
    """
    try:
        number = int(value)
    except ValueError as error:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, INVALID_PARAMETER.format(value=value, name=name)) from error
    if not bounds[0] <= number <= bounds[1] or not value.lstrip("-+").isdigit():
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, INVALID_PARAMETER.format(value=value, name=name))
    return number


def parse_choice[T](name: str, value: str, parse: Callable[[str], T]) -> T:
    """A parameter read by ``parse``, as JAX-RS converts an enum; refused when it cannot (DV-39).

    Raises:
        AtlasError: ``BAD_REQUEST`` for text that names none.
    """
    try:
        return parse(value)
    except ValueError as error:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, INVALID_PARAMETER.format(value=value, name=name)) from error


def parse_flag(value: str | None, *, default: bool = False) -> bool:
    """A boolean parameter as JAX-RS reads one: true only for ``true`` in any case; ``default`` for none."""
    return default if value is None else value.lower() == "true"


type RequestParams = Mapping[str, str]
"""A request's query parameters, first value per name; a repeated name reads as a list through ``items``."""


def _list(params: RequestParams, name: str) -> list[str]:
    """Every value of a name, in order: ``getlist`` when there is one, else the mapping's value."""
    getlist = getattr(params, "getlist", None)
    if getlist is not None:
        return list(getlist(name))
    value = params.get(name)
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [value]


def _first(params: RequestParams, name: str) -> str | None:
    values = _list(params, name)
    return values[0] if values else None


def _all(params: RequestParams, name: str) -> list[str]:
    return _list(params, name)


def _items(params: RequestParams) -> list[tuple[str, str]]:
    """Every parameter as it arrived, repeated names in order; a plain mapping answers its items."""
    multi = getattr(params, "multi_items", None)
    return list(multi()) if multi is not None else list(params.items())


@dataclass(frozen=True)
class Param:
    """The marker of a query-parameter field: how the request's value is read (JAX-RS semantics)."""

    name: str = ""
    default: Any = None

    def lookup(self, field_name: str) -> str:
        """The parameter's name in the request: the marker's, else the field's Java name."""
        return self.name or to_camel(field_name)

    def read(self, params: RequestParams, name: str) -> Any:  # noqa: ANN401 - the field's value
        """The parameter's value for a model field."""
        value = _first(params, name)
        return self.default if value is None else value


@dataclass(frozen=True)
class NumberParam(Param):
    """A Java ``short``/``int``/``long`` parameter: digits of the type, the default when absent (DV-39)."""

    bounds: tuple[int, int] = INT_RANGE

    def read(self, params: RequestParams, name: str) -> Any:  # noqa: ANN401 - the field's value
        """The parameter as a Java number of ``bounds``; ``default`` when absent (DV-39)."""
        value = _first(params, name)
        return self.default if value is None else parse_number(name, value, self.bounds)


@dataclass(frozen=True)
class LongParam(Param):
    """A Java ``long`` parameter."""

    def read(self, params: RequestParams, name: str) -> Any:  # noqa: ANN401 - the field's value
        """The parameter as a Java ``long``; ``default`` when absent (DV-39)."""
        value = _first(params, name)
        return self.default if value is None else parse_number(name, value, LONG_RANGE)


@dataclass(frozen=True)
class FlagParam(Param):
    """A boolean parameter: true only for ``true`` in any case (``Boolean.valueOf``)."""

    default: bool = False

    def read(self, params: RequestParams, name: str) -> Any:  # noqa: ANN401 - the field's value
        """The parameter as ``Boolean.valueOf`` reads it; ``default`` when absent."""
        return parse_flag(_first(params, name), default=self.default)


@dataclass(frozen=True)
class EnumParam(Param):
    """An enum parameter, read by ``parse``; the default when absent (DV-39)."""

    parse: Callable[[str], Any] = str

    def read(self, params: RequestParams, name: str) -> Any:  # noqa: ANN401 - the field's value
        """The parameter as ``parse`` reads it; ``default`` when absent (DV-39)."""
        value = _first(params, name)
        return self.default if value is None else parse_choice(name, value, self.parse)


@dataclass(frozen=True)
class ListParam(Param):
    """A repeated parameter: every value, in order; empty when none."""

    def read(self, params: RequestParams, name: str) -> Any:  # noqa: ANN401 - the field's value
        """Every value of the parameter, in the order it arrived."""
        return _all(params, name)


@dataclass(frozen=True)
class AttrParam(Param):
    """The ``attr:<name>`` parameters of a unique attribute: each name with its first value (ERD-08)."""

    prefix: str = "attr:"

    def lookup(self, field_name: str) -> str:  # noqa: ARG002 - the parameters are read by prefix
        """The marker's prefix, not a name: every ``attr:<name>`` parameter belongs to the field."""
        return self.prefix

    def read(self, params: RequestParams, name: str) -> Any:  # noqa: ANN401,ARG002 - the field's value; read by prefix
        """Each ``attr:<name>`` parameter with its first value, in the order the parameters arrive."""
        found: dict[str, Any] = {}
        for key, value in _items(params):
            if key.startswith(self.prefix):
                found.setdefault(key.removeprefix(self.prefix), value)
        return found


@dataclass(frozen=True)
class AttrSetParam(Param):
    """The ``attr_<n>:<name>`` parameters: one set per index, in the order indices appear (ERD-08, DV-19)."""

    prefix: str = "attr_"

    def lookup(self, field_name: str) -> str:  # noqa: ARG002 - the parameters are read by prefix
        """The marker's prefix, not a name: every ``attr_<n>:<name>`` parameter belongs to the field."""
        return self.prefix

    def read(self, params: RequestParams, name: str) -> Any:  # noqa: ANN401,ARG002 - the field's value; read by prefix
        """One set per index of ``attr_<n>:<name>``, in the order the indices appear (DV-19)."""
        sets: dict[str, dict[str, Any]] = {}
        seen: set[str] = set()
        for key, value in _items(params):
            if not key.startswith(self.prefix) or key in seen:
                continue
            seen.add(key)
            index, separator, attribute = key.removeprefix(self.prefix).partition(":")
            if separator:
                sets.setdefault(index, {})[attribute] = value
        return list(sets.values())


def read_params[M: BaseModel](model: type[M], params: RequestParams) -> M:
    """``model`` filled from a request's query parameters, each read by its marker (DV-39, TYR-04).

    A field with no marker is the parameter's first value or its default; the model's own checks then
    hold the endpoint's rules. The values arrive under the field names, which the models accept.

    Raises:
        AtlasError: ``BAD_REQUEST`` or the model's own code for a value its checks refuse.
    """
    values: dict[str, Any] = {}
    for field_name, info in model.model_fields.items():
        marker = next((item for item in info.metadata if isinstance(item, Param)), None)
        if marker is not None:
            values[field_name] = marker.read(params, marker.lookup(field_name))
        else:
            default = None if info.is_required() else info.default
            value = _first(params, info.alias or to_camel(field_name))
            values[field_name] = default if value is None else value
    return model.model_validate(values)


class PageParams(BaseModel):
    """The paging parameters every list takes: ``limit`` (-1, all), ``offset`` (0) and ``sort`` (GLS-05)."""

    limit: Annotated[int, NumberParam(default=-1)]
    offset: Annotated[int, NumberParam(default=0)]
    sort: str | None = None

    def sort_name(self) -> str:
        """The ``sort`` parameter as the service reads it: ``ASC`` when absent (GLS-05)."""
        return self.sort or "ASC"


class EntityGuidParams(BaseModel):
    """The ``guid`` parameters of a bulk read or delete: UUID text, none longer than a parameter (ERD-01, EDL-02)."""

    guids: Annotated[list[str], ListParam("guid")]

    def checked(self) -> list[str]:
        """Every GUID within a parameter's length and as UUID text (EDL-01, DV-161).

        Raises:
            AtlasError: ``INVALID_QUERY_PARAM_LENGTH``; ``INVALID_OBJECT_ID``.
        """
        for guid in self.guids:
            validate_guid("guid", guid)
        return self.guids


class ExtendedInfoParams(BaseModel):
    """``extendedInfo`` of a relationship read: the ends' headers with it (REL-06)."""

    extended_info: Annotated[bool, FlagParam("extendedInfo")]


class EntityReadParams(BaseModel):
    """The reading parameters of the entity endpoints: ``minExtInfo`` and ``ignoreRelationships``."""

    min_ext_info: Annotated[bool, FlagParam("minExtInfo")]
    ignore_relationships: Annotated[bool, FlagParam("ignoreRelationships")]


class EntityDeleteParams(BaseModel):
    """``deleteType`` as a request asks for it; the server's setting decides what it means (EDL-04, DD-059)."""

    delete_type: Annotated[str | None, Param("deleteType")]


class UniqueAttributeParams(BaseModel):
    """The unique-attribute parameters of an endpoint: ``attr:<name>``, and the sets of the bulk (ERD-08)."""

    attributes: Annotated[dict[str, str], AttrParam()]
    attribute_sets: Annotated[list[dict[str, str]], AttrSetParam()]


class PartialAttributeParams(BaseModel):
    """The ``name`` parameter of ``partialUpdateEntityAttrByGuid``: the attribute to set (EWR-15)."""

    name: Annotated[str | None, Param()]

    def checked(self) -> str | None:
        """The name at a parameter's length, when given (EWR-15).

        Raises:
            AtlasError: ``INVALID_QUERY_PARAM_LENGTH``.
        """
        if self.name is not None:
            validate_param_length("name", self.name)
        return self.name


class ClassificationDeleteParams(BaseModel):
    """``associatedEntityGuid`` of ``deleteClassification`` (CLS-09)."""

    associated_entity_guid: Annotated[str | None, Param("associatedEntityGuid")]

    def checked(self) -> str | None:
        """The GUID at a parameter's length, when given (CLS-09).

        Raises:
            AtlasError: ``INVALID_QUERY_PARAM_LENGTH``.
        """
        if self.associated_entity_guid is not None:
            validate_param_length("associatedEntityGuid", self.associated_entity_guid)
        return self.associated_entity_guid


class EntityAuditParams(BaseModel):
    """The parameters of ``getAuditEvents``: what to list, how sorted and paged (AUD-06 to AUD-09)."""

    start_key: Annotated[str | None, Param("startKey")]
    audit_action: Annotated[EntityAuditActionV2 | None, EnumParam("auditAction", parse=EntityAuditActionV2.from_string)]
    count: Annotated[int, NumberParam(bounds=SHORT_RANGE, default=AUDIT_COUNT_DEFAULT)]
    offset: Annotated[int, NumberParam(default=-1)]
    sort_by: Annotated[str | None, Param("sortBy")]
    sort_order: Annotated[str | None, Param("sortOrder")]


class EntityHeadersParams(BaseModel):
    """``tagUpdateStartTime`` of ``getEntityHeaders``: a time not after now (CAU-07, DV-41)."""

    tag_update_start_time: Annotated[int, LongParam("tagUpdateStartTime", default=0)]

    def checked(self, now: int) -> int:
        """The start time, refused when it is after ``now``.

        Raises:
            AtlasError: ``BAD_REQUEST`` naming the rule (DV-41).
        """
        if self.tag_update_start_time > now:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, START_AFTER_END)
        return self.tag_update_start_time


class LineageParams(BaseModel):
    """``direction`` (``BOTH``) and ``depth`` (3) of a lineage read (LIN-01, DV-39)."""

    direction: Annotated[LineageDirection, EnumParam(parse=LineageDirection, default=LineageDirection.BOTH)]
    depth: Annotated[int, NumberParam(default=3)]


class SavedSearchParams(BaseModel):
    """``user`` of the saved-search reads: at a parameter's length (SVS-04)."""

    user: Annotated[str | None, Param()]

    def checked(self) -> str | None:
        """The user at a parameter's length, when given (SVS-04).

        Raises:
            AtlasError: ``INVALID_QUERY_PARAM_LENGTH``.
        """
        if self.user is not None:
            validate_param_length("user", self.user)
        return self.user


class BasicSearchParams(BaseModel):
    """The query parameters of ``searchUsingBasic``: a search, only its lengths checked (SRC-11).

    Defaults let ``validate_basic_search_parameters`` check a body's ``SearchParameters`` through the same rule.
    """

    query: Annotated[str | None, Param()] = None
    type_name: Annotated[str | None, Param("typeName")] = None
    classification: Annotated[str | None, Param("classification")] = None
    sort_by: Annotated[str | None, Param("sortBy")] = None
    sort_order: Annotated[SortOrder | None, EnumParam("sortOrder", parse=SortOrder)] = None
    exclude_deleted_entities: Annotated[bool, FlagParam("excludeDeletedEntities")] = False
    limit: Annotated[int, NumberParam(default=0)] = 0
    offset: Annotated[int, NumberParam(default=0)] = 0
    marker: Annotated[str | None, Param()] = None

    def checked(self) -> None:
        """The names and the query at their lengths (FTX-01, TYR-04).

        Raises:
            AtlasError: ``INVALID_QUERY_PARAM_LENGTH`` or ``INVALID_QUERY_LENGTH``.
        """
        for name, value in (
            ("typeName", self.type_name),
            ("classification", self.classification),
            ("sortBy", self.sort_by),
        ):
            if value is not None:
                validate_param_length(name, value)
        validate_query_length(self.query)


class FullTextSearchParams(BaseModel):
    """The parameters of ``searchUsingFullText``: a query of at most the full-text limit (FTX-05)."""

    query: Annotated[str | None, Param()]
    exclude_deleted_entities: Annotated[bool, FlagParam("excludeDeletedEntities")]
    limit: Annotated[int, NumberParam(default=0)]
    offset: Annotated[int, NumberParam(default=0)]

    def checked(self) -> str:
        """The query, refused when longer than the limit; it is read as empty when absent (FTX-05).

        Raises:
            AtlasError: ``INVALID_QUERY_LENGTH``.
        """
        validate_query_length(self.query)
        return self.query or ""


class DslSearchParams(BaseModel):
    """The parameters of ``searchUsingDSL``: names at their length, the query at the DSL limit (DSE-01).

    Defaults let ``validate_dsl_search_parameters`` check values that came from elsewhere.
    """

    query: Annotated[str | None, Param()] = None
    type_name: Annotated[str | None, Param("typeName")] = None
    classification: Annotated[str | None, Param("classification")] = None
    limit: Annotated[int, NumberParam(default=0)] = 0
    offset: Annotated[int, NumberParam(default=0)] = 0

    def checked(self) -> None:
        """The names at a parameter's length, the query at the DSL limit (DSE-01).

        Raises:
            AtlasError: ``INVALID_QUERY_PARAM_LENGTH`` or ``INVALID_QUERY_LENGTH``.
        """
        for name, value in (
            ("typeName", self.type_name),
            ("classification", self.classification),
        ):
            if value is not None:
                validate_param_length(name, value)
        if self.query and len(self.query) > MAX_DSL_QUERY_LENGTH:
            raise AtlasError(AtlasErrorCode.INVALID_QUERY_LENGTH, DSL_LENGTH_SETTING)


class AttributeSearchParams(BaseModel):
    """The parameters of ``searchUsingAttribute``: the attribute and its prefix (SRC-11)."""

    attr_name: Annotated[str | None, Param("attrName")]
    attr_value_prefix: Annotated[str | None, Param("attrValuePrefix")]
    type_name: Annotated[str | None, Param("typeName")]
    limit: Annotated[int, NumberParam(default=0)]
    offset: Annotated[int, NumberParam(default=0)]

    def checked(self) -> None:
        """The names at a parameter's length, then the search's two required parameters.

        Raises:
            AtlasError: ``INVALID_QUERY_PARAM_LENGTH``, ``INVALID_PARAMETERS``.
        """
        for name, value in (
            ("attrName", self.attr_name),
            ("attrValuePrefix", self.attr_value_prefix),
            ("typeName", self.type_name),
        ):
            if value is not None:
                validate_param_length(name, value)
        if not self.attr_name and not self.attr_value_prefix:
            message = NO_ATTRIBUTE_SEARCH.format(
                name=java_string(self.attr_name), value=java_string(self.attr_value_prefix)
            )
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, message)


class QuickQueryParams(BaseModel):
    """The parameters of ``quickSearch`` by query: a query of at most the full-text limit (QSR-01, QSR-02)."""

    query: Annotated[str | None, Param()]
    type_name: Annotated[str | None, Param("typeName")]
    exclude_deleted_entities: Annotated[bool, FlagParam("excludeDeletedEntities")]
    offset: Annotated[int, NumberParam(default=0)]
    limit: Annotated[int, NumberParam(default=0)]
    sort_by: Annotated[str | None, Param("sortBy")]
    sort_order: Annotated[SortOrder | None, EnumParam("sortOrder", parse=SortOrder)]

    def checked(self) -> None:
        """The query at its length — the only check of this variant (QSR-02).

        Raises:
            AtlasError: ``INVALID_QUERY_LENGTH``.
        """
        validate_query_length(self.query)


class SuggestionsParams(BaseModel):
    """The parameters of ``getSuggestions``: a prefix, and the field to suggest from (SUG-01)."""

    prefix_string: Annotated[str | None, Param("prefixString")]
    field_name: Annotated[str | None, Param("fieldName")]


class SimilarSearchParams(BaseModel):
    """The parameters of the search for an entity's nearest: a page, refused when negative (SBM-05)."""

    type_name: Annotated[str | None, Param("typeName")]
    exclude_deleted_entities: Annotated[bool, FlagParam("excludeDeletedEntities")]
    offset: Annotated[int, NumberParam(default=0)]
    limit: Annotated[int, NumberParam(default=0)]

    def checked(self) -> None:
        """The page, refused when negative (SBM-04, SBM-05).

        Raises:
            AtlasError: ``BAD_REQUEST`` for a negative page.
        """
        if self.limit < 0 or self.offset < 0:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, NEGATIVE_PAGE)


class MetricsTimeParams(BaseModel):
    """The time range of the metrics history: two ``long``s and the type names of the range (MHS-03, DV-136)."""

    start_time: Annotated[str | None, Param("startTime")]
    end_time: Annotated[str | None, Param("endTime")]
    type_names: Annotated[list[str], ListParam("typeName")]

    def checked(self) -> tuple[int, int, list[str]]:
        """The range as ``long``s and its type names, each at a parameter's length.

        Raises:
            AtlasError: ``BAD_REQUEST`` for a missing or blank time, or one that is no ``long`` (DV-136);
                ``INVALID_QUERY_PARAM_LENGTH`` for a long one.
        """
        if self.start_time is None or not self.start_time.strip() or self.end_time is None or not self.end_time.strip():
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_TIME)
        validate_param_length("startTime", self.start_time)
        validate_param_length("endTime", self.end_time)
        for type_name in self.type_names:
            validate_param_length("typeName", type_name)
        return (
            parse_number("startTime", self.start_time, LONG_RANGE),
            parse_number("endTime", self.end_time, LONG_RANGE),
            self.type_names,
        )


class MetricsListParams(BaseModel):
    """``mininfo`` of ``getAllMetrics``: the metrics themselves unless asked without (MHS-02)."""

    min_info: Annotated[bool, FlagParam("mininfo", default=True)]


class AuditDetailsParams(BaseModel):
    """The paging of ``getAuditDetails``: ``limit`` (10) from ``offset`` (ADA-05)."""

    limit: Annotated[int, NumberParam(default=10)]
    offset: Annotated[int, NumberParam(default=0)]


class ExportImportAuditParams(BaseModel):
    """The parameters of ``getExportImportAudit``: the values each entry must match (REP-05)."""

    server_name: Annotated[str | None, Param("serverName")]
    user_name: Annotated[str | None, Param("userName")]
    operation: Annotated[str | None, Param("operation")]
    start_time: Annotated[str | None, Param("startTime")]
    end_time: Annotated[str | None, Param("endTime")]
    limit: Annotated[int, NumberParam(default=0)]
    offset: Annotated[int, NumberParam(default=0)]


class AuditConfigParams(BaseModel):
    """``useAuditConfig`` of ``ageoutAuditData``: the aging of the configuration, not of the body (AGE-01)."""

    use_audit_config: Annotated[bool, FlagParam("useAuditConfig")]
