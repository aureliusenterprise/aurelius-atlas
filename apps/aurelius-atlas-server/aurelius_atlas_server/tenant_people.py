"""A tenant's people: users made in the realm and put in the tenant with the groups of their role (15.7).

The command `add` makes a tenant's standard users, `user add` one person; the standalone stack's one shot seeds
demo's and meyn's through the same code (TAD-03 to TAD-07, TAD-13). A person is a member of the tenants they are
added to and of no other; a user the realm has already is found, not made again, and keeps its password
(TAD-06). A person the command makes gets a temporary password, which they change at the first sign-in
(DD-701).
"""

import secrets
import string
from dataclasses import dataclass
from enum import StrEnum

from aurelius_atlas_server.realm_tenants import RealmOrganization, RealmTenants

__all__ = [
    "ROLES",
    "Person",
    "Role",
    "ensure_person",
    "standard_email",
    "standard_username",
    "temporary_password",
]


class Role(StrEnum):
    """A tenant person's role: the groups they get, and the standard user's name after ``<tenant>_``."""

    ATLAS = "atlas"
    STEWARD = "steward"
    SCIENTIST = "scientist"


@dataclass(frozen=True)
class RoleShape:
    """A role's first and last name for its standard user, and the tenant's groups it gets."""

    first: str
    last: str
    groups: tuple[str, ...]


ROLES: dict[Role, RoleShape] = {
    Role.ATLAS: RoleShape("Atlas", "Administrator", ("atlas-read", "atlas-write", "atlas-types", "atlas-admin")),
    Role.STEWARD: RoleShape("Data", "Steward", ("atlas-read", "atlas-write")),
    Role.SCIENTIST: RoleShape("Data", "Scientist", ("atlas-read",)),
}
"""Each role's names and groups (TAD-04, the spec's table)."""

PASSWORD_LENGTH = 16
"""Characters of a generated password: above the realm policy's 12 (DD-701)."""

SPECIALS = "!#%+-=?@"
"""The special characters a generated password draws from: none a shell or a URL quotes."""


@dataclass(frozen=True)
class Person:
    """A person of a tenant after the command: their username, role, whether made now, and their temporary
    password when made with one (TAD-08).
    """  # noqa: D205 - one sentence

    username: str
    role: Role
    made: bool
    password: str | None


def standard_username(tenant: str, role: Role) -> str:
    """The standard user's name: ``<tenant>_<role>`` (TAD-04)."""
    return f"{tenant}_{role.value}"


def standard_email(tenant: str, role: Role) -> str:
    """The standard user's email: ``<tenant>.<role>@example.com`` (TAD-04)."""
    return f"{tenant}.{role.value}@example.com"


def temporary_password() -> str:
    """A random password that meets the realm's policy: 16 characters, at least one upper- and one lower-case
    letter, one digit and one special character (TAD-05, DD-701).
    """  # noqa: D205 - one sentence
    alphabet = string.ascii_letters + string.digits + SPECIALS
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(SPECIALS),
    ]
    characters = required + [secrets.choice(alphabet) for _ in range(PASSWORD_LENGTH - len(required))]
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)


async def ensure_person(  # noqa: PLR0913 - where, who, and how their password is set
    realm: RealmTenants,
    org: RealmOrganization,
    username: str,
    role: Role,
    *,
    email: str,
    password: str | None = None,
) -> Person:
    """The person, found or made, a member of the organization in the groups of their role (TAD-04 to TAD-07).

    A user the realm has is not made again and keeps its password (TAD-06). A user made with ``password`` gets it
    as permanent, the seeded tenants' way (TAD-13, DD-700); without, a generated temporary one, which they change
    at the first sign-in (TAD-05, DD-701).
    """
    shape = ROLES[role]
    user = await realm.find_user(username)
    made_password: str | None = None
    if user is None:
        temporary = password is None
        made_password = temporary_password() if temporary else password
        user = await realm.create_user(
            {
                "username": username,
                "email": email,
                "emailVerified": True,
                "enabled": True,
                "firstName": shape.first,
                "lastName": shape.last,
                "credentials": [{"type": "password", "value": made_password, "temporary": temporary}],
                **({"requiredActions": ["UPDATE_PASSWORD"]} if temporary else {}),
            }
        )
    if user not in await realm.members(org):
        await realm.add_member(org, user)
    await realm.add_to_groups(org, user, shape.groups)
    return Person(username, role, made=made_password is not None, password=made_password if password is None else None)
