"""The acting user on writes (USR-01 to USR-03): the user a request authenticates as names what it writes.

Read from Atlas 2.4.0's ``RequestContext#getUser``, which the stores stamp as ``createdBy`` and ``updatedBy``
and the audit listener records, against the fake identity provider (``fake_issuer``).
"""

from types import SimpleNamespace
from typing import Any, cast

import httpx2 as httpx
import pytest
from aurelius_atlas_server.authentication import User, acting_user
from fake_issuer import FakeIssuer
from fastapi import Request

TYPES = "/api/atlas/v2/types/typedefs"
ENTITY = "/api/atlas/v2/entity"


def as_user(issuer: FakeIssuer, name: str) -> dict[str, str]:
    """The ``Authorization`` header of a token of the user."""
    return {"Authorization": f"Bearer {issuer.token(name)}"}


@pytest.mark.covers("aurelius_atlas_server.authentication.acting_user", rules=["USR-01"])
def test__the_acting_user_is_the_authenticated_users_name() -> None:
    """The name of the request's user; none for a request without one, as on an open path."""

    def request(user: User | None) -> Request:
        return cast("Request", SimpleNamespace(state=SimpleNamespace(user=user)))

    assert acting_user(request(User("ann", ("g",)))) == "ann"
    assert acting_user(request(None)) is None
    assert acting_user(cast("Request", SimpleNamespace(state=SimpleNamespace()))) is None


@pytest.mark.covers(
    "aurelius_atlas_server.routes.types.create_typedefs",
    "aurelius_atlas_server.routes.types.update_typedefs",
    rules=["USR-02"],
)
async def test__a_type_names_who_created_and_last_updated_it(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """``createdBy`` is the creator, ``updatedBy`` the last updater."""
    definition: dict[str, Any] = {"entityDefs": [{"name": "t_users", "superTypes": [], "attributeDefs": []}]}
    created = await client.post(TYPES, json=definition, headers=as_user(issuer, "reader"))
    entity_def = created.json()["entityDefs"][0]
    assert (entity_def["createdBy"], entity_def["updatedBy"]) == ("reader", "reader")
    definition["entityDefs"][0]["description"] = "changed"
    updated = await client.put(TYPES, json=definition, headers=as_user(issuer, "ann"))
    entity_def = updated.json()["entityDefs"][0]
    assert (entity_def["createdBy"], entity_def["updatedBy"]) == ("reader", "ann")


@pytest.mark.covers(
    "aurelius_atlas_server.routes.entity.create_or_update",
    "aurelius_atlas_server.routes.entity.writer",
    rules=["USR-03"],
)
async def test__an_entity_and_its_audit_name_the_user(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """``createdBy``, ``updatedBy`` and each audit event's ``user`` are the users who wrote."""
    await client.post(
        TYPES,
        json={
            "entityDefs": [
                {"name": "t_audited", "superTypes": [], "attributeDefs": [{"name": "name", "typeName": "string"}]}
            ]
        },
    )
    body = {"entity": {"typeName": "t_audited", "attributes": {"name": "a"}}}
    created = await client.post(ENTITY, json=body, headers=as_user(issuer, "reader"))
    guid = created.json()["mutatedEntities"]["CREATE"][0]["guid"]
    body["entity"]["guid"] = guid
    body["entity"]["attributes"]["name"] = "b"
    await client.post(ENTITY, json=body, headers=as_user(issuer, "ann"))
    entity = (await client.get(f"{ENTITY}/guid/{guid}")).json()["entity"]
    assert (entity["createdBy"], entity["updatedBy"]) == ("reader", "ann")
    events = (await client.get(f"{ENTITY}/{guid}/audit")).json()
    assert sorted((event["action"], event["user"]) for event in events) == [
        ("ENTITY_CREATE", "reader"),
        ("ENTITY_UPDATE", "ann"),
    ]
    await client.delete(f"{ENTITY}/guid/{guid}", headers=as_user(issuer, "carl"))
    deleted = (await client.get(f"{ENTITY}/{guid}/audit", params={"auditAction": "ENTITY_DELETE"})).json()
    assert [event["user"] for event in deleted] == ["carl"]
