"""The JSON maps the REST endpoints take where Java declares no class for the body.

Each is read from the request as it arrives and checked by the endpoint's own rules (DV-10); the models
give the OpenAPI document a name and an item shape instead of an anonymous object.
"""

from typing import Any

from pydantic import RootModel, field_validator

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

NO_ATTRIBUTES_BODY = "Invalid body: a JSON object of attribute values is expected"
"""A body that is no JSON object where attribute values are expected (BMD-01, DV-10)."""

NO_BUSINESS_BODY = "Invalid body: a JSON object of attribute values by business metadata is expected"
"""A body that is no JSON object of value maps by business metadata (BMD-01, DV-10)."""


class JsonValue(RootModel[Any]):
    """Any JSON value.

    ``partialUpdateEntityAttrByGuid`` takes the attribute's new value as one (EWR-15), the body Java
    reads as a plain ``Object``.
    """


class AttributeValues(RootModel[dict[str, Any]]):
    """A JSON object of values by attribute name (BMD-01).

    Java's ``Map<String, Object>``, as the glossary ``/partial`` updates take the attributes to set
    (GTM-04, GCT-04, GLS-04) and one business metadata takes its values (BMD-03). A body that is no
    JSON object is refused, as the endpoints refused it.
    """

    @field_validator("root", mode="before")
    @classmethod
    def _json_object(cls, value: object) -> object:
        if not isinstance(value, dict):
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_ATTRIBUTES_BODY)
        return value


class BusinessAttributesMap(RootModel[dict[str, dict[str, Any] | None]]):
    """Attribute values by business metadata name (BMD-01, BMD-05).

    Java's nested map, where a name alone carries null and removes that metadata's attributes. A body
    that is no JSON object of such a map is refused, as the endpoints refused it.
    """

    @field_validator("root", mode="before")
    @classmethod
    def _json_object_of_value_maps(cls, value: object) -> object:
        if not isinstance(value, dict) or not all(item is None or isinstance(item, dict) for item in value.values()):
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_BUSINESS_BODY)
        return value
