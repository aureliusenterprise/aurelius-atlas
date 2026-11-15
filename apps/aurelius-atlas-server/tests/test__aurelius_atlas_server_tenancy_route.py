"""``GET /api/aurelius/v1/tenancy`` (TNW-01, TNW-09): whether the server serves tenants, without a user.

Apache Atlas has no tenants (ADR 063); the expected answers are the spec's.
"""

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient

PATH = "/api/aurelius/v1/tenancy"


async def answer(settings: ServerSettings) -> httpx.Response:
    """The started server's answer to a request without credentials."""
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas") as client:
            return await client.get(PATH)


@pytest.mark.usefixtures("fake_es")
@pytest.mark.covers("aurelius_atlas_server.routes.tenancy.tenancy", rules=["TNW-01", "TNW-09"])
async def test__the_tenancy_is_answered_without_a_user(settings: ServerSettings, fake_es: FakeClient) -> None:
    """Off: only that it is off. On: the operator organization and role, as the server reads tokens."""
    _ = fake_es
    off = await answer(settings)
    assert (off.status_code, off.json()) == (200, {"enabled": False})
    on = await answer(
        settings.model_copy(
            update={"tenancy_enabled": True, "tenancy_operator_organization": "ops", "tenancy_operator_role": "op"}
        )
    )
    assert (on.status_code, on.json()) == (200, {"enabled": True, "operatorOrganization": "ops", "operatorRole": "op"})
