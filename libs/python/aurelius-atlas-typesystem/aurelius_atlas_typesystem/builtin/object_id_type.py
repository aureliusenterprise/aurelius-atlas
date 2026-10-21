"""``AtlasBuiltInTypes.AtlasObjectIdType`` (VAL-10)."""

from collections.abc import Mapping

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelatedObjectId
from aurelius_atlas_model.typedef import ATLAS_TYPE_ASSET, ATLAS_TYPE_OBJECT_ID, SERVICE_TYPE_ATLAS_CORE, TypeCategory

from aurelius_atlas_typesystem.atlas_type import AtlasType

DEFAULT_UNASSIGNED_GUID = "-1"


class ObjectIdType(AtlasType):
    """``objectid``: a reference to an entity of ``object_type``, by GUID or by unique attributes."""

    def __init__(self, object_type: str | None = ATLAS_TYPE_ASSET) -> None:
        super().__init__(ATLAS_TYPE_OBJECT_ID, TypeCategory.OBJECT_ID_TYPE, SERVICE_TYPE_ATLAS_CORE)
        self.object_type = object_type

    def create_default_value(self) -> AtlasObjectId:
        """An object id with the unassigned GUID ``-1`` and the object type."""
        return AtlasObjectId(guid=DEFAULT_UNASSIGNED_GUID, type_name=self.object_type)

    def is_valid_value(self, value: object) -> bool:
        """Null, an object id, or a map that identifies an entity."""
        if value is None or isinstance(value, AtlasObjectId):
            return True
        return isinstance(value, Mapping) and _identifies_entity(value)

    def get_normalized_value(self, value: object) -> AtlasObjectId | None:
        """An object id as it is; a map that identifies an entity, read by Java's map constructor; else None.

        A map with a ``relationshipType`` key becomes a related object id.
        """
        if isinstance(value, AtlasObjectId):
            return value
        if not isinstance(value, Mapping) or not _identifies_entity(value):
            return None
        found = AtlasRelatedObjectId(guid=None) if "relationshipType" in value else AtlasObjectId(guid=None)
        found.read_map(value)
        return found

    def are_equal_values(self, left: object, right: object, guid_assignments: dict[str, str] | None) -> bool:
        """Equal by GUID, mapped through the assignments, when both or neither is assigned (VAL-10).

        When only one GUID is assigned, the type names and unique attributes decide.
        """
        if left is None or right is None:
            return left is None and right is None
        normalized_left, normalized_right = self.get_normalized_value(left), self.get_normalized_value(right)
        if normalized_left is None or normalized_right is None:
            return False
        guid_left = _assigned(normalized_left.guid, guid_assignments)
        guid_right = _assigned(normalized_right.guid, guid_assignments)
        if is_assigned_guid(guid_left) == is_assigned_guid(guid_right):
            return guid_left == guid_right
        return (
            normalized_left.type_name == normalized_right.type_name
            and normalized_left.unique_attributes == normalized_right.unique_attributes
        )


def is_assigned_guid(guid: str | None) -> bool:
    """``AtlasTypeUtil.isAssignedGuid``: non-empty and not starting with ``-``, which marks an unassigned GUID."""
    return bool(guid) and not str(guid).startswith("-")


def _assigned(guid: str | None, guid_assignments: dict[str, str] | None) -> str | None:
    if guid_assignments is not None and guid in guid_assignments:
        return guid_assignments[guid]
    return guid


def _identifies_entity(values: Mapping[object, object]) -> bool:
    """``isValidMap``: a non-empty ``guid``, or a non-empty ``typeName`` with a non-empty ``uniqueAttributes`` map."""
    guid = values.get("guid")
    if guid is not None and java_string(guid):
        return True
    type_name, unique = values.get("typeName"), values.get("uniqueAttributes")
    return type_name is not None and bool(java_string(type_name)) and isinstance(unique, Mapping) and bool(unique)
