"""Atlas errors: the code, HTTP status and message of each failure (``AtlasErrorCode``, DD-023).

Every layer raises ``AtlasError``; the server answers it with Atlas's error body. Codes are copied from
``org.apache.atlas.AtlasErrorCode`` of Apache Atlas 2.4.0 as an increment first raises them.
"""

import math
import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

_PLACEHOLDER = re.compile(r"\{(\d+)\}")


class AtlasErrorCode(Enum):
    """The Atlas error codes raised so far, with their HTTP status and message template (TRG-15)."""

    UNKNOWN_TYPE = (400, "ATLAS-400-00-001", "Unknown type {0} for {1}.{2}")
    CIRCULAR_REFERENCE = (400, "ATLAS-400-00-002", "{0}: invalid supertypes - circular reference back to self {1}")
    INCOMPATIBLE_SUPERTYPE = (400, "ATLAS-400-00-003", "{0}: incompatible supertype {1}")
    CONSTRAINT_MISSING_PARAMS = (
        400,
        "ATLAS-400-00-007",
        "{0}.{1} : invalid constraint. missing parameter {2} in {3}. params={4}",
    )
    CANNOT_ADD_MANDATORY_ATTRIBUTE = (400, "ATLAS-400-00-00C", "{0}.{1} : can not add mandatory attribute")
    ATTRIBUTE_DELETION_NOT_SUPPORTED = (400, "ATLAS-400-00-00D", "{0}.{1} : attribute delete not supported")
    SUPERTYPE_REMOVAL_NOT_SUPPORTED = (400, "ATLAS-400-00-00E", "superType remove not supported")
    TYPE_MATCH_FAILED = (400, "ATLAS-400-00-010", "Given type {0} doesn't match {1}")
    INVALID_ATTRIBUTE_TYPE_FOR_CARDINALITY = (
        400,
        "ATLAS-400-00-012",
        "Cardinality of attribute {0}.{1} requires a list or set type",
    )
    ATTRIBUTE_UNIQUE_INVALID = (400, "ATLAS-400-00-013", "Type {0} with unique attribute {1} does not exist")
    TYPE_NAME_INVALID = (400, "ATLAS-400-00-014", "Type {0} with name {1} does not exist")
    TYPE_CATEGORY_INVALID = (400, "ATLAS-400-00-015", "Type Category {0} is invalid")
    PATCH_NOT_APPLICABLE_FOR_TYPE = (400, "ATLAS-400-00-016", "{0} - invalid patch for type {1}")
    PATCH_FOR_UNKNOWN_TYPE = (400, "ATLAS-400-00-017", "{0} - patch references unknown type {1}")
    PATCH_INVALID_DATA = (400, "ATLAS-400-00-018", "{0} - patch data is invalid for type {1}")
    TYPE_NAME_INVALID_FORMAT = (
        400,
        "ATLAS-400-00-019",
        (
            "{0}: invalid name for {1}.  Names must consist of a letter followed by a sequence of letter, number, "
            "space, or '_' characters"
        ),
    )
    INVALID_PARAMETERS = (400, "ATLAS-400-00-01A", "invalid parameters: {0}")
    CONSTRAINT_INVERSE_REF_ATTRIBUTE_INVALID_TYPE = (
        400,
        "ATLAS-400-00-01C",
        "{0}.{1}: invalid {2} constraint. Attribute {3} is not an entity type",
    )
    CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_NON_EXISTING = (
        400,
        "ATLAS-400-00-01D",
        "{0}.{1}: invalid {2} constraint. Inverse attribute {3}.{4} does not exist",
    )
    CONSTRAINT_INVERSE_REF_INVERSE_ATTRIBUTE_INVALID_TYPE = (
        400,
        "ATLAS-400-00-01E",
        "{0}.{1}: invalid {2} constraint. Inverse attribute {3}.{4} is not an entity type",
    )
    CONSTRAINT_OWNED_REF_ATTRIBUTE_INVALID_TYPE = (
        400,
        "ATLAS-400-00-01F",
        "{0}.{1}: invalid {2} constraint. Attribute {3} is not an entity type",
    )
    INVALID_OBJECT_ID = (400, "ATLAS-400-00-021", "ObjectId is not valid {0}")
    UNKNOWN_ATTRIBUTE = (400, "ATLAS-400-00-023", "Attribute {0} not found for type {1}")
    SYSTEM_TYPE = (400, "ATLAS-400-00-024", "{0} is a System-type")
    INVALID_STRUCT_VALUE = (400, "ATLAS-400-00-025", "not a valid struct value {0}")
    ATTRIBUTE_UPDATE_NOT_SUPPORTED = (400, "ATLAS-400-00-027", "{0}.{1} : attribute update not supported")
    INVALID_VALUE = (400, "ATLAS-400-00-028", "invalid value: {0}")
    BAD_REQUEST = (400, "ATLAS-400-00-029", "{0}")
    MISSING_MANDATORY_ATTRIBUTE = (400, "ATLAS-400-00-02B", "Mandatory field {0}.{1} has empty/null value")
    RELATIONSHIPDEF_DOUBLE_CONTAINERS = (
        400,
        "ATLAS-400-00-02D",
        "relationshipDef {0} creation attempted with both ends as containers",
    )
    RELATIONSHIPDEF_ASSOCIATION_AND_CONTAINER = (
        400,
        "ATLAS-400-00-030",
        "ASSOCIATION relationshipDef {0} creation attempted with an end specifying isContainer",
    )
    RELATIONSHIPDEF_COMPOSITION_NO_CONTAINER = (
        400,
        "ATLAS-400-00-031",
        "COMPOSITION relationshipDef {0} creation attempted without an end specifying isContainer",
    )
    RELATIONSHIPDEF_AGGREGATION_NO_CONTAINER = (
        400,
        "ATLAS-400-00-032",
        "AGGREGATION relationshipDef {0} creation attempted without an end specifying isContainer",
    )
    RELATIONSHIPDEF_COMPOSITION_MULTIPLE_PARENTS = (
        400,
        "ATLAS-400-00-033",
        "COMPOSITION relationshipDef {0} can only have one parent; so cannot have SET cardinality on children",
    )
    RELATIONSHIPDEF_LIST_ON_END = (
        400,
        "ATLAS-400-00-034",
        "relationshipDef {0} cannot have a LIST cardinality on an end",
    )
    RELATIONSHIPDEF_INVALID_END_TYPE = (400, "ATLAS-400-00-035", "relationshipDef {0} has invalid end type {1}")
    RELATIONSHIPDEF_INVALID = (400, "ATLAS-400-00-044", "Invalid relationshipDef: {0}")
    INVALID_RELATIONSHIP_END_TYPE = (
        400,
        "ATLAS-400-00-036",
        "invalid relationshipDef: {0}: end type 1: {1}, end type 2: {2}",
    )
    RELATIONSHIPDEF_INVALID_END1_UPDATE = (
        400,
        "ATLAS-400-00-037",
        "invalid update for relationshipDef {0}: new end1 {1}, existing end1 {2}",
    )
    RELATIONSHIPDEF_INVALID_END2_UPDATE = (
        400,
        "ATLAS-400-00-038",
        "invalid update for relationshipDef {0}: new end2 {1}, existing end2 {2}",
    )
    RELATIONSHIPDEF_INVALID_CATEGORY_UPDATE = (
        400,
        "ATLAS-400-00-039",
        "invalid  update for relationship {0}: new relationshipDef category {1}, existing relationshipDef category {2}",
    )
    RELATIONSHIPDEF_INVALID_NAME_UPDATE = (
        400,
        "ATLAS-400-00-040",
        "invalid relationshipDef rename for relationship guid {0}: new name {1}, existing name {2}",
    )
    ENTITYTYPE_REMOVAL_NOT_SUPPORTED = (
        400,
        "ATLAS-400-00-051",
        "EntityTypes cannot be removed from ClassificationDef \u2018{0}\u2018",
    )
    CLASSIFICATIONDEF_INVALID_ENTITYTYPES = (
        400,
        "ATLAS-400-00-052",
        "ClassificationDef \u2018{0}\u2018 has invalid \u2018{1}\u2018 in entityTypes",
    )
    CLASSIFICATIONDEF_PARENTS_ENTITYTYPES_DISJOINT = (
        400,
        "ATLAS-400-00-053",
        (
            "ClassificationDef \u2018{0}\u2018 has supertypes whose entityTypes are disjoint; e.g. 2 supertypes that "
            "are not related by inheritance specify different non empty entityType lists. This means the child cannot "
            "honour the restrictions specified in both parents."
        ),
    )
    CLASSIFICATIONDEF_ENTITYTYPES_NOT_PARENTS_SUBSET = (
        400,
        "ATLAS-400-00-054",
        (
            "ClassificationDef \u2018{0}\u2018 has entityTypes \u2018{1}\u2018 which are not subsets of it's "
            "supertypes entityTypes"
        ),
    )
    INVALID_QUERY_PARAM_LENGTH = (400, "ATLAS-400-00-057", "Length of query param {0} exceeds the limit")
    INVALID_ENTITY_FOR_CLASSIFICATION = (
        400,
        "ATLAS-400-00-055",
        (
            "Entity (guid=\u2018{0}\u2018,typename=\u2018{1}\u2018) cannot be classified by Classification "
            "\u2018{2}\u2018, because \u2018{1}\u2018 is not in the ClassificationDef's restrictions."
        ),
    )
    ATTRIBUTE_TYPE_INVALID = (
        400,
        "ATLAS-400-00-081",
        "{0}.{1}: invalid attribute type. Attribute cannot be of type classification",
    )
    INVALID_TIMEBOUNDRY_TIMEZONE = (400, "ATLAS-400-00-085", "Invalid timezone {0}")
    INVALID_TIMEBOUNDRY_START_TIME = (400, "ATLAS-400-00-086", "Invalid startTime {0}")
    INVALID_TIMEBOUNDRY_END_TIME = (400, "ATLAS-400-00-087", "Invalid endTime {0}")
    INVALID_TIMEBOUNDRY_DATERANGE = (
        400,
        "ATLAS-400-00-088",
        "Invalid dateRange: startTime {0} must be before endTime {1}",
    )
    RELATIONSHIP_UPDATE_END_CHANGE_NOT_ALLOWED = (
        404,
        "ATLAS-400-00-069",
        (
            "change of relationship end is not permitted. relationship-type={0}, relationship-guid={1}, "
            "end-guid={2}, updated-end-guid={3}"
        ),
    )
    RELATIONSHIP_UPDATE_TYPE_CHANGE_NOT_ALLOWED = (
        404,
        "ATLAS-400-00-06A",
        "change of relationship type is not permitted. relationship-guid={0}, current-type={1}, new-type={2}",
    )
    RELATIONSHIP_END_IS_NULL = (400, "ATLAS-400-00-07D", "Relationship end is invalid. Expected {0} but is NULL")
    CLASSIFICATION_UPDATE_FROM_PROPAGATED_ENTITY = (
        400,
        "ATLAS-400-00-06B",
        "Update to classification {0} is not allowed from propagated entity",
    )
    CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY = (
        400,
        "ATLAS-400-00-06D",
        "Classification {0} is not associated with entity",
    )
    PROPAGATED_CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY = (
        400,
        "ATLAS-400-00-070",
        "Propagated classification {0} is not associated with entity {2}, it is associated with entity {1}",
    )
    INVALID_CLASSIFICATION_PARAMS = (
        400,
        "ATLAS-400-00-06F",
        "Invalid classification parameters passed for {0} operation for entity: {1}",
    )
    PATCH_MISSING_RELATIONSHIP_LABEL = (
        400,
        "ATLAS-400-00-08B",
        "{0} - must include relationship label for type {1}",
    )
    INVALID_CUSTOM_ATTRIBUTE_KEY_LENGTH = (
        400,
        "ATLAS-400-00-08C",
        "Invalid key: {0} in custom attribute, key size should not be greater than 50",
    )
    INVALID_CUSTOM_ATTRIBUTE_KEY_CHARACTERS = (
        400,
        "ATLAS-400-00-08D",
        "Invalid key: {0} in custom attribute, key should only contain alphanumeric characters, '_' or '-'",
    )
    INVALID_LABEL_LENGTH = (400, "ATLAS-400-00-08F", "Invalid label: {0}, label size should not be greater than {1}")
    INVALID_LABEL_CHARACTERS = (
        400,
        "ATLAS-400-00-090",
        "Invalid label: {0}, label should contain alphanumeric characters, '_' or '-'",
    )
    INVALID_PROPAGATION_TYPE = (
        400,
        "ATLAS-400-00-091",
        "Invalid propagation {0} for relationship-type={1}. Default value is {2}",
    )
    APPLICABLE_ENTITY_TYPES_DELETION_NOT_SUPPORTED = (
        400,
        "ATLAS-400-00-093",
        "Cannot remove applicableEntityTypes in Attribute Def: {0}, defined in business-metadata: {1}",
    )
    BUSINESS_METADATA_DEF_ATTRIBUTE_TYPE_INVALID = (
        400,
        "ATLAS-400-00-094",
        (
            "{0}.{1}: invalid attribute type. Business-metadata attribute cannot be of type "
            "entity/classification/struct/business-metadata"
        ),
    )
    ATTRIBUTE_NAME_ALREADY_EXISTS_IN_ANOTHER_PARENT_TYPE = (
        400,
        "ATLAS-400-00-09E",
        "Invalid attribute name: {0}.{1}. Attribute already exists in another parent type: {2}",
    )
    ATTRIBUTE_NAME_INVALID_CHARS = (
        400,
        "ATLAS-400-00-09A",
        (
            "{0}: invalid name. Attribute names must begin with a letter followed by a sequence of letters, numbers, "
            "or '_' characters"
        ),
    )
    TYPE_NAME_NOT_FOUND = (404, "ATLAS-404-00-001", "Given typename {0} was invalid")
    TYPE_GUID_NOT_FOUND = (404, "ATLAS-404-00-002", "Given type guid {0} was invalid")
    NO_CLASSIFICATIONS_FOUND_FOR_ENTITY = (404, "ATLAS-404-00-003", "No classifications associated with entity: {0}")
    INSTANCE_GUID_NOT_FOUND = (404, "ATLAS-404-00-005", "Given instance guid {0} is invalid/not found")
    CLASSIFICATION_NOT_FOUND = (404, "ATLAS-404-00-008", "Given classification {0} was invalid")
    INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND = (
        404,
        "ATLAS-404-00-009",
        "Instance {0} with unique attribute {1} does not exist",
    )
    INSTANCE_CRUD_INVALID_PARAMS = (
        404,
        "ATLAS-404-00-007",
        "Invalid instance creation/updation parameters passed : {0}",
    )
    REFERENCED_ENTITY_NOT_FOUND = (404, "ATLAS-404-00-00A", "Referenced entity {0} is not found")
    RELATIONSHIP_GUID_NOT_FOUND = (404, "ATLAS-404-00-00C", "Given relationship guid {0} is invalid/not found")
    RELATIONSHIP_CRUD_INVALID_PARAMS = (
        404,
        "ATLAS-404-00-00D",
        "Invalid relationship creation/updation parameters passed : {0}",
    )
    RELATIONSHIP_ALREADY_DELETED = (
        404,
        "ATLAS-404-00-00F",
        "Attempting to delete a relationship which is already deleted : {0}",
    )
    TYPE_ALREADY_EXISTS = (409, "ATLAS-409-00-001", "Given type {0} already exists")
    TYPE_HAS_REFERENCES = (409, "ATLAS-409-00-002", "Given type {0} has references")
    RELATIONSHIP_ALREADY_EXISTS = (
        409,
        "ATLAS-409-00-004",
        "relationship {0} already exists between entities {1} and {2}",
    )
    TYPE_HAS_RELATIONSHIPS = (409, "ATLAS-409-00-005", "Given type {0} has associated relationshipDefs")
    INTERNAL_ERROR = (500, "ATLAS-500-00-001", "Internal server error {0}")
    FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK = (
        500,
        "ATLAS-500-00-005",
        "Failed to get the lock; another type update might be in progress. Please try again",
    )

    def __init__(self, http_status: int, code: str, template: str) -> None:
        self.http_status = http_status
        self.code = code
        self.template = template

    def message(self, *params: object) -> str:
        """Fill the template's ``{0}``, ``{1}``, ... with the parameters, as Java's ``MessageFormat`` does (THY-13).

        An apostrophe starts or ends quoted text, which is copied without the apostrophe; two apostrophes are
        one. Parameters are written as Java's ``String.valueOf`` writes them (TRG-15).
        """
        return message_format(self.template, *params)


def java_double_string(value: float) -> str:
    """``Double.toString``: plain from 10^-3 to 10^7, else ``d.dddE<n>``; ``NaN`` and ``Infinity`` (VAL-09).

    The digits are Python's shortest ones, which are Java's for all but a few subnormal values.
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "-0.0" if math.copysign(1.0, value) < 0 else "0.0"
    if _PLAIN_DOUBLE_MIN <= abs(value) < _PLAIN_DOUBLE_MAX:
        text = repr(value)
        return text if "." in text else f"{text}.0"
    _, digits, exponent = Decimal(repr(abs(value))).normalize().as_tuple()
    text = "".join(map(str, digits))
    power = len(text) - 1 + int(exponent)
    sign = "-" if value < 0 else ""
    return f"{sign}{text[0]}.{text[1:] or '0'}E{power}"


_PLAIN_DOUBLE_MIN = 1e-3
_PLAIN_DOUBLE_MAX = 1e7


def java_date_string(value: datetime) -> str:
    """``Date.toString`` in UTC: ``Thu Jan 01 00:00:00 UTC 1970`` (VAL-09)."""
    return value.astimezone(UTC).strftime("%a %b %d %H:%M:%S UTC %Y")


def java_string(value: object) -> str:
    """``String.valueOf``: ``null``, ``true``, ``[a, b]`` for collections and ``{k=v}`` for maps (THY-13).

    A double is written as ``Double.toString``, a decimal as ``BigDecimal.toString`` and a date as
    ``Date.toString`` (VAL-09); a model with a ``java_string`` method as that method writes it (EWR-05).
    """
    scalar = _java_scalar(value)
    if scalar is not None:
        return scalar
    own = getattr(value, "java_string", None)
    if callable(own):
        return str(own())
    if isinstance(value, Mapping):
        return "{" + ", ".join(f"{java_string(key)}={java_string(item)}" for key, item in value.items()) + "}"
    if isinstance(value, Iterable):
        return "[" + ", ".join(java_string(item) for item in value) + "]"
    return str(value)


def _java_scalar(value: object) -> str | None:
    """Java's text of a null, boolean, string, double or date; None for anything else."""
    match value:
        case None:
            return "null"
        case bool():
            return "true" if value else "false"
        case str():
            return value
        case float():
            return java_double_string(value)
        case datetime():
            return java_date_string(value)
        case _:
            return None


def message_format(template: str, *params: object) -> str:
    """Java's ``MessageFormat.format`` for templates with plain ``{n}`` placeholders (THY-13)."""
    out: list[str] = []
    quoted = False
    i = 0
    while i < len(template):
        char = template[i]
        if char == "'":
            if template.startswith("''", i):
                out.append("'")
                i += 2
                continue
            quoted = not quoted
            i += 1
            continue
        if not quoted and (placeholder := _PLACEHOLDER.match(template, i)) is not None:
            index = int(placeholder[1])
            out.append(java_string(params[index]) if index < len(params) else placeholder[0])
            i = placeholder.end()
            continue
        out.append(char)
        i += 1
    return "".join(out)


class AtlasError(Exception):
    """An error the Atlas API answers with its own status and body (``AtlasBaseException``)."""

    def __init__(self, code: AtlasErrorCode, *params: object, cause: BaseException | None = None) -> None:
        self.code = code
        self.params = params
        self.message = code.message(*params)
        self.cause = cause
        super().__init__(self.message)

    @classmethod
    def of_message(cls, code: AtlasErrorCode, message: str) -> AtlasError:
        """``AtlasBaseException(String)``: an error whose message is the text itself, not the code's template."""
        error = cls(code)
        error.message = message
        error.args = (message,)
        return error
