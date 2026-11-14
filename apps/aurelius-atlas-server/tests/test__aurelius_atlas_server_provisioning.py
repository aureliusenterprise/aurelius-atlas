"""Tenant provisioning (TPR-01 to TPR-06): ``python -m aurelius_atlas_server.provisioning`` on the fake store.

Apache Atlas has no tenants (ADR 063); the expected results are the spec's.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings
from aurelius_atlas_server.provisioning import ProvisioningError, main, parser, run
from aurelius_atlas_server.tenant_stores import store_aliases, tenant_prefix
from aurelius_atlas_server.tenants import TENANTS_INDEX, TenantState
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_store_es.testing.fake import FakeClient
from base_models import base_models

P = "aurelius_atlas_server.provisioning"
ADMIN = "/api/atlas/admin"
TYPES = {"entityDefs": [{"name": "t_imp", "superTypes": ["Referenceable"], "attributeDefs": []}]}


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model: a sample import records its servers and audit entry (REP-02)."""
    return base_models(tmp_path)


class Command:
    """The command run against the fake store, as the operator ``op``; what it wrote and how long it waited."""

    def __init__(self, settings: ServerSettings) -> None:
        self.settings = settings
        self.lines: list[str] = []
        self.waits: list[float] = []

    async def __call__(self, *argv: str) -> list[str]:
        """Run the command; the lines it wrote."""
        self.lines = []

        async def sleep(seconds: float) -> None:
            self.waits.append(seconds)

        await run(
            parser().parse_args(argv),
            self.settings,
            self.lines.append,
            store=ElasticsearchStore(self.settings.store_settings()),
            sleep=sleep,
            user="op",
        )
        return self.lines


@pytest.fixture
def command(settings: ServerSettings, fake_es: FakeClient) -> Command:
    """The command, its servers' refresh 5 seconds."""
    _ = fake_es
    return Command(settings.model_copy(update={"tenancy_refresh_seconds": 5}))


async def record(fake_es: FakeClient, alias: str) -> dict[str, Any] | None:
    """The tenant's record as the tenants index holds it."""
    stored = fake_es.documents.get(fake_es.aliases.get(TENANTS_INDEX, ""), {}).get(alias)
    return None if stored is None else stored[0]


def alias_indices(fake_es: FakeClient, alias: str) -> list[str]:
    """The indices behind the tenant's aliases."""
    return sorted(fake_es.aliases[name] for name in store_aliases(tenant_prefix(alias)) if name in fake_es.aliases)


async def sample_zip(app_client: httpx.AsyncClient) -> bytes:
    """An export ZIP of one ``t_imp`` entity, made by the default catalogue."""
    assert (await app_client.post("/api/atlas/v2/types/typedefs", json=TYPES)).status_code == 200
    body = {"entity": {"typeName": "t_imp", "attributes": {"qualifiedName": "q"}}}
    guid = (await app_client.post("/api/atlas/v2/entity", json=body)).json()["mutatedEntities"]["CREATE"][0]["guid"]
    return (await app_client.post(f"{ADMIN}/export", json={"itemsToExport": [{"guid": guid}]})).content


@pytest.mark.covers(f"{P}.run", f"{P}.Provisioner.provision", f"{P}.parser", rules=["TPR-01", "TPR-02", "TPR-03"])
async def test__a_tenant_is_provisioned_with_its_indices_models_and_record(
    command: Command, fake_es: FakeClient
) -> None:
    """Every index of its aliases made, Atlas's base model loaded, recorded ``active`` and trusting the operators."""
    assert await command("provision", "acme") == ["Provisioned acme: indices aurelius-atlas-tenant-acme-*, no sample"]
    assert len(alias_indices(fake_es, "acme")) == len(store_aliases(tenant_prefix("acme")))
    typedefs = fake_es.documents[fake_es.aliases[f"{tenant_prefix('acme')}-typedefs"]]
    assert "Referenceable" in str(typedefs)
    stored = await record(fake_es, "acme")
    assert stored is not None
    assert (stored["alias"], stored["state"], stored["trustsOperators"], stored["sample"], stored["updatedBy"]) == (
        "acme",
        "active",
        True,
        None,
        "op",
    )
    await command("provision", "globex", "--no-operator-trust")
    assert (await record(fake_es, "globex") or {})["trustsOperators"] is False


@pytest.mark.covers(f"{P}.Provisioner.provision", f"{P}._read_sample", rules=["TPR-02"])
async def test__a_sample_is_imported_into_the_tenant_alone(
    command: Command, client: httpx.AsyncClient, fake_es: FakeClient, tmp_path: Path
) -> None:
    """The export ZIP's entity lands in the tenant's entities; the record names the sample."""
    sample = tmp_path / "sample_data.zip"
    sample.write_bytes(await sample_zip(client))
    lines = await command("provision", "acme", "--sample", str(sample))
    assert lines == ["Provisioned acme: indices aurelius-atlas-tenant-acme-*, sample sample_data.zip"]
    entities = fake_es.documents[fake_es.aliases[f"{tenant_prefix('acme')}-entities"]]
    assert [document["typeName"] for document, _ in entities.values() if document.get("typeName") == "t_imp"] == [
        "t_imp"
    ]
    assert (await record(fake_es, "acme") or {})["sample"] == "sample_data.zip"
    with pytest.raises(ProvisioningError, match="no export ZIP at"):
        await command("provision", "globex", "--sample", str(tmp_path / "missing.zip"))


@pytest.mark.covers(f"{P}.Provisioner.provision", f"{P}._check_alias", rules=["TPR-02", "TPR-04"])
async def test__provisioning_refuses_bad_and_taken_aliases_and_carries_on_an_interrupted_one(
    command: Command, fake_es: FakeClient, record_tenants: Callable[..., Awaitable[None]]
) -> None:
    """Not index-safe, the operators', ``active`` or ``removing``: refused; ``provisioning``: carried on."""
    for alias, reason in (
        ("Acme", "is no tenant alias"),
        ("acme_x", "is no tenant alias"),
        ("operators", "is the operator organization"),
    ):
        with pytest.raises(ProvisioningError, match=reason):
            await command("provision", alias)
    await command("provision", "acme")
    with pytest.raises(ProvisioningError, match="tenant acme is active"):
        await command("provision", "acme")
    await record_tenants("globex", state=TenantState.PROVISIONING, createdAt=7)
    await record_tenants("initech", state=TenantState.REMOVING)
    with pytest.raises(ProvisioningError, match="tenant initech is removing"):
        await command("provision", "initech")
    await command("provision", "globex")
    stored = await record(fake_es, "globex") or {}
    assert (stored["state"], stored["createdAt"]) == ("active", 7)


@pytest.mark.covers(f"{P}.Provisioner.remove", rules=["TPR-05"])
async def test__removal_deletes_the_tenants_indices_and_record_but_no_other_tenants(
    command: Command, fake_es: FakeClient
) -> None:
    """After the servers' refresh, the indices behind acme's aliases go; acme-corp's, which its prefix matches,
    stay; the operator organization and an unknown alias are refused.
    """  # noqa: D205 - one sentence
    await command("provision", "acme")
    await command("provision", "acme-corp")
    kept = alias_indices(fake_es, "acme-corp")
    removed = alias_indices(fake_es, "acme")
    assert await command("remove", "acme") == [f"Removed acme: {len(removed)} indices deleted"]
    assert command.waits == [5]
    assert alias_indices(fake_es, "acme") == []
    assert not any(name in fake_es.documents for name in removed)
    assert alias_indices(fake_es, "acme-corp") == kept
    assert all(name in fake_es.documents for name in kept)
    assert await record(fake_es, "acme") is None
    with pytest.raises(ProvisioningError, match="operators is the operator organization"):
        await command("remove", "operators")
    with pytest.raises(ProvisioningError, match="no tenant acme is recorded"):
        await command("remove", "acme")


@pytest.mark.covers(f"{P}.Provisioner.trust", f"{P}.Provisioner.list", rules=["TPR-03", "TPR-06"])
async def test__trust_is_changed_and_the_tenants_listed(command: Command) -> None:
    """``trust`` changes the record; ``list`` prints each tenant by alias; an unknown alias is refused."""
    await command("provision", "globex")
    await command("provision", "acme", "--no-operator-trust")
    assert await command("trust", "globex", "off") == ["globex does not trust the operators"]
    assert await command("trust", "acme", "on") == ["acme trusts the operators"]
    assert await command("list") == [
        "acme\tactive\ttrusts operators\t-",
        "globex\tactive\tno operator trust\t-",
    ]
    with pytest.raises(ProvisioningError, match="no tenant initech is recorded"):
        await command("trust", "initech", "on")


@pytest.mark.covers(f"{P}.main", rules=["TPR-06"])
def test__the_command_exits_1_with_the_reason_when_it_refuses(
    monkeypatch: pytest.MonkeyPatch, settings: ServerSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    """A refusal prints the reason on standard error and exits 1; a command done exits 0."""
    monkeypatch.setattr(f"{P}.ServerSettings", lambda: settings)

    async def refused(*_args: object, **_options: object) -> None:
        reason = "tenant acme is active"
        raise ProvisioningError(reason)

    async def done(*_args: object, **_options: object) -> None:
        return None

    monkeypatch.setattr(f"{P}.run", refused)
    assert main(["provision", "acme"]) == 1
    assert capsys.readouterr().err == "python -m aurelius_atlas_server.provisioning: tenant acme is active\n"
    monkeypatch.setattr(f"{P}.run", done)
    assert main(["list"]) == 0
