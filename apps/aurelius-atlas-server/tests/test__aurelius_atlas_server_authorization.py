"""Authorization (AUZ-01 to AUZ-14): the roles of the server's client grant Atlas's privileges.

Read from Atlas 2.4.0's ``AtlasPrivilege``, ``AtlasAuthorizationUtils``, ``AtlasSimpleAuthorizer`` and the checks of
its type-definition stores, ``AtlasEntityStoreV2#purgeByIds`` and ``AdminResource#getUserProfile``.
"""

import shutil
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_server.authentication import User
from aurelius_atlas_server.authorization import ROLE_PRIVILEGES, AtlasPrivilege, privileges
from fake_issuer import FakeIssuer

A = "aurelius_atlas_server.authorization"
T = "aurelius_atlas_server.routes.types"
TYPES = "/api/atlas/v2/types"
MODELS = (Path("0000-Area0") / "0010-base_model.json", Path("0000-Area0") / "0011-glossary_model.json")
DEFINITIONS: dict[str, Any] = {
    "enumDefs": [{"name": "e_auth", "elementDefs": [{"value": "A", "ordinal": 0}]}],
    "entityDefs": [{"name": "t_auth", "superTypes": [], "attributeDefs": []}],
}


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base and glossary models alone (MDL-16): ``Asset``, the glossary and the user profile."""
    directory = tmp_path / "core-models"
    for model in MODELS:
        (directory / model.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy(BUILTIN_MODELS_DIR / model, directory / model)
    return directory


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
    f"{T}.get_typedef_by_name",
    f"{T}.get_typedef_by_guid",
    f"{T}.kind_by_name",
    f"{T}.kind_by_guid",
    f"{T}.get_all_typedefs",
    f"{T}.get_typedef_headers",
    rules=["AUZ-04", "AUZ-14"],
)
async def test__one_definition_is_read_with_type_read(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """``read type <name or GUID>`` needs ``TYPE_READ``; the lists and headers leave out what it does not read."""
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
    assert (await client.get(f"{TYPES}/typedefs/headers", headers=nobody)).json() == []
    assert (await client.get(f"{TYPES}/typedefs", headers=nobody)).json() == (
        await client.get(f"{TYPES}/typedefs?type=nothing")
    ).json()
    reader = as_roles(issuer, "reader", "atlas-read")
    headers = (await client.get(f"{TYPES}/typedefs/headers", headers=reader)).json()
    assert {"t_auth", "e_auth"} <= {header["name"] for header in headers}
    assert (await client.get(f"{TYPES}/typedef/name/missing", headers=nobody)).status_code == 404


@pytest.mark.covers("aurelius_atlas_server.routes.admin.purge_by_ids", rules=["AUZ-05"])
async def test__purging_needs_the_admin_role(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """``purge entity: guids=[...]`` needs ``ADMIN_PURGE``; an empty list fails first, as Atlas checks it first."""
    g1, g2 = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"
    writer = as_roles(issuer, "writer", "atlas-read", "atlas-write")
    assert refusal(await client.put("/api/atlas/admin/purge", json=[g1, g2], headers=writer))[2] == (
        f"writer is not authorized to perform purge entity: guids=[{g1}, {g2}]"
    )
    assert (await client.put("/api/atlas/admin/purge", json=[], headers=writer)).status_code == 400
    admin = as_roles(issuer, "admin", "atlas-admin")
    assert (await client.put("/api/atlas/admin/purge", json=[g1], headers=admin)).status_code == 200


@pytest.mark.covers("aurelius_atlas_server.routes.admin.get_session", rules=["AUZ-06"])
async def test__the_session_reports_the_entity_permissions(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """Create and update are allowed with ``atlas-write``, not without."""

    async def allowed(*roles: str) -> tuple[bool, bool]:
        session = (await client.get("/api/atlas/admin/session", headers=as_roles(issuer, "u", *roles))).json()
        return session["atlas.entity.create.allowed"], session["atlas.entity.update.allowed"]

    assert await allowed("atlas-write") == (True, True)
    assert await allowed("atlas-read", "atlas-types", "atlas-admin") == (False, False)


ENTITY = "/api/atlas/v2/entity"
ASSET = {"typeName": "Asset", "attributes": {"qualifiedName": "a@auz", "name": "a"}}


async def asset(client: httpx.AsyncClient) -> str:
    """The GUID of a new ``Asset``, created as ``admin``, who holds every role."""
    created = (await client.post(ENTITY, json={"entity": ASSET})).json()
    return str(created["mutatedEntities"]["CREATE"][0]["guid"])


@pytest.mark.covers(
    "aurelius_atlas_server.routes.entity.get_by_id",
    "aurelius_atlas_server.routes.entity.get_header_by_id",
    "aurelius_atlas_server.routes.entity.get_by_unique_attributes",
    "aurelius_atlas_server.routes.entity.get_entity_header_by_unique_attributes",
    "aurelius_atlas_server.routes.entity.get_entities_by_unique_attributes",
    "aurelius_atlas_server.routes.entity.get_by_guids",
    "aurelius_atlas_server.routes.entity.get_audit_events",
    f"{A}.authorizer",
    rules=["AUZ-11"],
)
async def test__entities_are_read_with_entity_read(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """Each read is refused without ``atlas-read``, once the entity is found; a missing one is 404 first."""
    guid = await asset(client)
    nobody, reader = as_roles(issuer, "nobody"), as_roles(issuer, "reader", "atlas-read")
    unique = "typeName=Asset, uniqueAttributes={qualifiedName=a@auz}"
    for url, action in (
        (f"{ENTITY}/guid/{guid}", f"read entity: guid={guid}"),
        (f"{ENTITY}/guid/{guid}/header", f"read entity: guid={guid}"),
        (f"{ENTITY}/uniqueAttribute/type/Asset?attr:qualifiedName=a@auz", f"read entity: {unique}"),
        (f"{ENTITY}/uniqueAttribute/type/Asset/header?attr:qualifiedName=a@auz", f"read entity: {unique}"),
        (
            f"{ENTITY}/bulk/uniqueAttribute/type/Asset?attr_0:qualifiedName=a@auz",
            f"read entity: typeName=Asset, guid={guid}",
        ),
        (f"{ENTITY}/bulk?guid={guid}", f"read entity: guid={guid}"),
        (f"{ENTITY}/{guid}/audit", f"read entity: guid={guid}"),
    ):
        assert refusal(await client.get(url, headers=nobody))[2] == f"nobody is not authorized to perform {action}"
        assert (await client.get(url, headers=reader)).status_code == 200
    absent = "99999999-9999-4999-8999-999999999999"
    assert (await client.get(f"{ENTITY}/guid/{absent}", headers=nobody)).status_code == 404
    assert (await client.get(f"{ENTITY}/guid/missing", headers=nobody)).status_code == 400  # no GUID text (DV-161)
    assert (await client.delete(f"{ENTITY}/guid/{guid}")).status_code == 200
    assert (await client.put("/api/atlas/admin/purge", json=[guid])).status_code == 200
    assert refusal(await client.get(f"{ENTITY}/{guid}/audit", headers=nobody))[2] == (
        f"nobody is not authorized to perform read entity audit: guid={guid}"
    )


@pytest.mark.covers(
    "aurelius_atlas_server.routes.entity.writer",
    "aurelius_atlas_server.routes.entity.updater",
    "aurelius_atlas_server.routes.entity.classifications",
    "aurelius_atlas_server.routes.relationship.relationships",
    "aurelius_atlas_server.routes.glossary._service",
    rules=["AUZ-07", "AUZ-08", "AUZ-10"],
)
async def test__a_reader_changes_nothing(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """``atlas-read`` reads entities and their classifications; creating, deleting and saving are refused."""
    guid = await asset(client)
    reader = as_roles(issuer, "reader", "atlas-read")

    other = {"entity": {**ASSET, "attributes": {"qualifiedName": "b@auz", "name": "b"}}}
    assert refusal(await client.post(ENTITY, json=other, headers=reader)) == (
        403,
        "ATLAS-403-00-001",
        "reader is not authorized to perform create entity: type=Asset",
    )
    assert refusal(await client.delete(f"{ENTITY}/guid/{guid}", headers=reader))[2] == (
        f"reader is not authorized to perform delete entity: guid={guid}"
    )
    assert refusal(await client.post("/api/atlas/v2/glossary", json={"name": "g"}, headers=reader))[2] == (
        "reader is not authorized to perform create entity: type=AtlasGlossary"
    )
    saved = {"name": "s", "searchParameters": {"typeName": "Asset"}}
    assert refusal(await client.post("/api/atlas/v2/search/saved", json=saved, headers=reader))[2] == (
        "reader is not authorized to perform create entity: type=__AtlasUserProfile"
    )
    assert (await client.get(f"{ENTITY}/guid/{guid}/classifications", headers=reader)).status_code == 200
    gone = await client.delete("/api/atlas/v2/relationship/guid/99999999-9999-4999-8999-999999999999", headers=reader)
    assert gone.status_code == 404


@pytest.mark.covers(
    "aurelius_atlas_server.routes.discovery.search_using_basic",
    "aurelius_atlas_server.routes.discovery.quick_search_using_query",
    "aurelius_atlas_server.routes.lineage.lineage_service",
    rules=["AUZ-12", "AUZ-13"],
)
async def test__a_user_without_read_finds_scrubbed_entities_and_no_lineage(
    client: httpx.AsyncClient, issuer: FakeIssuer
) -> None:
    """Search answers headers scrubbed of GUID and attributes; lineage is refused once the entity is found."""
    guid = await asset(client)
    nobody, reader = as_roles(issuer, "nobody"), as_roles(issuer, "reader", "atlas-read")
    for url, path in (
        ("/api/atlas/v2/search/basic?typeName=Asset", ("entities",)),
        ("/api/atlas/v2/search/quick?typeName=Asset", ("searchResults", "entities")),
    ):
        hidden, shown = (await client.get(url, headers=nobody)).json(), (await client.get(url, headers=reader)).json()
        for key in path:
            hidden, shown = hidden[key], shown[key]
        assert [(header["guid"], header["attributes"]) for header in hidden] == [("-1", {})]
        assert [header["guid"] for header in shown] == [guid]
    assert refusal(await client.get(f"/api/atlas/v2/lineage/{guid}", headers=nobody)) == (
        403,
        "ATLAS-403-00-001",
        f"nobody is not authorized to perform read entity lineage: guid={guid}",
    )
    assert (await client.get(f"/api/atlas/v2/lineage/{guid}", headers=reader)).json()["errorCode"] == "ATLAS-404-00-011"
    assert (await client.get("/api/atlas/v2/lineage/missing", headers=nobody)).status_code == 404
