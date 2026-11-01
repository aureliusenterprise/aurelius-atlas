"""``AtlasAuthorizationUtils``: the checks the stores make, against what the acting user was granted (AUZ-03, AUZ-07).

The stores do not know how privileges are granted: the server builds an authorizer of the acting user's
privileges (DD-253) and hands it to each store of a request. A store built without one checks nothing, as the
tests of its behaviour and the server's own startup work need (DD-254).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string


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


class Authorizer(Protocol):
    """What a store asks before it reads or changes an entity or relationship."""

    def verify_access(self, privilege: AtlasPrivilege, *action: object) -> None:
        """``verifyAccess``: refuse without the privilege, naming the action."""
        ...


class AllowAll:
    """The authorizer of a store built without one: everything is allowed (DD-254)."""

    def verify_access(self, privilege: AtlasPrivilege, *action: object) -> None:
        """Allow."""


ALLOW_ALL = AllowAll()


@dataclass(frozen=True)
class Granted:
    """The privileges granted to ``user``, the acting user of a request (AUZ-03)."""

    user: str | None
    privileges: frozenset[AtlasPrivilege]

    def is_access_allowed(self, privilege: AtlasPrivilege) -> bool:
        """``isAccessAllowed``: whether the user holds the privilege."""
        return privilege in self.privileges

    def verify_access(self, privilege: AtlasPrivilege, *action: object) -> None:
        """``verifyAccess``: refuse without the privilege, naming the action (AUZ-03).

        Raises:
            AtlasError: ``UNAUTHORIZED_ACCESS``, ``<user> is not authorized to perform <action>``.
        """
        if not self.is_access_allowed(privilege):
            raise AtlasError(AtlasErrorCode.UNAUTHORIZED_ACCESS, self.user, joined(action))


def joined(action: Iterable[object]) -> str:
    """``StringUtils.join`` of the action's parts: each its Java text, a null part empty (``[a, b]``, ``{k=v}``)."""
    return "".join("" if part is None else java_string(part) for part in action)
