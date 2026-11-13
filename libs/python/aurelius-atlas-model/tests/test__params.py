"""The query parameters of the endpoints, read by their models (DV-39, TYR-04).

Each marker reads as JAX-RS does — first value, Java's number parse, an enum by its name, a flag true
only for ``true`` — and every refusal carries the text the endpoints answered before the rules moved here.
"""

import pytest
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.params import (
    AttributeSearchParams,
    BasicSearchParams,
    ClassificationDeleteParams,
    DslSearchParams,
    EntityAuditParams,
    EntityGuidParams,
    EntityHeadersParams,
    EntityReadParams,
    ExportImportAuditParams,
    LineageParams,
    MetricsListParams,
    MetricsTimeParams,
    PageParams,
    QuickQueryParams,
    SavedSearchParams,
    UniqueAttributeParams,
    read_params,
)
from starlette.datastructures import QueryParams


def query(text: str) -> QueryParams:
    """A request's query parameters, repeated names kept in order."""
    return QueryParams(text)


@pytest.mark.covers("aurelius_atlas_model.params.read_params", "aurelius_atlas_model.params.PageParams.sort_name")
def test__page_reads_its_defaults_and_its_sort() -> None:
    """``limit`` -1, ``offset`` 0, and ``sort`` read as the service reads it: ``ASC`` when absent."""
    empty = read_params(PageParams, query(""))
    assert (empty.limit, empty.offset, empty.sort_name()) == (-1, 0, "ASC")
    paged = read_params(PageParams, query("limit=10&offset=5&sort=DESC"))
    assert (paged.limit, paged.offset, paged.sort_name()) == (10, 5, "DESC")


@pytest.mark.covers("aurelius_atlas_model.params.NumberParam.read", rules=["DV-39"])
def test__a_number_that_is_no_number_of_its_type_is_refused() -> None:
    """``1_000``, a decimal or a range-crossing value fail as Java's ``Integer.valueOf`` does (DV-39)."""
    for value in ("1_000", "1.0", " 1", "", "abc", "2147483648", "-2147483649"):
        with pytest.raises(AtlasError) as raised:
            read_params(PageParams, query(f"limit={value}"))
        assert raised.value.code is AtlasErrorCode.BAD_REQUEST
        assert raised.value.message == f"Invalid value {value} for query parameter limit"
    assert read_params(PageParams, query("limit=%2B7")).limit == 7


@pytest.mark.covers(
    "aurelius_atlas_model.params.ListParam.read", "aurelius_atlas_model.params.EntityGuidParams.checked"
)
def test__every_guid_is_read_in_order_at_its_length() -> None:
    """Repeated ``guid`` parameters, each UUID text within a parameter's length (ERD-01, EDL-02, DV-161)."""
    a, b = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"
    assert read_params(EntityGuidParams, query(f"guid={b}&guid={a}")).checked() == [b, a]
    assert read_params(EntityGuidParams, query("")).checked() == []
    with pytest.raises(AtlasError) as raised:
        read_params(EntityGuidParams, query(f"guid={'g' * 4097}")).checked()
    assert raised.value.code is AtlasErrorCode.INVALID_QUERY_PARAM_LENGTH
    with pytest.raises(AtlasError) as raised:
        read_params(EntityGuidParams, query("guid=b")).checked()
    assert raised.value.code is AtlasErrorCode.INVALID_OBJECT_ID


@pytest.mark.covers("aurelius_atlas_model.params.FlagParam.read", "aurelius_atlas_model.params.read_params")
def test__a_flag_is_true_only_for_true_in_any_case() -> None:
    """``minExtInfo=YES`` is false, ``=True`` is true, absent is false (DV-39)."""
    assert read_params(EntityReadParams, query("minExtInfo=TRUE")).min_ext_info is True
    assert read_params(EntityReadParams, query("minExtInfo=yes")).min_ext_info is False
    assert read_params(EntityReadParams, query("")).ignore_relationships is False


@pytest.mark.covers("aurelius_atlas_model.params.EnumParam.read", "aurelius_atlas_model.params.read_params")
def test__the_audit_action_is_read_by_its_name() -> None:
    """``auditAction`` and the short ``count``/``offset`` of an audit read (AUD-06 to AUD-09)."""
    events = read_params(EntityAuditParams, query("auditAction=ENTITY_CREATE&count=3"))
    assert (events.audit_action and events.audit_action.value, events.count, events.offset) == ("ENTITY_CREATE", 3, -1)
    assert read_params(EntityAuditParams, query("")).count == 100
    with pytest.raises(AtlasError) as raised:
        read_params(EntityAuditParams, query("auditAction=CREATE"))
    assert raised.value.message == "Invalid value CREATE for query parameter auditAction"
    with pytest.raises(AtlasError):
        read_params(EntityAuditParams, query("count=32768"))


@pytest.mark.covers("aurelius_atlas_model.params.EntityHeadersParams.checked", rules=["DV-41"])
def test__a_start_after_now_is_refused() -> None:
    """``tagUpdateStartTime`` of ``getEntityHeaders``: a long, and not after now (CAU-07, DV-41)."""
    assert read_params(EntityHeadersParams, query("tagUpdateStartTime=5")).checked(10) == 5
    assert read_params(EntityHeadersParams, query("")).checked(10) == 0
    with pytest.raises(AtlasError) as raised:
        read_params(EntityHeadersParams, query("tagUpdateStartTime=11")).checked(10)
    assert raised.value.message == "fromTimestamp should be less than toTimestamp"
    with pytest.raises(AtlasError):
        read_params(EntityHeadersParams, query("tagUpdateStartTime=abc"))


@pytest.mark.covers("aurelius_atlas_model.params.AttrParam.read", "aurelius_atlas_model.params.AttrSetParam.read")
def test__the_unique_attribute_parameters_keep_first_values_and_order() -> None:
    """``attr:<name>`` first values; one ``attr_<n>:`` set per index, in the order indices appear (ERD-08, DV-19)."""
    found = read_params(UniqueAttributeParams, query("attr:qualifiedName=a&attr:name=b&attr:qualifiedName=c"))
    assert found.attributes == {"qualifiedName": "a", "name": "b"}
    sets = read_params(UniqueAttributeParams, query("attr_2:name=b&attr_1:name=a&attr_2:id=9&attr_1:id=8&attr_x=blank"))
    assert sets.attribute_sets == [{"name": "b", "id": "9"}, {"name": "a", "id": "8"}]


@pytest.mark.covers("aurelius_atlas_model.params.read_params")
def test__lineage_reads_direction_and_depth_with_defaults() -> None:
    """``direction`` BOTH and ``depth`` 3 when the request gives neither (LIN-01, DV-39)."""
    default = read_params(LineageParams, query(""))
    assert (default.direction.value, default.depth) == ("BOTH", 3)
    asked = read_params(LineageParams, query("direction=INPUT&depth=2"))
    assert (asked.direction.value, asked.depth) == ("INPUT", 2)
    with pytest.raises(AtlasError) as raised:
        read_params(LineageParams, query("direction=UP"))
    assert raised.value.message == "Invalid value UP for query parameter direction"


@pytest.mark.covers("aurelius_atlas_model.params.SavedSearchParams.checked", rules=["SVS-04"])
def test__a_saved_search_user_is_read_at_its_length() -> None:
    """``user`` of the saved-search reads (SVS-04)."""
    assert read_params(SavedSearchParams, query("user=ann")).checked() == "ann"
    assert read_params(SavedSearchParams, query("")).checked() is None
    with pytest.raises(AtlasError):
        read_params(SavedSearchParams, query(f"user={'u' * 4097}")).checked()


@pytest.mark.covers(
    "aurelius_atlas_model.params.BasicSearchParams.checked",
    "aurelius_atlas_model.params.ClassificationDeleteParams.checked",
)
def test__a_long_search_value_is_refused_before_the_search() -> None:
    """The names and the query of a basic search, at their lengths (FTX-01, TYR-04); CLS-09's GUID."""
    read_params(BasicSearchParams, query("typeName=t&limit=2&offset=3")).checked()
    with pytest.raises(AtlasError) as raised:
        read_params(BasicSearchParams, query(f"typeName={'t' * 4097}")).checked()
    assert raised.value.code is AtlasErrorCode.INVALID_QUERY_PARAM_LENGTH
    with pytest.raises(AtlasError) as raised:
        read_params(BasicSearchParams, query("query=" + "q" * 4097)).checked()
    assert raised.value.code is AtlasErrorCode.INVALID_QUERY_LENGTH
    assert read_params(ClassificationDeleteParams, query("")).checked() is None
    with pytest.raises(AtlasError):
        read_params(ClassificationDeleteParams, query(f"associatedEntityGuid={'g' * 4097}")).checked()


@pytest.mark.covers("aurelius_atlas_model.params.DslSearchParams.checked", rules=["DSE-01"])
def test__the_dsl_query_is_refused_at_its_own_limit() -> None:
    """The DSL limit is its own setting, not the full-text one (DSE-01)."""
    read_params(DslSearchParams, query("query=" + "x" * 4096)).checked()
    with pytest.raises(AtlasError) as raised:
        read_params(DslSearchParams, query("query=" + "x" * 4097)).checked()
    assert raised.value.code is AtlasErrorCode.INVALID_QUERY_LENGTH
    assert "dsl" in raised.value.message


@pytest.mark.covers("aurelius_atlas_model.params.AttributeSearchParams.checked", rules=["SRC-11"])
def test__an_attribute_search_needs_its_attribute_or_prefix() -> None:
    """The names at their length, then the two required parameters (SRC-11)."""
    read_params(AttributeSearchParams, query("attrName=name&attrValuePrefix=s")).checked()
    with pytest.raises(AtlasError) as raised:
        read_params(AttributeSearchParams, query("")).checked()
    assert raised.value.code is AtlasErrorCode.INVALID_PARAMETERS
    assert raised.value.message == "invalid parameters: attrName : null, attrValue: null for attribute search."
    with pytest.raises(AtlasError):
        read_params(AttributeSearchParams, query(f"attrName={'a' * 4097}")).checked()


@pytest.mark.covers("aurelius_atlas_model.params.QuickQueryParams.checked", rules=["QSR-02"])
def test__a_quick_query_is_read_at_the_fulltext_limit() -> None:
    """Only the length is checked by the GET variant (QSR-02)."""
    read_params(QuickQueryParams, query("query=table")).checked()
    with pytest.raises(AtlasError):
        read_params(QuickQueryParams, query("query=" + "q" * 4097)).checked()


@pytest.mark.covers("aurelius_atlas_model.params.MetricsTimeParams.checked", rules=["DV-136"])
def test__the_metrics_range_needs_two_times() -> None:
    """A missing or blank time, or one that is no long, fails with the core's texts (MHS-03, DV-136)."""
    start, end, names = read_params(MetricsTimeParams, query("startTime=1&endTime=2&typeName=A&typeName=B")).checked()
    assert (start, end, names) == (1, 2, ["A", "B"])
    for text in ("", "endTime=2", "startTime=&endTime=2"):
        with pytest.raises(AtlasError) as raised:
            read_params(MetricsTimeParams, query(text)).checked()
        assert raised.value.message == "startTime or endTime is null/empty."
    with pytest.raises(AtlasError) as raised:
        read_params(MetricsTimeParams, query("startTime=abc&endTime=2")).checked()
    assert raised.value.message == "Invalid value abc for query parameter startTime"


@pytest.mark.covers("aurelius_atlas_model.params.FlagParam.read", "aurelius_atlas_model.params.read_params")
def test__mininfo_defaults_to_the_whole_response() -> None:
    """``getAllMetrics`` answers the metrics themselves unless asked without (MHS-02); REP-05's filters."""
    assert read_params(MetricsListParams, query("")).min_info is True
    assert read_params(MetricsListParams, query("mininfo=false")).min_info is False
    history = read_params(ExportImportAuditParams, query("userName=ann&operation=EXPORT&limit=5"))
    assert (history.user_name, history.operation, history.limit, history.offset) == ("ann", "EXPORT", 5, 0)
