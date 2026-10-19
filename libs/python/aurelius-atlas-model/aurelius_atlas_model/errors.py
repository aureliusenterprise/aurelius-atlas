"""Atlas errors: the code, HTTP status and message of each failure (``AtlasErrorCode``, DD-023).

Every layer raises ``AtlasError``; the server answers it with Atlas's error body. Codes are copied from
``org.apache.atlas.AtlasErrorCode`` of Apache Atlas 2.4.0 as an increment first raises them.
"""

import re
from collections.abc import Iterable, Mapping
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
    TYPE_NAME_INVALID = (400, "ATLAS-400-00-014", "Type {0} with name {1} does not exist")
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
    SYSTEM_TYPE = (400, "ATLAS-400-00-024", "{0} is a System-type")
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
    ATTRIBUTE_TYPE_INVALID = (
        400,
        "ATLAS-400-00-081",
        "{0}.{1}: invalid attribute type. Attribute cannot be of type classification",
    )
    PATCH_MISSING_RELATIONSHIP_LABEL = (
        400,
        "ATLAS-400-00-08B",
        "{0} - must include relationship label for type {1}",
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
    TYPE_ALREADY_EXISTS = (409, "ATLAS-409-00-001", "Given type {0} already exists")
    TYPE_HAS_REFERENCES = (409, "ATLAS-409-00-002", "Given type {0} has references")
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


def java_string(value: object) -> str:
    """``String.valueOf``: ``null``, ``true``, ``[a, b]`` for collections and ``{k=v}`` for maps (THY-13)."""
    match value:
        case None:
            return "null"
        case bool():
            return "true" if value else "false"
        case str():
            return value
        case Mapping():
            return "{" + ", ".join(f"{java_string(key)}={java_string(item)}" for key, item in value.items()) + "}"
        case Iterable():
            return "[" + ", ".join(java_string(item) for item in value) + "]"
        case _:
            return str(value)


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
