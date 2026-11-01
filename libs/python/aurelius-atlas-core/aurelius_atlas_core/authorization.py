"""``AtlasAuthorizationUtils``: the checks the stores make, against what the acting user was granted (AUZ-03, AUZ-07).

The stores do not know how privileges are granted: the server builds an authorizer of the acting user's
privileges (DD-300) and hands it to each store of a request. A store built without one checks nothing, as the
tests of its behaviour and the server's own startup work need (DD-301). What the user may not read is scrubbed
from search results and left out of type listings, as Atlas's authorizer does (AUZ-12, AUZ-14).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from aurelius_atlas_model.discovery import AtlasSearchResult
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import AtlasEntityHeader
from aurelius_atlas_model.typedef import AtlasTypesDef

from aurelius_atlas_core.typedef_store import types_def_of


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

    def is_access_allowed(self, privilege: AtlasPrivilege) -> bool:
        """``isAccessAllowed``: whether the user holds the privilege."""
        ...

    def verify_access(self, privilege: AtlasPrivilege, *action: object) -> None:
        """``verifyAccess``: refuse without the privilege, naming the action."""
        ...


class AllowAll:
    """The authorizer of a store built without one: everything is allowed (DD-301)."""

    def is_access_allowed(self, privilege: AtlasPrivilege) -> bool:  # noqa: ARG002 - the protocol's
        """Allowed."""
        return True

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


SCRUBBED_GUID = "-1"
"""The GUID a scrubbed entity header shows (``AtlasAuthorizer.scrubEntityHeader``)."""


def scrub_entity_header(header: AtlasEntityHeader) -> None:
    """``scrubEntityHeader``: the GUID ``-1``, and each present attribute, classification and meaning list emptied."""
    header.guid = SCRUBBED_GUID
    for name in ("attributes", "classifications", "classification_names", "meanings", "meaning_names"):
        value = getattr(header, name)
        if value is not None:
            value.clear()


def scrub_search_results(authorizer: Authorizer, result: AtlasSearchResult) -> None:
    """``scrubSearchResults``: scrub each entity, full-text hit and referred entity the user may not read (AUZ-12)."""
    headers = [
        *(result.entities or []),
        *(found.entity for found in result.full_text_result or [] if found is not None),
        *(result.referred_entities or {}).values(),
    ]
    for header in headers:
        if header is not None and not authorizer.is_access_allowed(AtlasPrivilege.ENTITY_READ):
            scrub_entity_header(header)


def filter_types_def(authorizer: Authorizer, types_def: AtlasTypesDef) -> AtlasTypesDef:
    """``filterTypesDef``: the definitions of each kind the user may read (AUZ-14)."""
    kinds = (
        types_def.enum_defs,
        types_def.struct_defs,
        types_def.classification_defs,
        types_def.entity_defs,
        types_def.relationship_defs,
        types_def.business_metadata_defs,
    )
    return types_def_of(
        typedef
        for typedefs in kinds
        for typedef in typedefs or []
        if authorizer.is_access_allowed(AtlasPrivilege.TYPE_READ)
    )
