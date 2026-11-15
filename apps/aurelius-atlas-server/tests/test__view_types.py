"""The form-slice door ``GET /api/aurelius/v1/types/for-type/{name}`` (AVW-11).

One read answers the whole type chain an editor needs for one type: the named type and each supertype
with the attributes each declares (DD-593). The chain is deepest on an m4i type, so that is what the
first test asks for; the sample types cover the answers without the m4i models loaded.
"""

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_core.testing.entity_samples import SAMPLE_TYPES
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient
from base_models import base_models
from fake_issuer import FakeIssuer

F = "aurelius_atlas_server.routes.view_types.for_type"
FOR_TYPE = "/api/aurelius/v1/types/for-type"
TYPES = "/api/atlas/v2/types"


def as_roles(issuer: FakeIssuer, user: str, *roles: str) -> dict[str, str]:
    """The ``Authorization`` header of a token of the user holding these roles of the server's client."""
    return {"Authorization": f"Bearer {issuer.token(user, atlas_roles=roles)}"}


@contextlib.asynccontextmanager
async def m4i_server(settings: ServerSettings, headers: dict[str, str]) -> AsyncIterator[httpx.AsyncClient]:
    """A client of a server started with the m4i types on, over the fixture's base model."""
    app = create_app(settings.model_copy(update={"m4i_models_enabled": True}))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas", headers=headers) as client:
            yield client


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model: the types the m4i types extend (MDL-16)."""
    return base_models(tmp_path)


@pytest.mark.covers(F, rules=["AVW-11"])
async def test__the_answer_carries_the_whole_type_chain_of_an_m4i_type(
    settings: ServerSettings, auth_headers: dict[str, str], fake_es: FakeClient
) -> None:
    """The named type first, every supertype whole after it: enough to build one form (AVW-11)."""
    _ = fake_es
    async with m4i_server(settings, auth_headers) as client:
        answer = await client.get(f"{FOR_TYPE}/m4i_dataset")

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert set(body) == {"type", "superTypes"}
    assert body["type"]["category"] == "ENTITY"
    assert body["type"]["name"] == "m4i_dataset"
    names = [typedef["name"] for typedef in body["superTypes"]]
    assert names == ["DataSet", "m4i_referenceable", "Referenceable", "Asset"] or set(
        body["type"]["superTypes"]
    ) <= set(names)
    for typedef in [body["type"], *body["superTypes"]]:
        assert "attributeDefs" in typedef


@pytest.mark.covers(F, rules=["AVW-11"])
async def test__a_sample_type_chains_the_attributes_each_declares(client: httpx.AsyncClient) -> None:
    """Each supertype's own attributes ride its own typedef: the union a form is built from."""
    created = await client.post(TYPES + "/typedefs", json=SAMPLE_TYPES)
    assert created.status_code == 200, created.text

    answer = await client.get(f"{FOR_TYPE}/s_table")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert [typedef["name"] for typedef in body["superTypes"]] == ["s_ref"]
    own = {str(a["name"]) for a in body["type"]["attributeDefs"]}
    supertype = {str(a["name"]) for a in body["superTypes"][0]["attributeDefs"]}
    assert "created" in own
    assert "name" in supertype
    assert own & supertype == set()


@pytest.mark.covers(F, rules=["AVW-11"])
async def test__an_unknown_type_is_answered_the_types_404(client: httpx.AsyncClient) -> None:
    """No type carries the name: the same 404 the Atlas type endpoints answer (AVW-11)."""
    answer = await client.get(f"{FOR_TYPE}/no_such_type")

    assert answer.status_code == 404
    assert answer.json()["errorCode"] == "ATLAS-404-00-001"


@pytest.mark.covers(F, rules=["AVW-11"])
async def test__a_relationship_type_is_answered_the_same_404(client: httpx.AsyncClient) -> None:
    """The editor only asks for entity types: a relationship type has no form (AVW-11)."""
    created = await client.post(TYPES + "/typedefs", json=SAMPLE_TYPES)
    assert created.status_code == 200, created.text

    answer = await client.get(f"{FOR_TYPE}/s_table_home")

    assert answer.status_code == 404
    assert answer.json()["errorCode"] == "ATLAS-404-00-001"


@pytest.mark.covers(F, rules=["AVW-11"])
async def test__the_door_needs_type_read(
    client: httpx.AsyncClient, issuer: FakeIssuer, auth_headers: dict[str, str]
) -> None:
    """A reader may ask (TYPE_READ rides atlas-read); a roleless token may not (AVW-11)."""
    _ = auth_headers
    created = await client.post(TYPES + "/typedefs", json=SAMPLE_TYPES)
    assert created.status_code == 200, created.text

    reader = httpx.AsyncClient(
        transport=client._transport,  # noqa: SLF001 - the same app, another token
        base_url="https://aurelius-atlas",
        headers=as_roles(issuer, "reader", "atlas-read"),
    )
    allowed = await reader.get(f"{FOR_TYPE}/s_table")
    refused = await client.get(
        f"{FOR_TYPE}/s_table", headers={"Authorization": f"Bearer {issuer.token('nobody', atlas_roles=())}"}
    )

    assert allowed.status_code == 200
    assert refused.status_code == 403
    assert refused.json()["errorCode"] == "ATLAS-403-00-001"
    answer: dict[str, Any] = allowed.json()
    assert answer["type"]["name"] == "s_table"
