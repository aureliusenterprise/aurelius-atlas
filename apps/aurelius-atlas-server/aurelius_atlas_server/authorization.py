"""Authorization: Atlas's privileges, granted by four roles of the server's client (AUZ-01 to AUZ-03, DD-253).

What a user may do is decided in one place (ADR 038): the identity provider holds who has which role, and this
module what each role grants. A check refused is Atlas's ``UNAUTHORIZED_ACCESS``.
"""

from collections.abc import Iterable
from enum import StrEnum

from fastapi import Request

from aurelius_atlas_server.authentication import User
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode


class AtlasPrivilege(StrEnum):
    """``AtlasPrivilege``: what a request may need, by Atlas's names."""

    TYPE_CREATE = "type-create"
    TYPE_UPDATE = "type-update"
    TYPE_DELETE = "type-delete"
    TYPE_READ = "type-read"
    ENTITY_READ = "entity-read"
    ENTITY_CREATE = "entity-create"
    ENTITY_UPDATE = "entity-update"
    ENTITY_DELETE = "entity-delete"
    ENTITY_READ_CLASSIFICATION = "entity-read-classification"
    ENTITY_ADD_CLASSIFICATION = "entity-add-classification"
    ENTITY_UPDATE_CLASSIFICATION = "entity-update-classification"
    ENTITY_REMOVE_CLASSIFICATION = "entity-remove-classification"
    ENTITY_ADD_LABEL = "entity-add-label"
    ENTITY_REMOVE_LABEL = "entity-remove-label"
    ENTITY_UPDATE_BUSINESS_METADATA = "entity-update-business-metadata"
    RELATIONSHIP_ADD = "add-relationship"
    RELATIONSHIP_UPDATE = "update-relationship"
    RELATIONSHIP_REMOVE = "remove-relationship"
    ADMIN_EXPORT = "admin-export"
    ADMIN_IMPORT = "admin-import"
    ADMIN_PURGE = "admin-purge"
    ADMIN_AUDITS = "admin-audits"
    SERVICE_NOTIFICATION_POST = "service-notification-post"


P = AtlasPrivilege
ROLE_PRIVILEGES: dict[str, frozenset[AtlasPrivilege]] = {
    "atlas-read": frozenset({P.TYPE_READ, P.ENTITY_READ, P.ENTITY_READ_CLASSIFICATION}),
    "atlas-write": frozenset(
        {
            P.ENTITY_CREATE,
            P.ENTITY_UPDATE,
            P.ENTITY_DELETE,
            P.ENTITY_ADD_CLASSIFICATION,
            P.ENTITY_UPDATE_CLASSIFICATION,
            P.ENTITY_REMOVE_CLASSIFICATION,
            P.ENTITY_ADD_LABEL,
            P.ENTITY_REMOVE_LABEL,
            P.ENTITY_UPDATE_BUSINESS_METADATA,
            P.RELATIONSHIP_ADD,
            P.RELATIONSHIP_UPDATE,
            P.RELATIONSHIP_REMOVE,
        }
    ),
    "atlas-types": frozenset({P.TYPE_CREATE, P.TYPE_UPDATE, P.TYPE_DELETE, P.TYPE_READ}),
    "atlas-admin": frozenset({P.ADMIN_EXPORT, P.ADMIN_IMPORT, P.ADMIN_PURGE, P.ADMIN_AUDITS}),
}
"""What each role of the server's client grants (AUZ-02, DD-253); ``atlas-types`` reads the types it may change,
as Atlas's simple authorizer adds ``TYPE_READ``."""


def privileges(user: User | None) -> frozenset[AtlasPrivilege]:
    """Every privilege the user's roles grant; none without a user (AUZ-01, AUZ-02)."""
    if user is None:
        return frozenset()
    return frozenset(privilege for role in user.roles for privilege in ROLE_PRIVILEGES.get(role, ()))


def is_access_allowed(request: Request, privilege: AtlasPrivilege) -> bool:
    """``isAccessAllowed``: whether the request's user holds the privilege (AUZ-02)."""
    return privilege in privileges(getattr(request.state, "user", None))


def verify_access(request: Request, privilege: AtlasPrivilege, *action: object) -> None:
    """``verifyAccess``: refuse the request without the privilege, naming the action (AUZ-03).

    Raises:
        AtlasError: ``UNAUTHORIZED_ACCESS``, ``<user> is not authorized to perform <action>``.
    """
    if not is_access_allowed(request, privilege):
        user: User | None = getattr(request.state, "user", None)
        raise AtlasError(AtlasErrorCode.UNAUTHORIZED_ACCESS, None if user is None else user.name, _joined(action))


def _joined(action: Iterable[object]) -> str:
    """``StringUtils.join`` of the action's parts: each its Java text, a collection as ``[a, b]``."""
    return "".join(_text(part) for part in action)


def _text(part: object) -> str:
    if isinstance(part, (list, set, tuple, frozenset)):
        return "[" + ", ".join(str(item) for item in part) + "]"
    return "null" if part is None else str(part)
