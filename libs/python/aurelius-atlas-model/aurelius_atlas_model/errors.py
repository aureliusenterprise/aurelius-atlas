"""Atlas errors: the code, HTTP status and message of each failure (``AtlasErrorCode``, DD-023).

Every layer raises ``AtlasError``; the server answers it with Atlas's error body. Codes are copied from
``org.apache.atlas.AtlasErrorCode`` of Apache Atlas 2.4.0 as an increment first raises them.
"""

from enum import Enum


class AtlasErrorCode(Enum):
    """The Atlas error codes raised so far, with their HTTP status and message template (TRG-15)."""

    CONSTRAINT_MISSING_PARAMS = (
        400,
        "ATLAS-400-00-007",
        "{0}.{1} : invalid constraint. missing parameter {2} in {3}. params={4}",
    )
    INVALID_ATTRIBUTE_TYPE_FOR_CARDINALITY = (
        400,
        "ATLAS-400-00-012",
        "Cardinality of attribute {0}.{1} requires a list or set type",
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
    ATTRIBUTE_TYPE_INVALID = (
        400,
        "ATLAS-400-00-081",
        "{0}.{1}: invalid attribute type. Attribute cannot be of type classification",
    )
    TYPE_NAME_NOT_FOUND = (404, "ATLAS-404-00-001", "Given typename {0} was invalid")
    TYPE_GUID_NOT_FOUND = (404, "ATLAS-404-00-002", "Given type guid {0} was invalid")
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
        """Fill the template's ``{0}``, ``{1}``, ... with the parameters, as Java's ``MessageFormat`` does.

        Java formats a null parameter as ``null``.
        """
        return self.template.format(*("null" if param is None else param for param in params))


class AtlasError(Exception):
    """An error the Atlas API answers with its own status and body (``AtlasBaseException``)."""

    def __init__(self, code: AtlasErrorCode, *params: object, cause: BaseException | None = None) -> None:
        self.code = code
        self.params = params
        self.message = code.message(*params)
        self.cause = cause
        super().__init__(self.message)
