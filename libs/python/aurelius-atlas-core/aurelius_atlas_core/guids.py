"""``AssignedGuid``: a GUID that names an entity the store has or mints, never a request placeholder (DV-162).

A request names entities two ways: a placeholder GUID (text starting with ``-``, ``AtlasTypeUtil.isAssignedGuid``
calls it unassigned) for one of the same request, and a stored GUID for one already there. Discovery maps the
first onto the second, and every GUID it records passes through ``as_assigned_guid``. Past that point the type
says no placeholder is in the value, so a mapper or a stored document cannot be handed a ``-1`` by accident.
"""

from typing import NewType

from aurelius_atlas_typesystem.builtin.object_id_type import is_assigned_guid

AssignedGuid = NewType("AssignedGuid", str)
"""A GUID of a stored or minted entity: assigned text, with the request's placeholders excluded by the type."""


def as_assigned_guid(guid: str) -> AssignedGuid:
    """``guid`` as an ``AssignedGuid``, checking it names an entity rather than a placeholder (DV-162).

    Raises:
        AssertionError: ``guid`` is empty or a placeholder: a caller passed a request GUID past discovery,
            a bug rather than a client error.
    """
    if not is_assigned_guid(guid):
        raise AssertionError  # pragma: no cover - a caller bug
    return AssignedGuid(guid)
