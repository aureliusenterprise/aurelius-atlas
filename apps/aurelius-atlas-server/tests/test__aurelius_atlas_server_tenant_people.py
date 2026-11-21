"""Adding a tenant by command (TAD-01 to TAD-11): ``add``, ``user`` and ``samples`` on the fake store and realm.

Apache Atlas has no tenants (ADR 063); the expected results are the spec's. The fake Keycloak makes users with a
``Location``, refuses a taken username and a member already in a group with 409, as Keycloak 26.7 does.
"""

import re
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings
from aurelius_atlas_server.provisioning import NO_GRAFANA, NO_REALM, ProvisioningError, parser, run
from aurelius_atlas_server.realm_tenants import KeycloakAdmin, RealmTenants
from aurelius_atlas_server.tenant_people import Role, temporary_password
from aurelius_atlas_server.tenant_stores import tenant_prefix
from aurelius_atlas_server.tenants import TENANTS_INDEX
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_store_es.testing.fake import FakeClient
from base_models import base_models
from fake_keycloak import CLIENT_ID, CLIENT_SECRET, REALM, SERVER, FakeKeycloak
from test__aurelius_atlas_server_provisioning import sample_zip

P = "aurelius_atlas_server.provisioning.Provisioner"
T = "aurelius_atlas_server.tenant_people"
POLICY = (r"[A-Z]", r"[a-z]", r"\d", r"[^A-Za-z0-9]")


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model: a sample import records its servers and audit entry (REP-02)."""
    return base_models(tmp_path)


class Command:
    """The command against the fake store and realm, with a sample folder; the lines it wrote."""

    def __init__(self, settings: ServerSettings, keycloak: FakeKeycloak) -> None:
        self.settings = settings
        self.keycloak = keycloak
        self.lines: list[str] = []

    async def __call__(self, *argv: str) -> list[str]:
        """Run the command; the lines it wrote."""
        self.lines = []

        async def sleep(_seconds: float) -> None:
            return None

        http = httpx.AsyncClient(transport=self.keycloak.transport())
        realm = RealmTenants(
            KeycloakAdmin(SERVER, REALM, CLIENT_ID, CLIENT_SECRET, http=http),
            operator_organization="operators",
            operator_role="atlas-operator",
        )
        await run(
            parser().parse_args(argv),
            self.settings,
            self.lines.append,
            store=ElasticsearchStore(self.settings.store_settings()),
            realm=realm,
            sleep=sleep,
            user="op",
        )
        return [line for line in self.lines if line not in {NO_REALM, NO_GRAFANA}]


@pytest.fixture
def keycloak() -> FakeKeycloak:
    """A realm with the operator Ann in ``operators``."""
    fake = FakeKeycloak()
    ann = fake.user("ann", roles=("atlas-operator",))
    fake.organization("operators", {ann: ("atlas-read",)})
    return fake


@pytest.fixture
def samples(tmp_path: Path) -> Path:
    """The sample folder: two names, no file there yet that the import reads."""
    folder = tmp_path / "samples"
    folder.mkdir()
    return folder


@pytest.fixture
def command(settings: ServerSettings, fake_es: FakeClient, keycloak: FakeKeycloak, samples: Path) -> Command:
    """The command, its sample folder ``samples``."""
    _ = fake_es
    return Command(settings.model_copy(update={"sample_dir": samples}), keycloak)


def user(keycloak: FakeKeycloak, username: str) -> dict[str, Any]:
    """The fake realm's user of that username."""
    return next(u for u in keycloak.users.values() if u["username"] == username)


def groups_of(keycloak: FakeKeycloak, alias: str, username: str) -> set[str]:
    """The names of the user's groups in the tenant's organization."""
    org = keycloak.by_alias(alias)
    assert org is not None
    names = {group_id: name for name, group_id in org.groups.items()}
    return {names[group_id] for group_id in org.members[user(keycloak, username)["id"]]}


def orgs_of(keycloak: FakeKeycloak, username: str) -> set[str]:
    """The aliases of the organizations the user is a member of."""
    user_id = user(keycloak, username)["id"]
    return {org.alias for org in keycloak.organizations.values() if user_id in org.members}


def printed_password(lines: list[str], username: str) -> str:
    """The temporary password the summary printed for the user."""
    found = re.search(rf"  {username} \(\w+\): made, temporary password (\S+)$", "\n".join(lines), re.MULTILINE)
    assert found is not None, lines
    return found[1]


@pytest.mark.covers(f"{P}.add", f"{P}._summary", f"{T}.ensure_person", rules=["TAD-01", "TAD-03", "TAD-04", "TAD-08"])
async def test__add_makes_the_tenant_and_its_administrator_alone(command: Command, keycloak: FakeKeycloak) -> None:
    """``add acme``: the tenant provisioned, ``acme_atlas`` made in acme alone with all four groups, acme's
    administrator, and the summary naming it with its password.
    """  # noqa: D205 - one sentence
    lines = await command("add", "acme")

    assert "Provisioned acme: indices aurelius-atlas-tenant-acme-*, no sample" in lines
    assert "acme_atlas administers acme" in lines
    assert "Tenant acme: no sample" in lines
    made = user(keycloak, "acme_atlas")
    assert (made["email"], made["firstName"], made["lastName"]) == ("acme.atlas@example.com", "Atlas", "Administrator")
    assert orgs_of(keycloak, "acme_atlas") == {"acme"}
    assert groups_of(keycloak, "acme", "acme_atlas") == {"atlas-read", "atlas-write", "atlas-types", "atlas-admin"}
    assert not any(u["username"] in {"acme_steward", "acme_scientist"} for u in keycloak.users.values())
    printed_password(lines, "acme_atlas")


@pytest.mark.covers(f"{P}.add", f"{T}.temporary_password", rules=["TAD-03", "TAD-05"])
async def test__add_all_makes_the_three_with_temporary_passwords_printed_once(
    command: Command, keycloak: FakeKeycloak
) -> None:
    """``--users all``: the steward and the scientist too, in their groups; each password temporary, meeting the
    realm's policy, the update required, printed in the summary and kept nowhere in the realm's representation
    beyond its credential.
    """  # noqa: D205 - one sentence
    lines = await command("add", "acme", "--users", "all")

    assert groups_of(keycloak, "acme", "acme_steward") == {"atlas-read", "atlas-write"}
    assert groups_of(keycloak, "acme", "acme_scientist") == {"atlas-read"}
    for name in ("acme_atlas", "acme_steward", "acme_scientist"):
        made = user(keycloak, name)
        password = printed_password(lines, name)
        assert made["credentials"] == [{"type": "password", "value": password, "temporary": True}]
        assert made["requiredActions"] == ["UPDATE_PASSWORD"]
        assert len(password) >= 12
        assert all(re.search(pattern, password) for pattern in POLICY), password
        assert sum(password in line for line in lines) == 1
    assert len({printed_password(lines, name) for name in ("acme_atlas", "acme_steward", "acme_scientist")}) == 3


@pytest.mark.covers(f"{T}.temporary_password", rules=["TAD-05"])
def test__every_generated_password_meets_the_realm_s_policy() -> None:
    """A thousand generated passwords: 16 characters, each with an upper, a lower, a digit and a special one."""
    for _ in range(1000):
        password = temporary_password()
        assert len(password) == 16
        assert all(re.search(pattern, password) for pattern in POLICY), password


@pytest.mark.covers(f"{P}.add", f"{P}._sample", rules=["TAD-02", "TAD-08"])
async def test__a_named_sample_is_imported_into_a_new_tenant_and_not_into_an_existing_one(
    command: Command, client: httpx.AsyncClient, fake_es: FakeClient, samples: Path
) -> None:
    """``--sample small`` imports ``small.zip`` into a new tenant; the same command again loads nothing and says
    why.
    """  # noqa: D205 - one sentence
    (samples / "small.zip").write_bytes(await sample_zip(client))

    lines = await command("add", "acme", "--sample", "small")
    assert "Tenant acme: sample small" in lines
    entities = fake_es.documents[fake_es.aliases[f"{tenant_prefix('acme')}-entities"]]
    assert sum(1 for document, _ in entities.values() if document.get("typeName") == "t_imp") == 1
    stored = fake_es.documents[fake_es.aliases[TENANTS_INDEX]]["acme"][0]
    assert stored["sample"] == "small.zip"

    again = await command("add", "acme", "--sample", "small")
    assert "Tenant acme: no sample: acme was provisioned already, so small is not loaded" in again


@pytest.mark.covers(f"{P}.add", f"{P}._sample", f"{P}._sample_names", rules=["TAD-01", "TAD-02"])
async def test__an_unknown_sample_or_a_bad_alias_is_refused_before_anything_is_done(
    command: Command, keycloak: FakeKeycloak, fake_es: FakeClient, samples: Path
) -> None:
    """No tenant record, no organization, no user: the error lists the samples the folder holds."""
    (samples / "small.zip").write_bytes(b"zip")
    (samples / "sample_data.zip").write_bytes(b"zip")

    with pytest.raises(ProvisioningError, match="no sample big: the sample folder holds sample_data, small"):
        await command("add", "acme", "--sample", "big")
    with pytest.raises(ProvisioningError, match="no tenant alias"):
        await command("add", "Not An Alias")
    with pytest.raises(ProvisioningError, match="operator organization"):
        await command("add", "operators")

    assert keycloak.by_alias("acme") is None
    assert {u["username"] for u in keycloak.users.values()} == {"ann"}
    assert "acme" not in fake_es.documents.get(fake_es.aliases.get(TENANTS_INDEX, ""), {})


@pytest.mark.covers(f"{P}.add", f"{T}.ensure_person", rules=["TAD-01", "TAD-06", "TAD-11"])
async def test__a_second_add_makes_only_the_missing_people_and_prints_no_old_password(
    command: Command, keycloak: FakeKeycloak
) -> None:
    """After ``add acme``, ``add acme --users all`` makes the steward and the scientist; ``acme_atlas`` existed,
    keeps its password, and the summary prints none for it. A third run makes nothing and prints no password.
    """  # noqa: D205 - one sentence
    first = await command("add", "acme")
    kept = user(keycloak, "acme_atlas")["credentials"]

    second = await command("add", "acme", "--users", "all")
    assert "  acme_atlas (atlas): existed, password unchanged" in second
    printed_password(second, "acme_steward")
    assert user(keycloak, "acme_atlas")["credentials"] == kept
    assert printed_password(first, "acme_atlas") not in "\n".join(second)

    third = await command("add", "acme", "--users", "all")
    assert not any("temporary password" in line for line in third)
    posts = [call for call in keycloak.calls if call == ("POST", "/users")]
    assert len(posts) == 3


@pytest.mark.covers(f"{P}.user_add", f"{T}.ensure_person", rules=["TAD-07", "TAD-06", "TAD-08"])
async def test__user_add_puts_one_person_in_a_tenant_made_or_found(
    command: Command, keycloak: FakeKeycloak, fake_es: FakeClient
) -> None:
    """A new person made with the given email in the steward's groups, not acme's administrator; an existing one,
    a member of globex already, added to acme too with no password printed.
    """  # noqa: D205 - one sentence
    await command("add", "acme")
    await command("add", "globex")

    lines = await command("user", "acme", "add", "jane", "--role", "steward", "--email", "jane@acme.test")
    assert user(keycloak, "jane")["email"] == "jane@acme.test"
    assert groups_of(keycloak, "acme", "jane") == {"atlas-read", "atlas-write"}
    assert lines[0] == "Tenant acme"
    printed_password(lines, "jane")
    administrators = fake_es.documents[fake_es.aliases[TENANTS_INDEX]]["acme"][0]["administrators"]
    assert user(keycloak, "jane")["id"] not in administrators  # the role grants groups, not administration

    again = await command("user", "acme", "add", "globex_atlas", "--role", "scientist")
    assert "  globex_atlas (scientist): existed, password unchanged" in again
    assert orgs_of(keycloak, "globex_atlas") == {"acme", "globex"}
    assert groups_of(keycloak, "acme", "globex_atlas") == {"atlas-read"}

    lines = await command("user", "acme", "add", "bob")
    assert user(keycloak, "bob")["email"] == "bob@example.com"
    assert groups_of(keycloak, "acme", "bob") == {"atlas-read"}


@pytest.mark.covers(f"{P}.user_add", rules=["TAD-07"])
async def test__user_add_refuses_a_tenant_that_is_not_active(command: Command) -> None:
    """A tenant with no record is refused, and so is one that isn't ``active``."""
    with pytest.raises(ProvisioningError, match="no tenant acme is recorded"):
        await command("user", "acme", "add", "jane")


@pytest.mark.covers(f"{P}.user_remove", rules=["TAD-09"])
async def test__user_remove_takes_a_person_out_of_one_tenant_alone(
    command: Command, keycloak: FakeKeycloak, fake_es: FakeClient
) -> None:
    """``acme_atlas``, acme's administrator and globex's member, is taken out of acme: membership, groups and
    administration; still in the realm and in globex.
    """  # noqa: D205 - one sentence
    await command("add", "acme")
    await command("add", "globex")
    await command("user", "globex", "add", "acme_atlas", "--role", "steward")

    lines = await command("user", "acme", "remove", "acme_atlas")

    assert lines[-1] == "acme_atlas is no longer a member of acme"
    assert "acme_atlas no longer administers acme" in lines
    assert orgs_of(keycloak, "acme_atlas") == {"globex"}
    assert fake_es.documents[fake_es.aliases[TENANTS_INDEX]]["acme"][0]["administrators"] == []


@pytest.mark.covers(f"{P}.samples", f"{P}._sample_names", rules=["TAD-10"])
async def test__samples_lists_the_sample_folder_s_names(command: Command, samples: Path) -> None:
    """One name per line, sorted, without ``.zip``; a folder of no ZIP lists none."""
    assert await command("samples") == []
    for name in ("small.zip", "sample_data.zip", "only_gov_quality.zip", "notes.txt"):
        (samples / name).write_bytes(b"x")

    assert await command("samples") == ["only_gov_quality", "sample_data", "small"]


@pytest.mark.covers(f"{P}.add", f"{P}._people_realm", rules=["TAD-11"])
async def test__a_failed_step_stops_and_the_same_command_finishes_the_rest(
    command: Command, keycloak: FakeKeycloak
) -> None:
    """The realm refusing the steward's creation stops ``add`` after the administrator was made; the same command
    again, once the realm takes it, makes the steward and the scientist, the administrator found as it was.
    """  # noqa: D205 - one sentence
    original = keycloak._route  # noqa: SLF001 - the fake's router; refusing one user

    def refusing(method: str, path: str, query: dict[str, str], body: Any) -> httpx.Response:  # noqa: ANN401
        if method == "POST" and path == "/users" and body["username"] == "acme_steward":
            return httpx.Response(400, json={"error": "invalidPasswordMinSpecialCharsMessage"})
        return original(method, path, query, body)

    keycloak._route = refusing  # noqa: SLF001
    with pytest.raises(ProvisioningError, match="refused POST /users"):
        await command("add", "acme", "--users", "all")
    assert {u["username"] for u in keycloak.users.values()} == {"ann", "acme_atlas"}

    keycloak._route = original  # noqa: SLF001
    lines = await command("add", "acme", "--users", "all")
    assert "  acme_atlas (atlas): existed, password unchanged" in lines
    printed_password(lines, "acme_steward")
    printed_password(lines, "acme_scientist")


@pytest.mark.covers(f"{P}._people_realm", rules=["TAD-01", "TAD-07"])
async def test__people_need_the_realm(settings: ServerSettings, fake_es: FakeClient) -> None:
    """Without the provisioning client's secret, ``add`` and ``user`` refuse before anything is done."""
    _ = fake_es
    for argv in (["add", "acme"], ["user", "acme", "add", "jane"]):
        args = parser().parse_args(argv)
        with pytest.raises(ProvisioningError, match="people are kept in the realm"):
            await run(args, settings, lambda _line: None, user="op")


@pytest.mark.covers(f"{T}.standard_username", f"{T}.standard_email", rules=["TAD-04"])
def test__the_standard_names() -> None:
    """``<tenant>_<role>`` and ``<tenant>.<role>@example.com``."""
    from aurelius_atlas_server.tenant_people import standard_email, standard_username  # noqa: PLC0415

    assert standard_username("acme", Role.STEWARD) == "acme_steward"
    assert standard_email("acme", Role.SCIENTIST) == "acme.scientist@example.com"
