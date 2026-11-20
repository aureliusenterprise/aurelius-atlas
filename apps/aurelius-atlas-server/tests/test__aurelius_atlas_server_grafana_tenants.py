"""Grafana per tenant (TGF-04 to TGF-11, TGF-14): the command against the fake store, realm and Grafana.

Apache Atlas has no tenants and no Grafana; the expected results are the spec's.
"""

import json
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings
from aurelius_atlas_server.grafana_tenants import GrafanaAdmin, GrafanaError, GrafanaTenants, reader_name, reader_role
from aurelius_atlas_server.provisioning import NO_GRAFANA, NO_REALM, parser, run
from aurelius_atlas_server.realm_tenants import KeycloakAdmin, RealmTenants
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_store_es.testing.fake import FakeClient
from base_models import base_models
from fake_grafana import ADMIN_PASSWORD, URL, FakeGrafana, FakeStore
from fake_keycloak import CLIENT_ID, CLIENT_SECRET, REALM, SERVER, FakeKeycloak

G = "aurelius_atlas_server.grafana_tenants.GrafanaTenants"
A = "aurelius_atlas_server.grafana_tenants.GrafanaAdmin"
P = "aurelius_atlas_server.provisioning.Provisioner"
STORE_URL = "https://elasticsearch:9200"
REFUSED = "connection refused"
CA = "-----BEGIN CERTIFICATE-----\nstack\n-----END CERTIFICATE-----\n"


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model."""
    return base_models(tmp_path)


class Command:
    """The command against the fake store, realm and Grafana; the lines it wrote."""

    def __init__(
        self, settings: ServerSettings, keycloak: FakeKeycloak, grafana: FakeGrafana, store: FakeStore
    ) -> None:
        self.settings = settings
        self.keycloak = keycloak
        self.grafana = grafana
        self.store = store
        self.lines: list[str] = []

    async def __call__(self, *argv: str) -> list[str]:
        """Run the command; the lines it wrote."""
        self.lines = []

        async def sleep(_seconds: float) -> None:
            return None

        realm = RealmTenants(
            KeycloakAdmin(
                SERVER, REALM, CLIENT_ID, CLIENT_SECRET, http=httpx.AsyncClient(transport=self.keycloak.transport())
            ),
            operator_organization="operators",
            operator_role="atlas-operator",
        )
        admin = GrafanaAdmin(URL, "admin", ADMIN_PASSWORD, http=httpx.AsyncClient(transport=self.grafana.transport()))
        grafana = GrafanaTenants(admin, self.store, store_url=STORE_URL, ca_pem=CA)
        await run(
            parser().parse_args(argv),
            self.settings,
            self.lines.append,
            store=ElasticsearchStore(self.settings.store_settings()),
            realm=realm,
            sleep=sleep,
            user="op",
            grafana=grafana,
        )
        return [line for line in self.lines if line not in {NO_REALM, NO_GRAFANA}]


@pytest.fixture
def keycloak() -> FakeKeycloak:
    """A realm with the operator Ann in ``operators``."""
    fake = FakeKeycloak()
    ann = fake.user("ann", roles=("atlas-operator",))
    fake.users[ann]["email"] = "ann@example.com"
    fake.organization("operators", {ann: ("atlas-read",)})
    return fake


@pytest.fixture
def grafana() -> FakeGrafana:
    """A Grafana with its main organization and its administrator."""
    return FakeGrafana()


@pytest.fixture
def store() -> FakeStore:
    """The store's security API."""
    return FakeStore()


@pytest.fixture
def command(
    settings: ServerSettings, fake_es: FakeClient, keycloak: FakeKeycloak, grafana: FakeGrafana, store: FakeStore
) -> Command:
    """The command, its servers' refresh 0 seconds."""
    _ = fake_es
    return Command(settings.model_copy(update={"tenancy_refresh_seconds": 0}), keycloak, grafana, store)


@pytest.mark.covers(f"{G}.ensure_tenant", f"{P}._grafana_tenant", rules=["TGF-04", "TGF-05", "TGF-06"])
async def test__add_makes_the_tenants_grafana_organization_with_its_data_sources_and_dashboards(
    command: Command, grafana: FakeGrafana, store: FakeStore
) -> None:
    """``add acme``: the organization ``acme``, its two data sources reading acme's indices as acme's reader over
    TLS with the store's CA, and the two dashboards; the reader's role reads acme's indices and the cluster's
    status alone, and its password is in the data sources and nowhere in the command's output.
    """  # noqa: D205 - one sentence
    lines = await command("add", "acme")

    org = grafana.by_name("acme")
    assert org is not None
    assert any(line.startswith(f"Grafana acme: organization {org.id}") for line in lines)
    entities, audits = org.datasources["tenant-entities"], org.datasources["tenant-audits"]
    assert entities["jsonData"]["index"] == "aurelius-atlas-tenant-acme-entities"
    assert (entities["jsonData"]["timeField"], audits["jsonData"]["timeField"]) == ("createTime", "timestamp")
    assert audits["jsonData"]["index"] == "aurelius-atlas-tenant-acme-entity-audits"
    for source in (entities, audits):
        assert (source["url"], source["basicAuthUser"]) == (STORE_URL, reader_name("acme"))
        assert source["secureJsonData"]["tlsCACert"] == CA
        assert source["secureJsonData"]["basicAuthPassword"] == store.security.users[reader_name("acme")]["password"]
    password = store.security.users[reader_name("acme")]["password"]
    assert not any(password in line for line in command.lines)
    role = store.security.roles[reader_role("acme")]
    assert role["cluster"] == ["monitor"]
    assert role["indices"] == [
        {"names": ["aurelius-atlas-tenant-acme-*"], "privileges": ["read", "view_index_metadata"]}
    ]
    assert set(org.dashboards) == {"tenant-catalogue", "tenant-activity"}
    for board in org.dashboards.values():
        assert board["editable"] is False
        uids = {target["datasource"]["uid"] for panel in board["panels"] for target in panel["targets"]}
        assert uids <= set(org.datasources)


@pytest.mark.covers(f"{G}.sync_members", f"{G}._user", rules=["TGF-07", "TGF-09"])
async def test__the_tenants_members_are_its_viewers_and_land_in_it(
    command: Command, grafana: FakeGrafana, keycloak: FakeKeycloak
) -> None:
    """Acme's people, ``acme_atlas`` and the trusted operator Ann, are Viewers of ``acme``; ``acme_atlas``, made
    in Grafana by the command, lands in ``acme`` and has no role in the main organization.
    """  # noqa: D205 - one sentence
    await command("add", "acme")

    assert grafana.roles("acme") == {"admin": "Admin", "acme_atlas": "Viewer", "ann": "Viewer"}
    atlas = next(i for i, u in grafana.users.items() if u["login"] == "acme_atlas")
    assert grafana.users[atlas]["email"] == "acme.atlas@example.com"
    assert grafana.using[atlas] == grafana.by_name("acme").id  # type: ignore[union-attr]
    assert grafana.roles("main")["acme_atlas"] == "None"
    _ = keycloak


@pytest.mark.covers(f"{G}.sync_members", f"{P}.user_add", f"{P}.user_remove", rules=["TGF-07", "TGF-08"])
async def test__a_person_added_or_removed_is_added_or_removed_in_grafana(
    command: Command, grafana: FakeGrafana
) -> None:
    """``user add`` makes jane a Viewer of ``acme``; ``user remove`` takes her out of it again."""
    await command("add", "acme")
    await command("user", "acme", "add", "jane", "--role", "steward")
    assert grafana.roles("acme")["jane"] == "Viewer"

    await command("user", "acme", "remove", "jane")
    assert "jane" not in grafana.roles("acme")


@pytest.mark.covers(f"{G}.remove_tenant", f"{P}.remove", rules=["TGF-08"])
async def test__removing_a_tenant_deletes_its_organization_and_its_reader(
    command: Command, grafana: FakeGrafana, store: FakeStore
) -> None:
    """``remove acme``: no organization ``acme``, no reader, no reader's role."""
    await command("add", "acme")
    await command("remove", "acme")

    assert grafana.by_name("acme") is None
    assert reader_name("acme") not in store.security.users
    assert reader_role("acme") not in store.security.roles


@pytest.mark.covers(f"{G}.sync_platform", f"{P}.grafana_sync", rules=["TGF-09", "TGF-10"])
async def test__grafana_sync_makes_the_operators_viewers_of_the_platform_alone(
    command: Command, grafana: FakeGrafana
) -> None:
    """After ``grafana sync``, Ann is a Viewer of the main organization, ``acme_atlas`` a member of it with no
    role.
    """  # noqa: D205 - one sentence
    await command("add", "acme")
    lines = await command("grafana", "sync")

    roles = grafana.roles("main")
    assert (roles["ann"], roles["acme_atlas"]) == ("Viewer", "None")
    assert lines[-1] == "Grafana: 1 operators in the platform's organization, 0 users deleted"


@pytest.mark.covers(f"{P}.grafana_sync", f"{G}.sync_members", rules=["TGF-10"])
async def test__grafana_sync_catches_up_a_person_added_in_the_console(
    command: Command, grafana: FakeGrafana, keycloak: FakeKeycloak
) -> None:
    """A person put in acme's organization in Keycloak, not by the command, is a Viewer of ``acme`` after
    ``grafana sync``; one taken out there leaves it.
    """  # noqa: D205 - one sentence
    await command("add", "acme")
    org = keycloak.by_alias("acme")
    assert org is not None
    bob = keycloak.user("bob")
    keycloak.users[bob]["email"] = "bob@example.com"
    org.members[bob] = set()

    await command("grafana", "sync")
    assert grafana.roles("acme")["bob"] == "Viewer"

    del org.members[bob]
    await command("grafana", "sync")
    assert "bob" not in grafana.roles("acme")


@pytest.mark.covers(f"{G}.cleanup", f"{P}.grafana_sync", rules=["TGF-14"])
async def test__grafana_sync_deletes_the_people_the_realm_gives_no_tenant(
    command: Command, grafana: FakeGrafana, keycloak: FakeKeycloak
) -> None:
    """After acme is removed, ``grafana sync`` deletes ``acme_atlas`` from Grafana; the operator Ann, a member of
    no tenant, stays; the local administrator stays.
    """  # noqa: D205 - one sentence
    await command("add", "acme")
    await command("remove", "acme")
    lines = await command("grafana", "sync")

    logins = {u["login"] for u in grafana.users.values()}
    assert "acme_atlas" not in logins
    assert {"admin", "ann"} <= logins
    assert lines[-1].endswith("1 users deleted")
    _ = keycloak


@pytest.mark.covers(f"{G}.ensure_tenant", rules=["TGF-04", "TGF-05"])
async def test__a_second_add_keeps_the_readers_password_and_a_lost_reader_gets_a_new_one(
    command: Command, grafana: FakeGrafana, store: FakeStore
) -> None:
    """A re-run finds the data sources and the reader: the password stays. With the reader gone from the store,
    the next run sets a new password in the reader and both data sources.
    """  # noqa: D205 - one sentence
    await command("add", "acme")
    first = store.security.users[reader_name("acme")]["password"]
    await command("add", "acme")
    assert store.security.users[reader_name("acme")]["password"] == first

    del store.security.users[reader_name("acme")]
    await command("grafana", "sync")
    second = store.security.users[reader_name("acme")]["password"]
    assert second != first
    org = grafana.by_name("acme")
    assert org is not None
    assert {s["secureJsonData"]["basicAuthPassword"] for s in org.datasources.values()} == {second}


@pytest.mark.covers(f"{P}._no_grafana", f"{P}.grafana_sync", rules=["TGF-11"])
async def test__without_grafana_the_command_leaves_it_alone_and_says_so_once(
    settings: ServerSettings, fake_es: FakeClient, keycloak: FakeKeycloak
) -> None:
    """No Grafana settings: ``add`` and ``grafana sync`` run their realm and store steps and say once that Grafana
    is left as it is.
    """  # noqa: D205 - one sentence
    _ = fake_es
    lines: list[str] = []
    realm = RealmTenants(
        KeycloakAdmin(SERVER, REALM, CLIENT_ID, CLIENT_SECRET, http=httpx.AsyncClient(transport=keycloak.transport())),
        operator_organization="operators",
        operator_role="atlas-operator",
    )

    async def sleep(_seconds: float) -> None:
        return None

    await run(
        parser().parse_args(["add", "acme"]),
        settings,
        lines.append,
        store=ElasticsearchStore(settings.store_settings()),
        realm=realm,
        sleep=sleep,
        user="op",
    )
    assert lines.count(NO_GRAFANA) == 1


@pytest.mark.covers(f"{G}.ensure_tenant", rules=["TGF-06"])
def test__the_packaged_dashboards_name_the_two_data_sources() -> None:
    """The package's dashboards query the two data sources by uid on their time fields."""
    from importlib import resources  # noqa: PLC0415

    folder = resources.files("aurelius_atlas_server.grafana")
    for name in ("catalogue", "activity"):
        board = json.loads(folder.joinpath(f"{name}.json").read_text())
        assert board["uid"] == f"tenant-{name}"
        for panel in board["panels"]:
            for target in panel["targets"]:
                expected = {"tenant-entities": "createTime", "tenant-audits": "timestamp"}[target["datasource"]["uid"]]
                assert target["timeField"] == expected


@pytest.mark.covers(f"{A}.call", f"{A}._send", f"{A}.http", f"{A}.close")
async def test__a_call_waits_for_grafana_and_names_a_refusal() -> None:
    """A call tried while Grafana is not answering yet is tried again; one Grafana never answers, or refuses, is
    a ``GrafanaError`` naming the call; ``missing`` takes a 404 for nothing.
    """  # noqa: D205 - one sentence
    tries = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal tries
        tries += 1
        if tries < 3:
            raise httpx.ConnectError(REFUSED, request=request)
        return httpx.Response(200 if request.url.path == "/api/org" else 404 if "missing" in request.url.path else 403)

    async def sleep(_seconds: float) -> None:
        return None

    admin = GrafanaAdmin(
        URL, "admin", ADMIN_PASSWORD, http=httpx.AsyncClient(transport=httpx.MockTransport(handle)), sleep=sleep
    )
    assert await admin.call("GET", "/api/org") is None
    assert tries == 3
    assert await admin.call("GET", "/api/missing", missing=True) is None
    with pytest.raises(GrafanaError, match="Grafana refused GET /api/orgs: 403"):
        await admin.call("GET", "/api/orgs")
    await admin.close()

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    gone = GrafanaAdmin(
        URL, "admin", ADMIN_PASSWORD, http=httpx.AsyncClient(transport=httpx.MockTransport(down)), sleep=sleep
    )
    with pytest.raises(GrafanaError, match="could not be reached for GET /api/org"):
        await gone.call("GET", "/api/org")
    await gone.close()
    real = GrafanaAdmin.http()
    await real.aclose()
