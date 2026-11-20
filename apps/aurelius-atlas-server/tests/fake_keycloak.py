"""A fake of Keycloak 26.7's admin API for the realm's tenants (TRM-02 to TRM-10, DD-600 to DD-602).

It answers the calls ``realm_tenants`` makes as a running Keycloak 26.7.4 answered them: organizations found by
an exact search, created with a ``Location``, their alias unique; a group's member must be the organization's;
policies and permissions created with their representation in the body and no ``Location``; an organization's
deletion drops the permissions on it and its groups, and leaves the others.
"""

# ruff: noqa: INP001

import itertools
import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx2 as httpx

SERVER = "https://keycloak.test"
REALM = "atlas"
CLIENT_ID = "aurelius-atlas-provisioning"
CLIENT_SECRET = "provisioning-secret"  # noqa: S105 - the fake realm's own


@dataclass
class Organization:
    """An organization: its alias, its groups' ids by name, and its members' ids with their groups' ids."""

    id: str
    alias: str
    name: str = ""
    groups: dict[str, str] = field(default_factory=dict)
    members: dict[str, set[str]] = field(default_factory=dict)


@dataclass
class FakeKeycloak:
    """The realm's users, organizations, policies and permissions, and the calls made; ``refuse`` answers a
    method and path prefix with a status.
    """  # noqa: D205 - one sentence

    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    organizations: dict[str, Organization] = field(default_factory=dict)
    policies: dict[str, dict[str, Any]] = field(default_factory=dict)
    permissions: dict[str, dict[str, Any]] = field(default_factory=dict)
    refuse: dict[tuple[str, str], int] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)
    tokens: int = 0
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1))

    def new_id(self, kind: str) -> str:
        """A fresh id, readable in a failing test."""
        return f"{kind}-{next(self._ids)}"

    def user(self, username: str, *, roles: tuple[str, ...] = ()) -> str:
        """Add a user with realm roles; their id."""
        user_id = self.new_id("user")
        self.users[user_id] = {"id": user_id, "username": username, "roles": set(roles)}
        return user_id

    def organization(
        self, alias: str, members: dict[str, tuple[str, ...]] | None = None, *, name: str = ""
    ) -> Organization:
        """Add an organization, named its alias unless ``name``, with the four groups and members in some."""
        org = Organization(self.new_id("org"), alias, name or alias)
        for group in ("atlas-read", "atlas-write", "atlas-types", "atlas-admin"):
            org.groups[group] = self.new_id("group")
        for user_id, groups in (members or {}).items():
            org.members[user_id] = {org.groups[group] for group in groups}
        self.organizations[org.id] = org
        return org

    def by_alias(self, alias: str) -> Organization | None:
        """The organization of the alias, if any."""
        return next((org for org in self.organizations.values() if org.alias == alias), None)

    def named(self, kind: str, name: str) -> dict[str, Any] | None:
        """The policy or permission of that name, if any."""
        items = self.policies if kind == "policy" else self.permissions
        return next((item for item in items.values() if item["name"] == name), None)

    def transport(self) -> httpx.MockTransport:
        """The transport an ``httpx.AsyncClient`` reaches the fake with."""
        return httpx.MockTransport(self._answer)

    def _answer(self, request: httpx.Request) -> httpx.Response:
        url = urlparse(str(request.url))
        if url.path == f"/realms/{REALM}/protocol/openid-connect/token":
            form = parse_qs(request.content.decode())
            if form.get("client_secret") != [CLIENT_SECRET]:
                return httpx.Response(401, json={"error": "unauthorized_client"})
            self.tokens += 1
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        prefix = f"/admin/realms/{REALM}"
        path = url.path.removeprefix(prefix)
        self.calls.append((request.method, path))
        for (method, refused), status in self.refuse.items():
            if request.method == method and path.startswith(refused):
                return httpx.Response(status, json={"error": "refused"})
        query = {key: values[0] for key, values in parse_qs(url.query).items()}
        body = json.loads(request.content) if request.content else None
        return self._route(request.method, path, query, body)

    def _route(self, method: str, path: str, query: dict[str, str], body: Any) -> httpx.Response:  # noqa: ANN401, C901, PLR0911, PLR0912 - one fake router
        if path == "/organizations" and method == "GET":
            found = list(self.organizations.values())
            if "search" in query:  # Keycloak matches the name (or a domain), not the alias
                found = [org for org in found if org.name == query["search"]]
            return _page([{"id": org.id, "name": org.name, "alias": org.alias} for org in found], query)
        if path == "/organizations" and method == "POST":
            if self.by_alias(body["alias"]) is not None:
                return httpx.Response(409, json={"errorMessage": "A organization with the same alias already exists"})
            org = Organization(self.new_id("org"), body["alias"], body["name"])
            self.organizations[org.id] = org
            return httpx.Response(201, headers={"Location": f"{SERVER}/admin/realms/{REALM}/organizations/{org.id}"})
        if match := re.fullmatch(r"/organizations/([^/]+)", path):
            org = self.organizations.get(match[1])
            if org is None:
                return httpx.Response(404)
            if method == "DELETE":
                del self.organizations[org.id]
                dropped = {org.id, *org.groups.values()}
                for key in [k for k, p in self.permissions.items() if set(p["resources"]) & dropped]:
                    del self.permissions[key]
                return httpx.Response(204)
            return httpx.Response(200, json={"id": org.id, "alias": org.alias})
        if match := re.fullmatch(r"/organizations/([^/]+)/groups", path):
            org = self.organizations[match[1]]
            if method == "POST":
                group_id = self.new_id("group")
                org.groups[body["name"]] = group_id
                return httpx.Response(201, headers={"Location": f"{SERVER}{path}/{group_id}"})
            return httpx.Response(200, json=[{"id": i, "name": n, "path": f"/{n}"} for n, i in org.groups.items()])
        if match := re.fullmatch(r"/organizations/([^/]+)/members", path):
            org = self.organizations[match[1]]
            if method == "POST":
                if body in org.members:
                    return httpx.Response(409, json={"errorMessage": "User is already a member"})
                org.members[body] = set()
                return httpx.Response(201)
            return _page(
                [{"id": user_id, "username": self.users[user_id]["username"]} for user_id in org.members], query
            )
        if match := re.fullmatch(r"/organizations/([^/]+)/members/([^/]+)", path):
            org = self.organizations[match[1]]
            if org.members.pop(match[2], None) is None:
                return httpx.Response(404)
            return httpx.Response(204)
        if match := re.fullmatch(r"/organizations/([^/]+)/groups/([^/]+)/members/([^/]+)", path):
            org, group, user_id = self.organizations[match[1]], match[2], match[3]
            if user_id not in org.members:
                return httpx.Response(400, json={"errorMessage": "User is not member of the organization"})
            if method == "PUT":
                if group in org.members[user_id]:  # Keycloak 26.7 refuses a second addition
                    return httpx.Response(409, json={"errorMessage": "User is already a member of the group"})
                org.members[user_id].add(group)
            else:
                org.members[user_id].discard(group)
            return httpx.Response(204)
        if path == "/users" and method == "POST":  # as Keycloak 26.7: 409 for a taken username
            if any(u["username"] == body["username"] for u in self.users.values()):
                return httpx.Response(409, json={"errorMessage": "User exists with same username"})
            user_id = self.new_id("user")
            self.users[user_id] = {"id": user_id, "roles": set(), **body}
            return httpx.Response(201, headers={"Location": f"{SERVER}/admin/realms/{REALM}/users/{user_id}"})
        if path == "/users":
            found = [u for u in self.users.values() if u["username"] == query.get("username")]
            return httpx.Response(200, json=[{"id": u["id"], "username": u["username"]} for u in found])
        if (match := re.fullmatch(r"/users/([^/]+)", path)) and method == "GET":
            found = self.users.get(match[1])
            if found is None:
                return httpx.Response(404)
            return httpx.Response(200, json={k: v for k, v in found.items() if k != "roles"})
        if match := re.fullmatch(r"/users/([^/]+)/role-mappings/realm/composite", path):
            return httpx.Response(200, json=[{"name": role} for role in sorted(self.users[match[1]]["roles"])])
        if path == "/clients":
            return httpx.Response(200, json=[{"id": "admin-permissions-id", "clientId": "admin-permissions"}])
        base = "/clients/admin-permissions-id/authz/resource-server"
        if not path.startswith(base):
            return httpx.Response(404)
        return self._authz(method, path.removeprefix(base), query, body)

    def _authz(self, method: str, path: str, query: dict[str, str], body: Any) -> httpx.Response:  # noqa: ANN401, PLR0911 - the permissions' router
        if path in {"/policy", "/permission"} and method == "GET":
            item = self.named(path.strip("/"), query.get("name", ""))
            return httpx.Response(200, json=[] if item is None else [{"id": item["id"], "name": item["name"]}])
        if path in {"/policy/user", "/permission/scope"} and method == "POST":
            kind = "policy" if path == "/policy/user" else "permission"
            if self.named(kind, body["name"]) is not None:
                return httpx.Response(409, json={"error": "conflict"})
            item = {**body, "id": self.new_id(kind)}
            (self.policies if kind == "policy" else self.permissions)[item["id"]] = item
            return httpx.Response(201, json=item)
        if match := re.fullmatch(r"/(policy/user|permission/scope)/([^/]+)", path):
            items = self.policies if match[1] == "policy/user" else self.permissions
            if method == "GET":
                found = items[match[2]]
                return httpx.Response(200, json={"id": found["id"], "name": found["name"], "type": "user"})
            items[match[2]] = {**items[match[2]], **body}
            return httpx.Response(201)
        if match := re.fullmatch(r"/(policy|permission)/([^/]+)", path):
            items = self.policies if match[1] == "policy" else self.permissions
            return httpx.Response(204 if items.pop(match[2], None) is not None else 404)
        return httpx.Response(404)


def _page(items: list[dict[str, Any]], query: dict[str, str]) -> httpx.Response:
    first, most = int(query.get("first", 0)), int(query.get("max", 10))
    return httpx.Response(200, json=items[first : first + most])
