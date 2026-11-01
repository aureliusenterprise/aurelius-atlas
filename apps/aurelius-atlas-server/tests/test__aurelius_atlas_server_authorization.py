"""Authorization (AUZ-01 to AUZ-06): the roles of the server's client grant Atlas's privileges.

Read from Atlas 2.4.0's ``AtlasPrivilege``, ``AtlasAuthorizationUtils``, ``AtlasSimpleAuthorizer`` and the checks of
its type-definition stores, ``AtlasEntityStoreV2#purgeByIds`` and ``AdminResource#getUserProfile``.
"""

from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_server.authentication import User
from aurelius_atlas_server.authorization import ROLE_PRIVILEGES, AtlasPrivilege, privileges
from fake_issuer import FakeIssuer

A = "aurelius_atlas_server.authorization"
T = "aurelius_atlas_server.routes.types"
TYPES = "/api/atlas/v2/types"
DEFINITIONS: dict[str, Any] = {
    "enumDefs": [{"name": "e_auth", "elementDefs": [{"value": "A", "ordinal": 0}]}],
    "entityDefs": [{"name": "t_auth", "superTypes": [], "attributeDefs": []}],
}


def as_roles(issuer: FakeIssuer, user: str, *roles: str) -> dict[str, str]:
    """The ``Authorization`` header of a token of the user holding these roles of the server's client."""
    return {"Authorization": f"Bearer {issuer.token(user, atlas_roles=roles)}"}


def refusal(response: httpx.Response) -> tuple[int, str, str]:
    """The status, error code and message of a refused request."""
    body = response.json()
    return response.status_code, body["errorCode"], body["errorMessage"]


@pytest.mark.covers(f"{A}.privileges", rules=["AUZ-01", "AUZ-02"])
def test__each_role_grants_its_privileges_only() -> None:
    """The four roles' privileges; an unknown role, no role or no user grant none."""
    reader = privileges(User("r", roles=frozenset({"atlas-read", "another-role"})))
    assert reader == {AtlasPrivilege.TYPE_READ, AtlasPrivilege.ENTITY_READ, AtlasPrivilege.ENTITY_READ_CLASSIFICATION}
    assert AtlasPrivilege.TYPE_READ in ROLE_PRIVILEGES["atlas-types"]
    assert AtlasPrivilege.ADMIN_PURGE in ROLE_PRIVILEGES["atlas-admin"]
    assert AtlasPrivilege.SERVICE_NOTIFICATION_POST not in privileges(User("a", roles=frozenset(ROLE_PRIVILEGES)))
    assert (privileges(User("n")), privileges(None)) == (frozenset(), frozenset())


@pytest.mark.covers(
    f"{A}.verify_access",
    f"{A}.is_access_allowed",
    f"{T}.create_typedefs",
    f"{T}.update_typedefs",
    f"{T}.delete_typedefs",
    f"{T}.delete_typedef_by_name",
    rules=["AUZ-03", "AUZ-04"],
)
async def test__type_definitions_change_with_the_types_role(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """Without ``atlas-types`` each change is refused, the first definition of the stores' order named."""
    reader = as_roles(issuer, "reader", "atlas-read")
    typer = as_roles(issuer, "typer", "atlas-types")
    assert refusal(await client.post(f"{TYPES}/typedefs", json=DEFINITIONS, headers=reader)) == (
        403,
        "ATLAS-403-00-001",
        "reader is not authorized to perform create enum-def e_auth",
    )
    assert (await client.post(f"{TYPES}/typedefs", json=DEFINITIONS, headers=typer)).status_code == 200
    update = {"entityDefs": [{**DEFINITIONS["entityDefs"][0], "description": "changed"}]}
    assert refusal(await client.put(f"{TYPES}/typedefs", json=update, headers=reader))[2] == (
        "reader is not authorized to perform update entity-def t_auth"
    )
    assert (await client.put(f"{TYPES}/typedefs", json=update, headers=typer)).status_code == 200
    assert refusal(await client.delete(f"{TYPES}/typedef/name/t_auth", headers=reader))[2] == (
        "reader is not authorized to perform delete entity-def t_auth"
    )
    assert refusal(await client.request("DELETE", f"{TYPES}/typedefs", json=DEFINITIONS, headers=reader))[2] == (
        "reader is not authorized to perform delete enum-def e_auth"
    )
    assert (await client.delete(f"{TYPES}/typedef/name/t_auth", headers=typer)).status_code == 204
    assert (await client.delete(f"{TYPES}/typedef/name/missing", headers=reader)).status_code == 404


@pytest.mark.covers(
    f"{T}.get_typedef_by_name", f"{T}.get_typedef_by_guid", f"{T}.kind_by_name", f"{T}.kind_by_guid", rules=["AUZ-04"]
)
async def test__one_definition_is_read_with_type_read(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """``read type <name or GUID>`` needs ``TYPE_READ``; the lists and headers need nothing; a missing one is 404."""
    created = (await client.post(f"{TYPES}/typedefs", json=DEFINITIONS)).json()
    guid = created["entityDefs"][0]["guid"]
    nobody = as_roles(issuer, "nobody")
    for url, action in (
        (f"{TYPES}/typedef/name/t_auth", "read type t_auth"),
        (f"{TYPES}/typedef/guid/{guid}", f"read type {guid}"),
        (f"{TYPES}/entitydef/name/t_auth", "read type t_auth"),
        (f"{TYPES}/entitydef/guid/{guid}", f"read type {guid}"),
    ):
        assert refusal(await client.get(url, headers=nobody))[2] == f"nobody is not authorized to perform {action}"
        assert (await client.get(url, headers=as_roles(issuer, "reader", "atlas-read"))).status_code == 200
    assert (await client.get(f"{TYPES}/typedefs/headers", headers=nobody)).status_code == 200
    assert (await client.get(f"{TYPES}/typedefs", headers=nobody)).status_code == 200
    assert (await client.get(f"{TYPES}/typedef/name/missing", headers=nobody)).status_code == 404


@pytest.mark.covers("aurelius_atlas_server.routes.admin.purge_by_ids", rules=["AUZ-05"])
async def test__purging_needs_the_admin_role(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """``purge entity: guids=[...]`` needs ``ADMIN_PURGE``; an empty list fails first, as Atlas checks it first."""
    writer = as_roles(issuer, "writer", "atlas-read", "atlas-write")
    assert refusal(await client.put("/api/atlas/admin/purge", json=["g1", "g2"], headers=writer))[2] == (
        "writer is not authorized to perform purge entity: guids=[g1, g2]"
    )
    assert (await client.put("/api/atlas/admin/purge", json=[], headers=writer)).status_code == 400
    admin = as_roles(issuer, "admin", "atlas-admin")
    assert (await client.put("/api/atlas/admin/purge", json=["g1"], headers=admin)).status_code == 200


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_session", rules=["AUZ-06"])
async def test__the_session_reports_the_entity_permissions(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """Create and update are allowed with ``atlas-write``, not without."""

    async def allowed(*roles: str) -> tuple[bool, bool]:
        session = (await client.get("/api/atlas/admin/session", headers=as_roles(issuer, "u", *roles))).json()
        return session["atlas.entity.create.allowed"], session["atlas.entity.update.allowed"]

    assert await allowed("atlas-write") == (True, True)
    assert await allowed("atlas-read", "atlas-types", "atlas-admin") == (False, False)
