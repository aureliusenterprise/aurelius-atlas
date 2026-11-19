"""The tenants' side of the realm, through Keycloak's admin API (TRM-02 to TRM-09, DD-600 to DD-602).

A tenant's organization, its four role groups, the operators trust makes members of it, and the rights of its
administrators. The calls and their answers are Keycloak 26.7's, checked against a running Keycloak.
"""

import json
import ssl
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx2 as httpx

from aurelius_atlas_server.tenancy import READ_ROLE
from aurelius_atlas_server.tenants import StoredTenant

__all__ = [
    "ROLE_GROUPS",
    "KeycloakAdmin",
    "RealmError",
    "RealmOrganization",
    "RealmTenants",
    "StepTaken",
    "administrators_policy",
    "permission_names",
]

ROLE_GROUPS = ("atlas-read", "atlas-write", "atlas-types", "atlas-admin")
"""An organization's four top-level role groups, in the order they are made (DD-564)."""

PAGE = 100
"""How many organizations or members one admin call lists."""

HTTP_TIMEOUT_SECONDS = 10.0

ORGANIZATION_SCOPES = ("view", "manage")
GROUP_SCOPES = ("view", "view-members", "manage-members", "manage-membership")
MEMBER_SCOPES = ("view", "manage-group-membership")
"""The scopes each of a tenant's three permissions grants its administrators (DD-602)."""


class RealmError(Exception):
    """A call the realm refused or failed, with the call and Keycloak's answer (TRM-10)."""


@dataclass(frozen=True)
class RealmOrganization:
    """An organization of the realm: its id, alias, and its role groups' ids by name."""

    id: str
    alias: str
    groups: dict[str, str]


@dataclass(frozen=True)
class StepTaken:
    """What bringing a tenant's realm in step changed: the operators added and removed."""

    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()


def administrators_policy(alias: str) -> str:
    """The name of the user policy that names the tenant's administrators (DD-602)."""
    return f"tenant {alias} administrators"


def permission_names(alias: str) -> tuple[str, str, str]:
    """The names of the tenant's permissions: on its organization, its groups and its members (DD-602)."""
    return f"tenant {alias} organization", f"tenant {alias} groups", f"tenant {alias} members"


class KeycloakAdmin:
    """Keycloak's admin API of ``realm`` at ``server_url``, as the client ``client_id``'s service account (DD-600)."""

    def __init__(  # noqa: PLR0913 - where, as whom, and over which connection
        self,
        server_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        *,
        http: httpx.AsyncClient,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._server = server_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http
        self._clock = clock
        self._token: tuple[str, float] | None = None

    @classmethod
    def http(cls, ca_file: str | None) -> httpx.AsyncClient:
        """The HTTP client for the admin API, verifying the provider with ``ca_file`` or the system's trust."""
        context = ssl.create_default_context(cafile=ca_file) if ca_file else ssl.create_default_context()
        return httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, verify=context)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()

    async def call(
        self, method: str, path: str, *, body: object = None, missing: bool = False, present: bool = False
    ) -> tuple[Any, str | None]:
        """The answer's JSON and its ``Location`` id, for a call under the realm's admin path.

        ``present`` takes a 409 for done: Keycloak 26.7 refuses to add what is there already, as a member of a
        group it has.

        Raises:
            RealmError: For an answer other than 2xx, a 404 excepted when ``missing`` allows it and a 409 when
                ``present`` does.
        """
        url = f"{self._server}/admin/realms/{self._realm}{path}"
        headers = {"Authorization": f"Bearer {await self._access_token()}"}
        content = None if body is None else json.dumps(body).encode()
        if content is not None:
            headers["Content-Type"] = "application/json"
        try:
            response = await self._http.request(method, url, content=content, headers=headers)
        except httpx.HTTPError as error:
            msg = f"the realm could not be reached for {method} {path}: {error}"
            raise RealmError(msg) from error
        if missing and response.status_code == httpx.codes.NOT_FOUND:
            return None, None
        if present and response.status_code == httpx.codes.CONFLICT:
            return None, None
        if not response.is_success:
            msg = f"the realm refused {method} {path}: {response.status_code} {response.text[:200]}"
            raise RealmError(msg)
        location = response.headers.get("location")
        found = response.json() if response.content else None
        return found, None if location is None else location.rstrip("/").rsplit("/", 1)[-1]

    async def _access_token(self) -> str:
        if self._token is not None and self._clock() < self._token[1]:
            return self._token[0]
        url = f"{self._server}/realms/{self._realm}/protocol/openid-connect/token"
        form = {"grant_type": "client_credentials", "client_id": self._client_id, "client_secret": self._client_secret}
        try:
            response = await self._http.post(url, data=form)
        except httpx.HTTPError as error:
            msg = f"the realm could not be reached for a token: {error}"
            raise RealmError(msg) from error
        if not response.is_success:
            msg = f"the realm refused the client {self._client_id} a token: {response.status_code}"
            raise RealmError(msg)
        answer = response.json()
        self._token = (answer["access_token"], self._clock() + float(answer.get("expires_in", 60)) - 10)
        return self._token[0]


class RealmTenants:
    """The tenants' organizations, their operators and administrators in the realm (TRM-02 to TRM-09).

    An operator is a member of ``operator_organization`` holding the realm role ``operator_role`` (DD-601).
    """

    def __init__(self, admin: KeycloakAdmin, *, operator_organization: str, operator_role: str) -> None:
        self.admin = admin
        self._operator_organization = operator_organization
        self._operator_role = operator_role
        self._permissions: str | None = None

    async def organization(self, alias: str) -> RealmOrganization | None:
        """The organization of the alias with its role groups, or None."""
        query = f"search={quote(alias)}&exact=true&briefRepresentation=true"
        found, _ = await self.admin.call("GET", f"/organizations?{query}")
        matches = [org for org in found if org.get("alias") == alias]
        if not matches:
            listed = await self._every("/organizations?briefRepresentation=true")
            matches = [org for org in listed if org.get("alias") == alias]
        if not matches:
            return None
        org_id = matches[0]["id"]
        groups, _ = await self.admin.call("GET", f"/organizations/{org_id}/groups")
        return RealmOrganization(org_id, alias, {group["name"]: group["id"] for group in groups})

    async def ensure_organization(self, alias: str) -> RealmOrganization:
        """The tenant's organization, made with each role group it lacks (TRM-02)."""
        org = await self.organization(alias)
        if org is None:
            _, org_id = await self.admin.call(
                "POST", "/organizations", body={"name": alias, "alias": alias, "enabled": True}
            )
            org = RealmOrganization(str(org_id), alias, {})
        groups = dict(org.groups)
        for name in ROLE_GROUPS:
            if name not in groups:
                _, group_id = await self.admin.call("POST", f"/organizations/{org.id}/groups", body={"name": name})
                groups[name] = str(group_id)
        return RealmOrganization(org.id, alias, groups)

    async def operators(self) -> frozenset[str]:
        """The operators' user ids: the operator organization's members holding the operator role (DD-601)."""
        org = await self.organization(self._operator_organization)
        if org is None:
            return frozenset()
        operators = set()
        for member in await self.members(org):
            roles, _ = await self.admin.call("GET", f"/users/{member}/role-mappings/realm/composite")
            if self._operator_role in {role["name"] for role in roles}:
                operators.add(member)
        return frozenset(operators)

    async def members(self, org: RealmOrganization) -> frozenset[str]:
        """The organization's members' user ids."""
        return frozenset(member["id"] for member in await self._every(f"/organizations/{org.id}/members"))

    async def add_member(self, org: RealmOrganization, user: str) -> None:
        """Make the user a member of the organization, in none of its groups (TRM-03)."""
        await self.admin.call("POST", f"/organizations/{org.id}/members", body=user)

    async def add_to_read_group(self, org: RealmOrganization, user: str) -> None:
        """Put a member in the organization's read group; there already is no fault (TRM-03)."""
        await self.admin.call(
            "PUT", f"/organizations/{org.id}/groups/{org.groups[READ_ROLE]}/members/{user}", present=True
        )

    async def remove_member(self, org: RealmOrganization, user: str) -> None:
        """Remove the user from the organization, with their groups there; gone already is no fault (TRM-04)."""
        await self.admin.call("DELETE", f"/organizations/{org.id}/members/{user}", missing=True)

    async def user_id(self, username: str) -> str:
        """The id of the realm's user of that username.

        Raises:
            RealmError: When the realm has no such user.
        """
        found = await self.find_user(username)
        if found is None:
            msg = f"the realm has no user {username}"
            raise RealmError(msg)
        return found

    async def find_user(self, username: str) -> str | None:
        """The id of the realm's user of that username, or None (TAD-06)."""
        query = f"username={quote(username)}&exact=true&briefRepresentation=true"
        found, _ = await self.admin.call("GET", f"/users?{query}")
        return found[0]["id"] if found else None

    async def create_user(self, representation: dict[str, Any]) -> str:
        """Make a user of the representation; its id (TAD-04, TAD-05).

        Raises:
            RealmError: When the realm refuses it, as for a taken username or a password its policy refuses.
        """
        _, made = await self.admin.call("POST", "/users", body=representation)
        return made if made is not None else await self.user_id(str(representation["username"]))

    async def add_to_groups(self, org: RealmOrganization, user: str, groups: Iterable[str]) -> None:
        """Put a member in the organization's named groups; a group they are in already is no fault (TAD-04)."""
        for group in groups:
            await self.admin.call(
                "PUT", f"/organizations/{org.id}/groups/{org.groups[group]}/members/{user}", present=True
            )

    async def grant(self, org: RealmOrganization, administrators: Iterable[str], members: Iterable[str]) -> None:
        """Grant the administrators the tenant's organization, its groups and its ``members``; with none, grant
        nothing; never a members' permission that names no member, which would name every user (TRM-07, TRM-08).
        """  # noqa: D205 - one sentence
        admins = sorted(administrators)
        on_org, on_groups, on_members = permission_names(org.alias)
        if not admins:
            await self._drop(org.alias)
            return
        policy = await self._ensure_policy(administrators_policy(org.alias), admins)
        await self._ensure_permission(on_org, "Organizations", [org.id], ORGANIZATION_SCOPES, policy)
        await self._ensure_permission(on_groups, "Groups", sorted(org.groups.values()), GROUP_SCOPES, policy)
        covered = sorted(members)
        if covered:
            await self._ensure_permission(on_members, "Users", covered, MEMBER_SCOPES, policy)
        else:
            await self._delete_named("permission", on_members)

    async def in_step(
        self,
        record: StoredTenant,
        operators: frozenset[str],
        save: Callable[[StoredTenant], Awaitable[None]],
    ) -> tuple[StoredTenant, StepTaken]:
        """Bring the tenant's organization in step with its record: made with its groups, ``operators`` its read
        members while it trusts them, those trust added and no longer due removed, its administrators' rights
        over its other members (TRM-02 to TRM-08).

        ``save`` keeps the record after each change of its operators, so a failed call loses none (TRM-10).
        """  # noqa: D205 - one sentence
        org = await self.ensure_organization(record.alias)
        members = await self.members(org)
        due = operators if record.trusts_operators else frozenset()
        listed = set(record.operator_members)
        added: list[str] = []
        removed: list[str] = []

        async def keep() -> StoredTenant:
            kept = record.model_copy(update={"operator_members": sorted(listed)})
            if kept.operator_members != record.operator_members:
                await save(kept)
            return kept

        try:
            for user in sorted(due):
                if user not in members:
                    await self.add_member(org, user)
                    listed.add(user)
                    added.append(user)
                if user in listed:  # again each time, so that an interrupted addition is finished
                    await self.add_to_read_group(org, user)
            for user in sorted(listed - due):
                await self.remove_member(org, user)
                listed.discard(user)
                removed.append(user)
        finally:
            record = await keep()
        own = (members | set(added)) - set(removed) - listed
        await self.grant(org, record.administrators, own)
        return record, StepTaken(tuple(added), tuple(removed))

    async def delete(self, alias: str) -> None:
        """Delete the organization, its groups and memberships with it, and its administrators' rights (TRM-09)."""
        org = await self.organization(alias)
        if org is not None:
            await self.admin.call("DELETE", f"/organizations/{org.id}", missing=True)
        await self._drop(alias)

    async def _drop(self, alias: str) -> None:
        for name in permission_names(alias):
            await self._delete_named("permission", name)
        await self._delete_named("policy", administrators_policy(alias))

    async def _server_path(self) -> str:
        if self._permissions is None:
            found, _ = await self.admin.call("GET", "/clients?clientId=admin-permissions")
            if not found:
                msg = "the realm has no admin-permissions client: fine-grained admin permissions are off"
                raise RealmError(msg)
            self._permissions = f"/clients/{found[0]['id']}/authz/resource-server"
        return self._permissions

    async def _named(self, kind: str, name: str) -> str | None:
        base = await self._server_path()
        found, _ = await self.admin.call("GET", f"{base}/{kind}?name={quote(name)}&exact=true")
        matches = [item for item in found or [] if item.get("name") == name]
        return matches[0]["id"] if matches else None

    async def _delete_named(self, kind: str, name: str) -> None:
        found = await self._named(kind, name)
        if found is not None:
            await self.admin.call("DELETE", f"{await self._server_path()}/{kind}/{found}", missing=True)

    async def _ensure_policy(self, name: str, users: list[str]) -> str:
        base = await self._server_path()
        found = await self._named("policy", name)
        if found is None:
            _, created = await self.admin.call("POST", f"{base}/policy/user", body={"name": name, "users": users})
            return created or str(await self._named("policy", name))
        typed, _ = await self.admin.call("GET", f"{base}/policy/user/{found}")
        await self.admin.call("PUT", f"{base}/policy/user/{found}", body={**typed, "users": users})
        return found

    async def _ensure_permission(
        self, name: str, resource_type: str, resources: list[str], scopes: tuple[str, ...], policy: str
    ) -> None:
        base = await self._server_path()
        body = {"resourceType": resource_type, "resources": resources, "scopes": list(scopes), "policies": [policy]}
        found = await self._named("permission", name)
        if found is None:
            await self.admin.call("POST", f"{base}/permission/scope", body={"name": name, **body})
            return
        typed, _ = await self.admin.call("GET", f"{base}/permission/scope/{found}")
        await self.admin.call("PUT", f"{base}/permission/scope/{found}", body={**typed, **body})

    async def _every(self, path: str) -> list[dict[str, Any]]:
        joiner = "&" if "?" in path else "?"
        listed: list[dict[str, Any]] = []
        while True:
            page, _ = await self.admin.call("GET", f"{path}{joiner}first={len(listed)}&max={PAGE}")
            listed += page
            if len(page) < PAGE:
                return listed
