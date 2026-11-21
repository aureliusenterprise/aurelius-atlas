"""The caller's tenant: the one organization its verified token names (VET-01, 12.7f).

The claim is read as the Atlas server reads it (TEN-02): Keycloak's organization mapper writes a list of
aliases, or an object keyed by them when it carries the groups. A token naming none, or more than one, acts in
no tenant, and the rules are read as the app's own identity (VET-03).
"""

from collections.abc import Mapping
from typing import Any

__all__ = ["ORGANIZATION_CLAIM", "tenant_of"]

ORGANIZATION_CLAIM = "organization"
"""The claim that names the organizations a token acts for (TEN-02)."""


def tenant_of(claims: Mapping[str, Any]) -> str | None:
    """The one organization the claims name, or None for none or several (VET-01)."""
    match claims.get(ORGANIZATION_CLAIM):
        case list() as aliases:
            named = [alias for alias in aliases if isinstance(alias, str)]
        case dict() as entries:
            named = [str(alias) for alias in entries]
        case _:
            named = []
    return named[0] if len(named) == 1 else None
