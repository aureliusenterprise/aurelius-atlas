"""Authorization: Atlas's privileges, granted by four roles of the server's client (AUZ-01 to AUZ-03, DD-300).

What a user may do is decided in one place (ADR 038): the identity provider holds who has which role, and this
module what each role grants. The stores check a request as Atlas's do, through the request's ``authorizer``; a
check refused is Atlas's ``UNAUTHORIZED_ACCESS``.
"""

from aurelius_atlas_core.authorization import AtlasPrivilege, Granted
from fastapi import Request

from aurelius_atlas_server.authentication import User

__all__ = ["ROLE_PRIVILEGES", "AtlasPrivilege", "authorizer", "is_access_allowed", "privileges", "verify_access"]

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
"""What each role of the server's client grants (AUZ-02, DD-300); ``atlas-types`` reads the types it may change,
as Atlas's simple authorizer adds ``TYPE_READ``."""


def privileges(user: User | None) -> frozenset[AtlasPrivilege]:
    """Every privilege the user's roles grant; none without a user (AUZ-01, AUZ-02)."""
    if user is None:
        return frozenset()
    return frozenset(privilege for role in user.roles for privilege in ROLE_PRIVILEGES.get(role, ()))


def authorizer(request: Request) -> Granted:
    """The authorizer of the request's stores: the privileges of its user (AUZ-03, AUZ-07 to AUZ-10)."""
    user: User | None = getattr(request.state, "user", None)
    return Granted(None if user is None else user.name, privileges(user))


def is_access_allowed(request: Request, privilege: AtlasPrivilege) -> bool:
    """``isAccessAllowed``: whether the request's user holds the privilege (AUZ-02)."""
    return authorizer(request).is_access_allowed(privilege)


def verify_access(request: Request, privilege: AtlasPrivilege, *action: object) -> None:
    """``verifyAccess``: refuse the request without the privilege, naming the action (AUZ-03).

    Raises:
        AtlasError: ``UNAUTHORIZED_ACCESS``, ``<user> is not authorized to perform <action>``.
    """
    authorizer(request).verify_access(privilege, *action)
