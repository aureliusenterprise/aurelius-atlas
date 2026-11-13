"""Tenancy: a request's tenant and its roles there, from its token's organization claim (TEN-01 to TEN-06).

A tenant is a Keycloak organization (ADR 063). A token names the organizations it acts for in the organization
claim; with tenancy on it must name exactly one, provisioned (DD-563, DD-565). The roles in it are the
organization's own groups (DD-564), and an operator only reads outside the operator organization (DD-567).
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

__all__ = ["ALIAS", "TENANT_ROLES", "Tenancy", "organizations", "tenant_of", "tenant_roles"]

TENANT_ROLES = frozenset({"atlas-read", "atlas-write", "atlas-types", "atlas-admin"})
"""The four roles a tenant's groups grant (AUZ-02): the group ``/<role>`` of the organization grants ``<role>``."""

READ_ROLE = "atlas-read"
"""All an operator holds outside the operator organization (TEN-06)."""

ALIAS = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
"""A tenant alias that is safe in an index name: a lowercase letter or digit, then up to 62 more or ``-`` (DD-565)."""


@dataclass(frozen=True)
class Tenancy:
    """How tenancy reads a token, while it is on: its organization claim, the operators, the provisioned tenants."""

    organization_claim: str = "organization"
    operator_organization: str = "operators"
    operator_role: str = "atlas-operator"
    tenants: frozenset[str] = frozenset()

    def is_provisioned(self, alias: str) -> bool:
        """Whether a tenant may act: an index-safe alias, the operator organization's or a provisioned one (TEN-04)."""
        return ALIAS.fullmatch(alias) is not None and (alias == self.operator_organization or alias in self.tenants)


def organizations(claims: Mapping[str, Any], claim: str) -> dict[str, Any]:
    """The organizations a token names, each alias with what its claim holds of it (TEN-02).

    The claim's strings when it is a list (the Organization Membership mapper), each with None; its entries when
    it is an object (the same mapper with the id or attributes, or the Organization Group Membership mapper).
    A missing claim, or one of another shape, names none.
    """
    match claims.get(claim):
        case list() as aliases:
            return {alias: None for alias in aliases if isinstance(alias, str)}
        case dict() as entries:
            return {str(alias): entry for alias, entry in entries.items()}
        case _:
            return {}


def tenant_of(claims: Mapping[str, Any], tenancy: Tenancy, user: str) -> tuple[str, Any]:
    """The one provisioned tenant a token acts in, with what its organization claim holds of it (TEN-03, TEN-04).

    Raises:
        AtlasError: ``NO_TENANT`` or ``SEVERAL_TENANTS`` unless the token names one organization;
            ``TENANT_NOT_PROVISIONED`` for an alias that isn't index-safe or provisioned.
    """
    named = organizations(claims, tenancy.organization_claim)
    if not named:
        raise AtlasError(AtlasErrorCode.NO_TENANT, user)
    if len(named) > 1:
        raise AtlasError(AtlasErrorCode.SEVERAL_TENANTS, user, len(named))
    [(alias, entry)] = named.items()
    if not tenancy.is_provisioned(alias):
        raise AtlasError(AtlasErrorCode.TENANT_NOT_PROVISIONED, alias)
    return alias, entry


def tenant_roles(claims: Mapping[str, Any], tenancy: Tenancy, tenant: str, entry: object) -> frozenset[str]:
    """The user's roles in the tenant: its own top-level groups among the four roles (TEN-05), capped at read for
    an operator outside the operator organization (TEN-06).
    """  # noqa: D205 - one sentence
    groups = entry.get("groups") if isinstance(entry, dict) else None
    held = (
        frozenset(group[1:] for group in groups or () if isinstance(group, str) and group.startswith("/"))
        & TENANT_ROLES
    )
    if tenant != tenancy.operator_organization and tenancy.operator_role in _realm_roles(claims):
        return held & {READ_ROLE}
    return held


def _realm_roles(claims: Mapping[str, Any]) -> frozenset[str]:
    """The token's realm roles, ``realm_access.roles``."""
    match claims.get("realm_access"):
        case {"roles": list() as roles}:
            return frozenset(role for role in roles if isinstance(role, str))
        case _:
            return frozenset()
