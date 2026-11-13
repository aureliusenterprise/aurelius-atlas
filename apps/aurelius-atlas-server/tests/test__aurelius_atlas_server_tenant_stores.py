"""Tenant-scoped stores (TSS-01 to TSS-08): each tenant's own indices and type registry, read by its requests.

Apache Atlas has no tenants (ADR 063); the expected answers are the spec's. Tokens come from the fake identity
provider (``fake_issuer``), with the organization claim Keycloak's Organization Group Membership mapper writes.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from types import SimpleNamespace
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_core.entity_documents import INDEX_PREFIX
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server.tenancy import Tenancy
from aurelius_atlas_server.tenant_stores import index_prefix, store_aliases, stores
from aurelius_atlas_server.tenants import TENANTS_INDEX
from aurelius_atlas_store_es.testing.fake import FakeClient
from fake_issuer import FakeIssuer
from fastapi import FastAPI

S = "aurelius_atlas_server.tenant_stores"
EVERY_GROUP = ["/atlas-read", "/atlas-write", "/atlas-types", "/atlas-admin"]
TYPEDEFS = "/api/atlas/v2/types/typedefs"
TYPEDEF = "/api/atlas/v2/types/typedef/name"
ENTITY = "/api/atlas/v2/entity"
DEFINITIONS: dict[str, Any] = {"entityDefs": [{"name": "t_acme", "superTypes": [], "attributeDefs": []}]}
TENANCY = Tenancy(tenants=frozenset({"acme", "globex"}))


@pytest.fixture
async def served(
    settings: ServerSettings, record_tenants: Callable[..., Awaitable[None]]
) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    """The started application with tenancy on, acme and globex provisioned, and a client without credentials."""
    await record_tenants("acme", "globex")
    app = create_app(settings.model_copy(update={"tenancy_enabled": True}))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://aurelius-atlas") as client:
            yield app, client


def member(issuer: FakeIssuer, tenant: str) -> dict[str, str]:
    """The ``Authorization`` header of a token acting in the tenant with every role of its groups."""
    token = issuer.token("ann", atlas_roles=(), organization={tenant: {"groups": EVERY_GROUP}})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.covers(f"{S}.index_prefix", f"{S}.tenant_prefix", rules=["TSS-01", "TSS-02", "TSS-03"])
def test__a_tenants_indices_carry_its_alias_and_the_operators_keep_the_default() -> None:
    """No tenancy, no tenant and the operator organization: the default prefix; another tenant: its own."""
    assert index_prefix("acme", None) == index_prefix(None, TENANCY) == INDEX_PREFIX == "aurelius-atlas"
    assert index_prefix("operators", TENANCY) == "aurelius-atlas"
    assert index_prefix("acme", TENANCY) == "aurelius-atlas-tenant-acme"


@pytest.mark.covers(f"{S}.open_stores", f"{S}.load_models", f"{S}.store_aliases", rules=["TSS-03", "TSS-04", "TPR-05"])
async def test__each_provisioned_tenant_gets_every_default_index_at_start(
    served: tuple[FastAPI, httpx.AsyncClient], fake_es: FakeClient
) -> None:
    """Every alias of the default store set, and the index behind it, exists under each tenant's prefix alone."""
    app, _ = served
    default = {
        alias: index
        for alias, index in fake_es.aliases.items()
        if f"{INDEX_PREFIX}-tenant-" not in alias and alias != TENANTS_INDEX
    }
    assert sorted(default) == sorted(store_aliases(INDEX_PREFIX))  # removal knows every index (DD-574)
    for tenant in ("acme", "globex"):
        tenant_prefix = f"{INDEX_PREFIX}-tenant-{tenant}"
        for alias, index in default.items():
            assert fake_es.aliases[alias.replace(INDEX_PREFIX, tenant_prefix, 1)] == index.replace(
                INDEX_PREFIX, tenant_prefix, 1
            )
    assert fake_es.matching(f"{INDEX_PREFIX}-tenant-initech-*") == []
    assert sorted(app.state.tenant_stores) == [
        INDEX_PREFIX,
        f"{INDEX_PREFIX}-tenant-acme",
        f"{INDEX_PREFIX}-tenant-globex",
    ]


@pytest.mark.covers(f"{S}.stores", rules=["TSS-05", "TSS-06"])
async def test__a_tenants_types_and_entities_are_its_own(
    served: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """A type and an entity made in acme are found there alone: not in globex, nor in the operator organization."""
    app, client = served
    acme, globex, operators = (member(issuer, tenant) for tenant in ("acme", "globex", "operators"))
    assert (await client.post(TYPEDEFS, json=DEFINITIONS, headers=acme)).status_code == 200
    created = await client.post(ENTITY, json={"entity": {"typeName": "t_acme", "attributes": {}}}, headers=acme)
    assert created.status_code == 200
    guid = next(iter(created.json()["guidAssignments"].values()))
    assert (await client.get(f"{TYPEDEF}/t_acme", headers=acme)).status_code == 200
    assert (await client.get(f"{ENTITY}/guid/{guid}", headers=acme)).status_code == 200
    for elsewhere in (globex, operators):
        assert (await client.get(f"{TYPEDEF}/t_acme", headers=elsewhere)).status_code == 404
        assert (await client.get(f"{ENTITY}/guid/{guid}", headers=elsewhere)).status_code == 404
    registries = {prefix: opened.registry for prefix, opened in app.state.tenant_stores.items()}
    assert registries[f"{INDEX_PREFIX}-tenant-acme"].entity_type("t_acme") is not None
    assert registries[f"{INDEX_PREFIX}-tenant-globex"].entity_type("t_acme") is None
    assert registries[INDEX_PREFIX].entity_type("t_acme") is None


@pytest.mark.covers(f"{S}.stores", rules=["TSS-06"])
async def test__the_audits_and_metrics_of_a_request_are_its_tenants(
    served: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """An entity's audits are read in its tenant; the entity counts of the metrics are each tenant's own."""
    _, client = served
    acme, globex = member(issuer, "acme"), member(issuer, "globex")
    await client.post(TYPEDEFS, json=DEFINITIONS, headers=acme)
    created = await client.post(ENTITY, json={"entity": {"typeName": "t_acme", "attributes": {}}}, headers=acme)
    guid = next(iter(created.json()["guidAssignments"].values()))
    audits = await client.get(f"{ENTITY}/{guid}/audit", headers=acme)
    assert [event["action"] for event in audits.json()] == ["ENTITY_CREATE"]
    assert (await client.get(f"{ENTITY}/{guid}/audit", headers=globex)).status_code == 404

    async def active(headers: dict[str, str]) -> int:
        metrics = (await client.get("/api/atlas/admin/metrics", headers=headers)).json()
        return metrics["data"]["entity"]["entityActive"].get("t_acme", 0)

    assert (await active(acme), await active(globex)) == (1, 0)


@pytest.mark.covers(f"{S}.stores", rules=["TSS-06"])
async def test__the_request_store_set_follows_its_tenant(served: tuple[FastAPI, httpx.AsyncClient]) -> None:
    """No tenant and the operator organization read the default store set; a tenant its own; one not open fails."""
    app, _ = served
    opened = app.state.tenant_stores

    def request(tenant: str | None) -> Any:  # noqa: ANN401 - a request's stand-in
        return SimpleNamespace(state=SimpleNamespace(tenant=tenant), app=app)

    assert stores(request(None)) is stores(request("operators")) is opened[INDEX_PREFIX]
    assert stores(request("acme")) is opened[f"{INDEX_PREFIX}-tenant-acme"]
    assert stores(request("acme")).documents is not stores(request("globex")).documents
    with pytest.raises(LookupError, match="no store set is open for tenant initech"):
        stores(request("initech"))


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["TSS-07", "TSS-08"])
async def test__the_workers_and_the_deployments_state_stay_on_the_default(
    served: tuple[FastAPI, httpx.AsyncClient], issuer: FakeIssuer
) -> None:
    """The workers' stores are the default set's; readiness answers alike in every tenant."""
    app, client = served
    default = app.state.tenant_stores[INDEX_PREFIX]
    assert (app.state.entity_store, app.state.entity_documents, app.state.type_registry) == (
        default.entity_store,
        default.documents,
        default.registry,
    )
    for tenant in ("acme", "operators"):
        ready = await client.get("/api/atlas/admin/readiness", headers=member(issuer, tenant))
        assert ready.status_code == 200
