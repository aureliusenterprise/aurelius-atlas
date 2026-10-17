"""Atlas error codes and messages (TRG-15), copied from ``AtlasErrorCode`` of Apache Atlas 2.4.0."""

import pytest
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string, message_format


@pytest.mark.covers("aurelius_atlas_model.errors.AtlasErrorCode.message", rules=["TRG-15"])
def test__an_error_code_fills_its_template_in_order() -> None:
    """``MessageFormat`` puts the parameters at ``{0}``, ``{1}``, ...; Java prints a null as ``null``."""
    assert AtlasErrorCode.INTERNAL_ERROR.message("boom") == "Internal server error boom"
    assert (
        AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_NON_EXISTING.message("t", "a", "inverseRef", "u", "b")
        == "t.a: invalid inverseRef constraint. Inverse attribute u.b does not exist"
    )
    assert AtlasErrorCode.TYPE_NAME_NOT_FOUND.message(None) == "Given typename null was invalid"


@pytest.mark.covers(rules=["TRG-15"])
@pytest.mark.parametrize(
    ("code", "status", "atlas_code"),
    [
        (AtlasErrorCode.CIRCULAR_REFERENCE, 400, "ATLAS-400-00-002"),
        (AtlasErrorCode.INCOMPATIBLE_SUPERTYPE, 400, "ATLAS-400-00-003"),
        (AtlasErrorCode.CONSTRAINT_MISSING_PARAMS, 400, "ATLAS-400-00-007"),
        (AtlasErrorCode.INVALID_ATTRIBUTE_TYPE_FOR_CARDINALITY, 400, "ATLAS-400-00-012"),
        (AtlasErrorCode.CONSTRAINT_INVERSE_REF_ATTRIBUTE_INVALID_TYPE, 400, "ATLAS-400-00-01C"),
        (AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_NON_EXISTING, 400, "ATLAS-400-00-01D"),
        (AtlasErrorCode.CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_INVALID_TYPE, 400, "ATLAS-400-00-01E"),
        (AtlasErrorCode.CONSTRAINT_OWNED_REF_ATTRIBUTE_INVALID_TYPE, 400, "ATLAS-400-00-01F"),
        (AtlasErrorCode.INVALID_VALUE, 400, "ATLAS-400-00-028"),
        (AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE, 400, "ATLAS-400-00-02B"),
        (AtlasErrorCode.RELATIONSHIPDEF_DOUBLE_CONTAINERS, 400, "ATLAS-400-00-02D"),
        (AtlasErrorCode.RELATIONSHIPDEF_ASSOCIATION_AND_CONTAINER, 400, "ATLAS-400-00-030"),
        (AtlasErrorCode.RELATIONSHIPDEF_COMPOSITION_NO_CONTAINER, 400, "ATLAS-400-00-031"),
        (AtlasErrorCode.RELATIONSHIPDEF_AGGREGATION_NO_CONTAINER, 400, "ATLAS-400-00-032"),
        (AtlasErrorCode.RELATIONSHIPDEF_COMPOSITION_MULTIPLE_PARENTS, 400, "ATLAS-400-00-033"),
        (AtlasErrorCode.RELATIONSHIPDEF_LIST_ON_END, 400, "ATLAS-400-00-034"),
        (AtlasErrorCode.RELATIONSHIPDEF_INVALID_END_TYPE, 400, "ATLAS-400-00-035"),
        (AtlasErrorCode.CLASSIFICATIONDEF_PARENTS_ENTITYTYPES_DISJOINT, 400, "ATLAS-400-00-053"),
        (AtlasErrorCode.CLASSIFICATIONDEF_ENTITYTYPES_NOT_PARENTS_SUBSET, 400, "ATLAS-400-00-054"),
        (AtlasErrorCode.ATTRIBUTE_TYPE_INVALID, 400, "ATLAS-400-00-081"),
        (AtlasErrorCode.BUSINESS_METADATA_DEF_ATTRIBUTE_TYPE_INVALID, 400, "ATLAS-400-00-094"),
        (AtlasErrorCode.ATTRIBUTE_NAME_ALREADY_EXISTS_IN_ANOTHER_PARENT_TYPE, 400, "ATLAS-400-00-09E"),
        (AtlasErrorCode.TYPE_NAME_NOT_FOUND, 404, "ATLAS-404-00-001"),
        (AtlasErrorCode.TYPE_GUID_NOT_FOUND, 404, "ATLAS-404-00-002"),
        (AtlasErrorCode.INTERNAL_ERROR, 500, "ATLAS-500-00-001"),
        (AtlasErrorCode.FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK, 500, "ATLAS-500-00-005"),
    ],
)
def test__each_code_has_atlas_status_and_code(code: AtlasErrorCode, status: int, atlas_code: str) -> None:
    """The status and code of every member match ``AtlasErrorCode.java``."""
    assert (code.http_status, code.code) == (status, atlas_code)


@pytest.mark.covers(rules=["TRG-15"])
def test__an_error_keeps_its_code_parameters_message_and_cause() -> None:
    """``AtlasBaseException(errorCode, cause, params...)``."""
    cause = ValueError("disk full")
    error = AtlasError(AtlasErrorCode.TYPE_GUID_NOT_FOUND, "g-1", cause=cause)

    assert error.code is AtlasErrorCode.TYPE_GUID_NOT_FOUND
    assert error.params == ("g-1",)
    assert error.message == str(error) == "Given type guid g-1 was invalid"
    assert error.cause is cause


@pytest.mark.covers("aurelius_atlas_model.errors.message_format", rules=["THY-13"])
@pytest.mark.parametrize(
    ("template", "params", "expected"),
    [
        ("{0} and {1}", ("a", "b"), "a and b"),
        ("it's {0}", ("x",), "its {0}"),
        ("it''s {0}", ("x",), "it's x"),
        ("'{0}' is {0}", ("x",), "{0} is x"),
        ("open 'quote {0}", ("x",), "open quote {0}"),
        ("{0} {1}", ("only",), "only {1}"),
    ],
    ids=["plain", "apostrophe-quotes", "double-apostrophe", "quoted-placeholder", "unclosed-quote", "missing-param"],
)
def test__messages_follow_message_format(template: str, params: tuple[object, ...], expected: str) -> None:
    """``MessageFormat``: apostrophes quote, ``''`` is one apostrophe, a missing argument stays ``{n}``."""
    assert message_format(template, *params) == expected


@pytest.mark.covers(rules=["THY-13"])
def test__atlas_apostrophe_is_dropped_as_java_drops_it() -> None:
    """``CLASSIFICATIONDEF_ENTITYTYPES_NOT_PARENTS_SUBSET`` says "it's"; Java's message says "its"."""
    message = AtlasErrorCode.CLASSIFICATIONDEF_ENTITYTYPES_NOT_PARENTS_SUBSET.message("PII", ["a", "b"])

    assert (
        message == "ClassificationDef \u2018PII\u2018 has entityTypes \u2018[a, b]\u2018 which are not subsets of its "
        "supertypes entityTypes"
    )


@pytest.mark.covers("aurelius_atlas_model.errors.java_string", rules=["THY-13"])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "null"),
        (True, "true"),
        (False, "false"),
        ("s", "s"),
        (7, "7"),
        (["a", "b"], "[a, b]"),
        ({"k": None}, "{k=null}"),
    ],
)
def test__parameters_are_written_as_java_writes_them(value: object, expected: str) -> None:
    """``String.valueOf`` of null, booleans, strings, numbers, collections and maps."""
    assert java_string(value) == expected
