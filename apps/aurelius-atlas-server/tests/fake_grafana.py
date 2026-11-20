"""A stand-in for Grafana's HTTP API and the store's security API, as far as the tenants' Grafana uses them (15.9).

Grafana: organizations by id and name, users by id with their login and email, each organization's members and
their roles, data sources by uid and dashboards by uid per organization, and each user's current organization. A
user made through the admin API joins the main organization with no role, as the stack's auto-assignment does.
Every call is recorded.
"""

# ruff: noqa: INP001, S101 - a test helper beside the tests, asserting what the stand-in assumes

import itertools
import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx2 as httpx

URL = "http://grafana.test:3000"
ADMIN_PASSWORD = "admin-secret"  # noqa: S105 - a test value


@dataclass
class Org:
    """One organization: its name, members' roles by user id, data sources and dashboards by uid."""

    id: int
    name: str
    members: dict[int, str] = field(default_factory=dict)
    datasources: dict[str, dict[str, Any]] = field(default_factory=dict)
    dashboards: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class FakeGrafana:
    """Grafana's organizations and users, the calls made, and each user's current organization."""

    orgs: dict[int, Org] = field(default_factory=dict)
    users: dict[int, dict[str, Any]] = field(default_factory=dict)
    using: dict[int, int] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)
    _ids: itertools.count = field(default_factory=lambda: itertools.count(2))

    def __post_init__(self) -> None:
        """The main organization and the local administrator, its Admin."""
        self.orgs[1] = Org(1, "Main Org.", {1: "Admin"})
        self.users[1] = {"id": 1, "login": "admin", "email": "admin@localhost", "isAdmin": True}

    def transport(self) -> httpx.MockTransport:
        """The transport answering as Grafana."""
        return httpx.MockTransport(self._handle)

    def by_name(self, name: str) -> Org | None:
        """The organization of that name."""
        return next((org for org in self.orgs.values() if org.name == name), None)

    def login(self, user_id: int) -> str:
        """A user's login."""
        return str(self.users[user_id]["login"])

    def roles(self, name: str) -> dict[str, str]:
        """The organization's members' roles, by login."""
        org = self.by_name(name) if name != "main" else self.orgs[1]
        assert org is not None
        return {self.login(user_id): role for user_id, role in org.members.items()}

    def _user_id(self, login_or_email: str) -> int | None:
        return next((i for i, u in self.users.items() if login_or_email in {u["login"], u["email"]}), None)

    def _handle(self, request: httpx.Request) -> httpx.Response:  # noqa: C901, PLR0911, PLR0912, PLR0915 - one fake router
        assert request.headers.get("authorization", "").startswith("Basic ")
        url = urlparse(str(request.url))
        path, query = url.path, {k: v[0] for k, v in parse_qs(url.query).items()}
        method = request.method
        self.calls.append((method, path))
        body: Any = json.loads(request.content) if request.content else {}
        org = self.orgs.get(int(request.headers.get("X-Grafana-Org-Id", "1")))
        if path == "/api/orgs" and method == "GET":
            return httpx.Response(200, json=[{"id": o.id, "name": o.name} for o in self.orgs.values()])
        if path == "/api/orgs" and method == "POST":
            if self.by_name(body["name"]) is not None:
                return httpx.Response(409, json={"message": "Organization name taken"})
            made = Org(next(self._ids), body["name"], {1: "Admin"})
            self.orgs[made.id] = made
            return httpx.Response(200, json={"orgId": made.id})
        if match := re.fullmatch(r"/api/orgs/name/(.+)", path):
            found = self.by_name(unquote(match[1]))
            return (
                httpx.Response(404) if found is None else httpx.Response(200, json={"id": found.id, "name": found.name})
            )
        if (match := re.fullmatch(r"/api/orgs/(\d+)", path)) and method == "DELETE":
            del self.orgs[int(match[1])]
            return httpx.Response(200, json={})
        if match := re.fullmatch(r"/api/orgs/(\d+)/users", path):
            target = self.orgs[int(match[1])]
            if method == "GET":
                return httpx.Response(
                    200,
                    json=[{"userId": i, "login": self.login(i), "role": r} for i, r in target.members.items()],
                )
            user_id = self._user_id(body["loginOrEmail"])
            if user_id is None:
                return httpx.Response(404)
            if user_id in target.members:
                return httpx.Response(409, json={"message": "User is already member of this organization"})
            target.members[user_id] = body["role"]
            return httpx.Response(200, json={})
        if match := re.fullmatch(r"/api/orgs/(\d+)/users/(\d+)", path):
            target, user_id = self.orgs[int(match[1])], int(match[2])
            if method == "PATCH":
                target.members[user_id] = body["role"]
            else:
                target.members.pop(user_id, None)
            return httpx.Response(200, json={})
        if path == "/api/users/lookup":
            user_id = self._user_id(query["loginOrEmail"])
            return httpx.Response(404) if user_id is None else httpx.Response(200, json=self.users[user_id])
        if path == "/api/users/search":
            users = list(self.users.values())
            return httpx.Response(200, json={"users": users, "totalCount": len(users)})
        if path == "/api/admin/users" and method == "POST":
            if self._user_id(body["login"]) is not None:
                return httpx.Response(412, json={"message": "User with same login already exists"})
            user_id = next(self._ids)
            self.users[user_id] = {"id": user_id, "login": body["login"], "email": body["email"], "isAdmin": False}
            self.orgs[1].members[user_id] = "None"
            self.using[user_id] = 1
            return httpx.Response(200, json={"id": user_id})
        if (match := re.fullmatch(r"/api/admin/users/(\d+)", path)) and method == "DELETE":
            user_id = int(match[1])
            del self.users[user_id]
            for each in self.orgs.values():
                each.members.pop(user_id, None)
            return httpx.Response(200, json={})
        if match := re.fullmatch(r"/api/users/(\d+)/using/(\d+)", path):
            self.using[int(match[1])] = int(match[2])
            return httpx.Response(200, json={})
        assert org is not None
        if match := re.fullmatch(r"/api/datasources/uid/(.+)", path):
            if method == "GET":
                found = org.datasources.get(match[1])
                return httpx.Response(404) if found is None else httpx.Response(200, json=found)
            org.datasources[match[1]] = body
            return httpx.Response(200, json={})
        if path == "/api/datasources" and method == "POST":
            org.datasources[body["uid"]] = body
            return httpx.Response(200, json={})
        if path == "/api/dashboards/db" and method == "POST":
            org.dashboards[body["dashboard"]["uid"]] = body["dashboard"]
            return httpx.Response(200, json={})
        return httpx.Response(404)


@dataclass
class FakeSecurity:
    """The store's security API: users with their password and roles, roles with their privileges."""

    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    roles: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def put_role(self, *, name: str, **privileges: Any) -> None:  # noqa: ANN401
        """Make or replace a role."""
        self.roles[name] = privileges

    async def put_user(self, *, username: str, password: str, roles: list[str], **_: Any) -> None:  # noqa: ANN401
        """Make or replace a user."""
        self.users[username] = {"password": password, "roles": roles}

    async def get_user(self, *, username: str) -> Any:  # noqa: ANN401
        """The user, under its name, or nothing."""
        return type("Answer", (), {"body": {username: self.users[username]} if username in self.users else {}})()

    async def delete_user(self, *, username: str) -> None:
        """Delete a user; gone already is no fault."""
        self.users.pop(username, None)

    async def delete_role(self, *, name: str) -> None:
        """Delete a role; gone already is no fault."""
        self.roles.pop(name, None)


@dataclass
class FakeStore:
    """The store's client, as far as the tenants' Grafana uses it."""

    security: FakeSecurity = field(default_factory=FakeSecurity)

    def options(self, **_: Any) -> FakeStore:  # noqa: ANN401
        """The same client, its options aside."""
        return self
