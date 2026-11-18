"""The standalone stack's tenant users: made by the tenants one shot when their tenant is provisioned (DD-680).

The script is loaded from its file, as the stack mounts it; Keycloak's admin API is stood in for by a realm that
records the calls.
"""

import importlib.util
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

import pytest
from aurelius_atlas_server.realm_tenants import RealmError, RealmOrganization
from conftest import WORKSPACE

SCRIPT = WORKSPACE / "apps/aurelius-atlas-server/docker/tenants.py"
GROUPS = {"atlas-read": "g-read", "atlas-write": "g-write", "atlas-types": "g-types", "atlas-admin": "g-admin"}


def tenants_script() -> ModuleType:
    """The tenants script, loaded from its file."""
    spec = importlib.util.spec_from_file_location("standalone_tenants", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class Admin:
    """Keycloak's admin API: users made by POST, every call recorded."""

    users: dict[str, str]
    calls: list[tuple[str, str, Any]] = field(default_factory=list)

    async def call(
        self, method: str, path: str, *, body: object = None, present: bool = False
    ) -> tuple[Any, str | None]:
        """Record the call; a POST of a user makes it, answering its id. A group addition must allow the 409
        Keycloak answers for a member already in the group (``present``), so a second start passes.
        """  # noqa: D205 - one sentence
        if method == "PUT":
            assert present, path
        self.calls.append((method, path, body))
        if method == "POST" and path == "/users":
            assert isinstance(body, dict)
            self.users[body["username"]] = f"id-{body['username']}"
            return None, self.users[body["username"]]
        return None, None


@dataclass
class Realm:
    """The realm's tenants: one organization, its members, the admin API."""

    admin: Admin
    org: RealmOrganization | None
    member_ids: set[str] = field(default_factory=set)

    async def organization(self, alias: str) -> RealmOrganization | None:
        """The one organization, by its alias."""
        return self.org if self.org is not None and self.org.alias == alias else None

    async def members(self, org: RealmOrganization) -> frozenset[str]:  # noqa: ARG002 - the one organization
        """Its members' ids."""
        return frozenset(self.member_ids)

    async def add_member(self, org: RealmOrganization, user: str) -> None:  # noqa: ARG002 - the one organization
        """Make the user a member."""
        self.member_ids.add(user)

    async def user_id(self, username: str) -> str:
        """The user's id, or the realm's refusal."""
        if username not in self.admin.users:
            msg = f"the realm has no user {username}"
            raise RealmError(msg)
        return self.admin.users[username]


def realm_with(users: dict[str, str] | None = None) -> Realm:
    """A realm with the organization demo and these users."""
    return Realm(Admin(dict(users or {})), RealmOrganization(id="o-demo", alias="demo", groups=GROUPS))


PASSWORDS = {
    "DEMO_USER_ATLAS_PASSWORD": "a",
    "DEMO_USER_STEWARD_PASSWORD": "s",
    "DEMO_USER_SCIENTIST_PASSWORD": "c",
}


def group_puts(admin: Admin, user: str) -> list[str]:
    """The tenant groups the user was put in, by group id."""
    return [
        path.split("/groups/")[1].split("/")[0]
        for method, path, _ in admin.calls
        if method == "PUT" and path.endswith(f"/members/{user}")
    ]


@pytest.mark.covers(rules=["TRM-02", "TRM-06"])
async def test__a_tenant_s_three_users_are_made_members_in_their_role_groups() -> None:
    """Each user is made with its own password, joins the tenant alone, in its groups: atlas all four, the
    steward read and write, the scientist read (DD-680).
    """  # noqa: D205 - one sentence
    realm = realm_with()

    made = await tenants_script().tenant_users(realm, "demo", PASSWORDS)

    assert made == ["demo_atlas", "demo_steward", "demo_scientist"]
    posted = {body["username"]: body for method, path, body in realm.admin.calls if method == "POST"}
    assert posted["demo_steward"]["credentials"] == [{"type": "password", "value": "s", "temporary": False}]
    assert posted["demo_atlas"]["email"] == "demo.atlas@example.com"
    assert realm.member_ids == {"id-demo_atlas", "id-demo_steward", "id-demo_scientist"}
    assert group_puts(realm.admin, "id-demo_atlas") == ["g-read", "g-write", "g-types", "g-admin"]
    assert group_puts(realm.admin, "id-demo_steward") == ["g-read", "g-write"]
    assert group_puts(realm.admin, "id-demo_scientist") == ["g-read"]


@pytest.mark.covers(rules=["TRM-02"])
async def test__a_user_already_there_keeps_its_password_and_a_user_without_one_is_not_made() -> None:
    """The next start makes nothing again; a tenant without a role's password gets no user for it."""
    realm = realm_with({"demo_atlas": "id-old"})
    realm.member_ids.add("id-old")

    made = await tenants_script().tenant_users(realm, "demo", {"DEMO_USER_ATLAS_PASSWORD": "new"})

    assert made == ["demo_atlas"]
    assert not [call for call in realm.admin.calls if call[0] == "POST"]
    assert group_puts(realm.admin, "id-old") == ["g-read", "g-write", "g-types", "g-admin"]


class RefusingAdmin(Admin):
    """An admin API whose realm refuses the steward's password, as its policy refuses a weak one."""

    async def call(
        self, method: str, path: str, *, body: object = None, present: bool = False
    ) -> tuple[Any, str | None]:
        """Refuse the steward; answer the rest."""
        if method == "POST" and isinstance(body, dict) and body["username"] == "demo_steward":
            self.calls.append((method, path, body))
            msg = "the realm refused POST /users: 400 invalidPasswordMinSpecialCharsMessage"
            raise RealmError(msg)
        return await super().call(method, path, body=body, present=present)


@pytest.mark.covers(rules=["TRM-02"])
async def test__a_user_the_realm_refuses_is_left_out_and_the_rest_are_made() -> None:
    """A password the realm's policy rejects costs that user alone: the others, and the next tenant, follow."""
    realm = Realm(RefusingAdmin({}), RealmOrganization(id="o-demo", alias="demo", groups=GROUPS))

    made = await tenants_script().tenant_users(realm, "demo", PASSWORDS)

    assert made == ["demo_atlas", "demo_scientist"]
    assert realm.member_ids == {"id-demo_atlas", "id-demo_scientist"}


@pytest.mark.covers(rules=["TRM-02"])
async def test__a_tenant_without_its_organization_is_a_fault() -> None:
    """Users are made after the provisioning made the organization; without it, the one shot stops."""
    realm = Realm(Admin({}), None)

    with pytest.raises(RealmError, match="demo has no organization"):
        await tenants_script().tenant_users(realm, "demo", PASSWORDS)
