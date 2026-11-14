"""The tenants index and the provisioned tenants the server reads from it (TPR-01, TPR-07 to TPR-09).

Apache Atlas has no tenants (ADR 063); the expected answers are the spec's.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from urllib.parse import parse_qs, urlparse

import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_core.entity_documents import INDEX_PREFIX
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server.tenancy import Tenancy
from aurelius_atlas_server.tenant_stores import tenant_prefix
from aurelius_atlas_server.tenants import TENANTS_INDEX, StoredTenant, TenantDirectory, TenantsIndex, TenantState
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_store_es.testing.fake import FakeClient
from base_models import base_models
from fake_issuer import FakeIssuer
from fastapi import FastAPI

T = "aurelius_atlas_server.tenants"
SESSION = "/api/atlas/admin/session"
EVERY_GROUP = ["/atlas-read", "/atlas-write", "/atlas-types", "/atlas-admin"]

type Record = Callable[..., Awaitable[None]]


def index_of(fake_es: FakeClient) -> TenantsIndex:
    """The tenants index of the fake store."""
    return TenantsIndex(cast("ElasticsearchStore", SimpleNamespace(client=fake_es)))


def member(issuer: FakeIssuer, tenant: str) -> dict[str, str]:
    """The ``Authorization`` header of a token acting in the tenant with every role of its groups."""
    token = issuer.token("ann", atlas_roles=(), organization={tenant: {"groups": EVERY_GROUP}})
    return {"Authorization": f"Bearer {token}"}


async def serve(settings: ServerSettings, **update: object) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    """The started application with the settings updated, and a client without credentials keeping cookies."""
    app = create_app(settings.model_copy(update=update))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas") as client:
            yield app, client


@pytest_asyncio.fixture(loop_scope="function")  # the test's loop, which stops the workers the start began
async def served(settings: ServerSettings, record_tenants: Record) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    """Tenancy on, the index read at every request, acme provisioned before the start."""
    await record_tenants("acme")
    async for both in serve(settings, tenancy_enabled=True, tenancy_refresh_seconds=0):
        yield both


@pytest.mark.covers(
    f"{T}.TenantsIndex.prepare",
    f"{T}.TenantsIndex.get",
    f"{T}.TenantsIndex.put",
    f"{T}.TenantsIndex.list",
    f"{T}.TenantsIndex.delete",
    rules=["TPR-01"],
)
async def test__a_tenants_record_is_written_read_listed_and_deleted(fake_es: FakeClient) -> None:
    """One document per alias, in the index's field names; none listed before the index exists."""
    index = index_of(fake_es)
    assert await index.list() == []
    await index.prepare()
    await index.prepare()
    record = StoredTenant(alias="globex", state=TenantState.ACTIVE, trusts_operators=False, sample="s.zip")
    await index.put(record)
    await index.put(StoredTenant(alias="acme", created_at=1, updated_at=2, updated_by="op"))
    stored = fake_es.documents[fake_es.aliases[TENANTS_INDEX]]["acme"][0]
    assert stored == {
        "alias": "acme",
        "state": "provisioning",
        "trustsOperators": True,
        "sample": None,
        "createdAt": 1,
        "updatedAt": 2,
        "updatedBy": "op",
    }
    assert await index.get("globex") == record
    assert [tenant.alias for tenant in await index.list()] == ["acme", "globex"]
    await index.delete("acme")
    await index.delete("acme")
    assert (await index.get("acme"), [tenant.alias for tenant in await index.list()]) == (None, ["globex"])


@pytest.mark.covers(f"{T}.TenantDirectory.load", f"{T}.TenantDirectory.current", rules=["TPR-07"])
async def test__the_directory_reads_the_active_tenants_when_due(fake_es: FakeClient, record_tenants: Record) -> None:
    """Only ``active`` tenants are provisioned; the index is read again once the interval has passed."""
    now = [0.0]
    await record_tenants("acme")
    await record_tenants("globex", state=TenantState.PROVISIONING)
    await record_tenants("initech", state=TenantState.REMOVING)
    directory = TenantDirectory(Tenancy(), index_of(fake_es), refresh_seconds=30, clock=lambda: now[0])
    assert directory.tenancy.tenants == frozenset()
    assert (await directory.current()).tenants == {"acme"}
    await record_tenants("globex")
    now[0] = 29
    assert (await directory.current()).tenants == {"acme"}
    now[0] = 30
    tenancy = await directory.current()
    assert (tenancy.tenants, tenancy.is_provisioned("operators")) == ({"acme", "globex"}, True)


@pytest.mark.covers(
    "aurelius_atlas_server.authentication.current_tenancy",
    "aurelius_atlas_server.tenant_stores.TenantStoreSets.ensure",
    rules=["TPR-07", "TPR-08"],
)
async def test__a_tenant_provisioned_while_the_server_runs_is_served_from_its_next_read(
    served: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer, record_tenants: Record
) -> None:
    """A tenant recorded ``active`` later is refused until then, and served from a store set opened on demand."""
    app, client = served
    refused = await client.get(SESSION, headers=member(issuer, "globex"))
    assert (refused.status_code, refused.json()["errorCode"]) == (403, "AURELIUS-403-00-003")
    await record_tenants("globex", state=TenantState.PROVISIONING)
    assert (await client.get(SESSION, headers=member(issuer, "globex"))).status_code == 403
    await record_tenants("globex")
    assert tenant_prefix("globex") not in app.state.tenant_stores
    assert (await client.get(SESSION, headers=member(issuer, "globex"))).status_code == 200
    assert tenant_prefix("globex") in app.state.tenant_stores
    assert (await client.get(SESSION, headers=member(issuer, "operators"))).status_code == 200


@pytest.mark.covers(
    "aurelius_atlas_server.tenant_stores.open_request_stores",
    "aurelius_atlas_server.tenant_stores.TenantStoreSets.retain",
    rules=["TPR-07", "TPR-08"],
)
async def test__a_tenant_removed_is_refused_and_its_store_set_closed(
    served: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer, record_tenants: Record
) -> None:
    """Once acme is recorded ``removing``, its token is refused and its store set leaves the open ones."""
    app, client = served
    assert (await client.get(SESSION, headers=member(issuer, "acme"))).status_code == 200
    await record_tenants("acme", state=TenantState.REMOVING)
    refused = await client.get(SESSION, headers=member(issuer, "operators"))
    assert refused.status_code == 200
    assert tenant_prefix("acme") not in app.state.tenant_stores
    assert (await client.get(SESSION, headers=member(issuer, "acme"))).json()["errorCode"] == "AURELIUS-403-00-003"
    assert INDEX_PREFIX in app.state.tenant_stores


@pytest.mark.covers("aurelius_atlas_server.authentication.tenancy_admits", rules=["TPR-07"])
async def test__a_browser_session_of_a_removed_tenant_is_signed_out(
    served: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer, record_tenants: Record
) -> None:
    """A session signed in to acme answers until acme leaves ``active``, then 401 and must sign in again."""
    _, client = served
    issuer.claims_of["ann"] = {"organization": {"acme": {"groups": ["/atlas-read"]}}}
    await client.get("/n/")
    started = await client.get("/login.jsp")
    query = parse_qs(urlparse(started.headers["location"]).query)
    code = issuer.grant_code(query["nonce"][0], "ann")
    assert (await client.get("/login.jsp", params={"code": code, "state": query["state"][0]})).status_code == 302
    assert (await client.get(SESSION)).status_code == 200
    await record_tenants("acme", state=TenantState.REMOVING)
    assert (await client.get(SESSION)).status_code == 401


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["TPR-08"])
async def test__only_the_tenants_opened_at_start_load_the_models(
    settings: ServerSettings, record_tenants: Record, issuer: FakeIssuer, tmp_path: Path
) -> None:
    """Tenant acme, active at start, has Atlas's base model loaded; globex, opened on demand later, keeps what its
    provisioning left: here, nothing.
    """  # noqa: D205 - one sentence
    await record_tenants("acme")
    update = {"models_dir": base_models(tmp_path), "tenancy_enabled": True, "tenancy_refresh_seconds": 0}
    async for app, client in serve(settings, **update):
        await record_tenants("globex")
        assert (await client.get(SESSION, headers=member(issuer, "globex"))).status_code == 200
        registries = {prefix: opened.registry for prefix, opened in app.state.tenant_stores.items()}
        assert registries[tenant_prefix("acme")].entity_type("Referenceable") is not None
        assert registries[tenant_prefix("globex")].entity_type("Referenceable") is None


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["TPR-09"])
async def test__without_tenancy_no_tenants_index_is_made_or_read(
    settings: ServerSettings, fake_es: FakeClient, auth_headers: dict[str, str]
) -> None:
    """The server answers as before, with no tenants index and no directory."""
    async for app, client in serve(settings):
        assert (await client.get(SESSION, headers=auth_headers)).status_code == 200
        assert (app.state.tenant_directory, TENANTS_INDEX in fake_es.aliases) == (None, False)
