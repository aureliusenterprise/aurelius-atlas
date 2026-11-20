"""The tenants' side of Grafana, through its HTTP API as its local administrator (15.9, TGF-04 to TGF-14).

Each tenant has a Grafana organization named after it, with two Elasticsearch data sources that read the tenant's
indices alone as a store user of that tenant, and the dashboards shipped in this package (DD-737, DD-738). The
tenant's members are its Viewers; the operators are Viewers of the main organization, the platform's, where
everyone else has no role (DD-736). Nothing here takes a role from a token: the tenant command keeps it.
"""

import asyncio
import json
import secrets
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from importlib import resources
from typing import Any
from urllib.parse import quote

import httpx2 as httpx

__all__ = [
    "MAIN_ORG",
    "GrafanaAdmin",
    "GrafanaError",
    "GrafanaTenants",
    "Person",
    "reader_name",
    "reader_role",
]

MAIN_ORG = 1
"""Grafana's main organization: the platform's, which holds the infra slice's dashboards."""

ADMIN_LOGIN = "admin"
"""Grafana's local administrator, never a member the command keeps or deletes."""

VIEWER = "Viewer"
NO_ROLE = "None"
ORG_HEADER = "X-Grafana-Org-Id"
HTTP_TIMEOUT_SECONDS = 10.0
CONNECT_ATTEMPTS = 30
"""How often a call is tried while Grafana is not yet answering, one second apart: the stack starts it beside
the one shot that seeds the tenants."""

DATA_SOURCES = {
    "tenant-entities": ("entities", "createTime", "Entities"),
    "tenant-audits": ("entity-audits", "timestamp", "Audit events"),
}
"""Each data source by its uid: the tenant's index family, its time field and its name (TGF-05)."""

DASHBOARDS = ("catalogue", "activity")
"""The dashboards of this package's ``grafana`` folder (TGF-06)."""


class GrafanaError(Exception):
    """A call Grafana refused or did not answer."""


@dataclass(frozen=True)
class Person:
    """A person of a tenant or the platform, as Grafana knows them: login and email."""

    login: str
    email: str


def reader_name(alias: str) -> str:
    """The tenant's store user, ``grafana_<tenant>_reader`` (TGF-05)."""
    return f"grafana_{alias}_reader"


def reader_role(alias: str) -> str:
    """The tenant reader's role in the store."""
    return f"aurelius_atlas_grafana_{alias}"


class GrafanaAdmin:
    """Grafana's HTTP API at ``url``, as its local administrator."""

    def __init__(
        self,
        url: str,
        user: str,
        password: str,
        *,
        http: httpx.AsyncClient,
        sleep: Callable[[float], Any] = asyncio.sleep,
    ) -> None:
        self._url = url.rstrip("/")
        self._auth = (user, password)
        self._http = http
        self._sleep = sleep

    @classmethod
    def http(cls) -> httpx.AsyncClient:
        """The HTTP client for the API."""
        return httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()

    async def call(
        self, method: str, path: str, *, body: object = None, org: int | None = None, missing: bool = False
    ) -> Any:  # noqa: ANN401 - Grafana's JSON
        """The answer's JSON, None for none; ``missing`` takes a 404 for None.

        Raises:
            GrafanaError: For any other answer than 2xx, or no answer after the attempts.
        """
        response = await self._send(method, path, body, {} if org is None else {ORG_HEADER: str(org)})
        if missing and response.status_code == httpx.codes.NOT_FOUND:
            return None
        if not response.is_success:
            msg = f"Grafana refused {method} {path}: {response.status_code} {response.text[:200]}"
            raise GrafanaError(msg)
        return response.json() if response.content else None

    async def _send(self, method: str, path: str, body: object, headers: dict[str, str]) -> httpx.Response:
        """The answer, tried again a second apart while Grafana is not answering yet."""
        for _ in range(CONNECT_ATTEMPTS - 1):
            try:
                return await self._http.request(
                    method, f"{self._url}{path}", json=body, headers=headers, auth=self._auth
                )
            except httpx.TransportError:
                await self._sleep(1)
        try:
            return await self._http.request(method, f"{self._url}{path}", json=body, headers=headers, auth=self._auth)
        except httpx.TransportError as error:
            msg = f"Grafana could not be reached for {method} {path}: {error}"
            raise GrafanaError(msg) from error


class GrafanaTenants:
    """The tenants' Grafana organizations, data sources, dashboards and members, and the store users that read for
    them (TGF-04 to TGF-14); ``store`` is the store's client, ``store_url`` the store as Grafana reaches it.
    """  # noqa: D205 - one sentence

    def __init__(self, grafana: GrafanaAdmin, store: Any, *, store_url: str, ca_pem: str) -> None:  # noqa: ANN401
        self.grafana = grafana
        self._store = store
        self._store_url = store_url
        self._ca_pem = ca_pem

    async def ensure_tenant(self, alias: str) -> int:
        """The tenant's organization, made if missing, with its data sources and dashboards; its id (TGF-04 to
        TGF-06). A data source found keeps its password; one missing, or a reader missing, gets a new one in both.
        """  # noqa: D205 - one sentence
        org = await self._org_id(alias)
        if org is None:
            org = int((await self.grafana.call("POST", "/api/orgs", body={"name": alias}))["orgId"])
        found = {
            uid: await self.grafana.call("GET", f"/api/datasources/uid/{uid}", org=org, missing=True)
            for uid in DATA_SOURCES
        }
        reader = await self._store.options(ignore_status=404).security.get_user(username=reader_name(alias))
        if any(source is None for source in found.values()) or reader_name(alias) not in reader.body:
            password = await self._reader(alias)
            for uid in DATA_SOURCES:
                body = self._data_source(alias, uid, password)
                if found[uid] is None:
                    await self.grafana.call("POST", "/api/datasources", body=body, org=org)
                else:
                    await self.grafana.call("PUT", f"/api/datasources/uid/{uid}", body=body, org=org)
        for name in DASHBOARDS:
            board = json.loads(resources.files("aurelius_atlas_server.grafana").joinpath(f"{name}.json").read_text())
            await self.grafana.call("POST", "/api/dashboards/db", body={"dashboard": board, "overwrite": True}, org=org)
        return org

    async def sync_members(self, org: int, members: Iterable[Person]) -> tuple[int, int]:
        """Make the tenant's members its Viewers and no one else a member, Grafana's administrator aside; a person
        Grafana has not met is made, and lands in the tenant's organization (TGF-07, TGF-08). How many were added
        and removed.
        """  # noqa: D205 - one sentence
        wanted = {person.login: person for person in members}
        current = {user["login"]: user for user in await self.grafana.call("GET", f"/api/orgs/{org}/users")}
        added = 0
        for login, person in wanted.items():
            user_id, made = await self._user(person)
            if login not in current:
                await self.grafana.call("POST", f"/api/orgs/{org}/users", body={"loginOrEmail": login, "role": VIEWER})
                added += 1
            elif current[login]["role"] != VIEWER:
                await self.grafana.call("PATCH", f"/api/orgs/{org}/users/{user_id}", body={"role": VIEWER})
            if made:
                await self.grafana.call("POST", f"/api/users/{user_id}/using/{org}")
        removed = 0
        for login, user in current.items():
            if login not in wanted and login != ADMIN_LOGIN:
                await self.grafana.call("DELETE", f"/api/orgs/{org}/users/{user['userId']}")
                removed += 1
        return added, removed

    async def sync_platform(self, operators: Iterable[Person]) -> None:
        """Make the operators Viewers of the main organization and everyone else a member of it with no role
        (TGF-09).
        """  # noqa: D205 - one sentence
        wanted = {person.login: person for person in operators}
        for person in wanted.values():
            await self._user(person)
        for user in await self.grafana.call("GET", f"/api/orgs/{MAIN_ORG}/users"):
            if user["login"] == ADMIN_LOGIN:
                continue
            role = VIEWER if user["login"] in wanted else NO_ROLE
            if user["role"] != role:
                await self.grafana.call("PATCH", f"/api/orgs/{MAIN_ORG}/users/{user['userId']}", body={"role": role})

    async def remove_tenant(self, alias: str) -> None:
        """Delete the tenant's organization, with its data sources and dashboards, and its store reader (TGF-08)."""
        org = await self._org_id(alias)
        if org is not None:
            await self.grafana.call("DELETE", f"/api/orgs/{org}")
        await self._store.options(ignore_status=404).security.delete_user(username=reader_name(alias))
        await self._store.options(ignore_status=404).security.delete_role(name=reader_role(alias))

    async def cleanup(self, keep: Iterable[str]) -> list[str]:
        """Delete every Grafana user whose login ``keep`` doesn't name, Grafana's administrators aside (TGF-14);
        their logins.
        """  # noqa: D205 - one sentence
        kept = set(keep)
        deleted: list[str] = []
        page = 1
        while True:
            found = await self.grafana.call("GET", f"/api/users/search?perpage=500&page={page}")
            for user in found["users"]:
                if user["login"] == ADMIN_LOGIN or user.get("isAdmin") or user["login"] in kept:
                    continue
                await self.grafana.call("DELETE", f"/api/admin/users/{user['id']}")
                deleted.append(user["login"])
            if page * 500 >= int(found["totalCount"]):
                return deleted
            page += 1

    async def _org_id(self, alias: str) -> int | None:
        found = await self.grafana.call("GET", f"/api/orgs/name/{quote(alias)}", missing=True)
        return None if found is None else int(found["id"])

    async def _user(self, person: Person) -> tuple[int, bool]:
        """The person's Grafana user id, made with no usable password when Grafana has not met them; whether made."""
        found = await self.grafana.call("GET", f"/api/users/lookup?loginOrEmail={quote(person.login)}", missing=True)
        if found is not None:
            return int(found["id"]), False
        made = await self.grafana.call(
            "POST",
            "/api/admin/users",
            body={
                "login": person.login,
                "email": person.email,
                "name": person.login,
                "password": secrets.token_urlsafe(32),
            },
        )
        return int(made["id"]), True

    async def _reader(self, alias: str) -> str:
        """The tenant's store reader, made or given a new password; the password (TGF-05, DD-737)."""
        await self._store.security.put_role(
            name=reader_role(alias),
            cluster=["monitor"],
            indices=[{"names": [f"aurelius-atlas-tenant-{alias}-*"], "privileges": ["read", "view_index_metadata"]}],
        )
        password = secrets.token_urlsafe(24)
        await self._store.security.put_user(
            username=reader_name(alias), password=password, roles=[reader_role(alias)], full_name=f"Grafana, {alias}"
        )
        return password

    def _data_source(self, alias: str, uid: str, password: str) -> Mapping[str, Any]:
        family, time_field, name = DATA_SOURCES[uid]
        return {
            "name": name,
            "uid": uid,
            "type": "elasticsearch",
            "access": "proxy",
            "url": self._store_url,
            "basicAuth": True,
            "basicAuthUser": reader_name(alias),
            "jsonData": {
                "index": f"aurelius-atlas-tenant-{alias}-{family}",
                "timeField": time_field,
                "tlsAuthWithCACert": True,
            },
            "secureJsonData": {"basicAuthPassword": password, "tlsCACert": self._ca_pem},
        }
