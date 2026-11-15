"""The tenants in the realm (TRM-02 to TRM-10): the provisioning command against a fake of Keycloak's admin API.

Apache Atlas has no tenants (ADR 063); the expected answers are the spec's, and the fake answers as Keycloak 26.7.4
did (DD-600 to DD-602).
"""

from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings
from aurelius_atlas_server.provisioning import ProvisioningError, parser, run
from aurelius_atlas_server.realm_tenants import (
    PAGE,
    KeycloakAdmin,
    RealmTenants,
    administrators_policy,
    permission_names,
)
from aurelius_atlas_server.tenants import TENANTS_INDEX, TenantState
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_store_es.testing.fake import FakeClient
from fake_keycloak import CLIENT_ID, CLIENT_SECRET, REALM, SERVER, FakeKeycloak, Organization

R = "aurelius_atlas_server.realm_tenants.RealmTenants"
P = "aurelius_atlas_server.provisioning.Provisioner"


class Realm:
    """Ann the operator, a scanner's service account and Ted in the operator organization; Ted isn't an operator."""

    def __init__(self) -> None:
        self.keycloak = FakeKeycloak()
        self.ann = self.keycloak.user("ann", roles=("atlas-operator",))
        self.scanner = self.keycloak.user("service-account-scanner")
        self.ted = self.keycloak.user("ted")
        self.bob = self.keycloak.user("bob")
        self.tadmin = self.keycloak.user("tadmin")
        self.keycloak.organization(
            "operators", {self.ann: ("atlas-read", "atlas-admin"), self.scanner: ("atlas-read",), self.ted: ()}
        )

    def tenants(self) -> RealmTenants:
        """The realm's tenants over a fresh connection, as the command closes its own."""
        http = httpx.AsyncClient(transport=self.keycloak.transport())
        admin = KeycloakAdmin(SERVER, REALM, CLIENT_ID, CLIENT_SECRET, http=http)
        return RealmTenants(admin, operator_organization="operators", operator_role="atlas-operator")

    def org(self, alias: str) -> Organization:
        """The tenant's organization; it must exist."""
        found = self.keycloak.by_alias(alias)
        assert found is not None
        return found

    def groups_of(self, alias: str, user: str) -> set[str]:
        """The names of the user's groups in the organization."""
        org = self.org(alias)
        names = {group_id: name for name, group_id in org.groups.items()}
        return {names[group_id] for group_id in org.members[user]}


@pytest.fixture
def realm() -> Realm:
    """The fake realm."""
    return Realm()


@pytest.fixture
def command(settings: ServerSettings, fake_es: FakeClient, realm: Realm) -> Any:  # noqa: ANN401 - the runner
    """The command against the fake store and realm; the lines it wrote."""
    _ = fake_es

    async def call(*argv: str) -> list[str]:
        lines: list[str] = []

        async def sleep(_seconds: float) -> None:
            return None

        await run(
            parser().parse_args(argv),
            settings,
            lines.append,
            store=ElasticsearchStore(settings.store_settings()),
            realm=realm.tenants(),
            sleep=sleep,
            user="op",
        )
        return lines

    return call


def record(fake_es: FakeClient, alias: str) -> dict[str, Any]:
    """The tenant's record as the tenants index holds it."""
    return fake_es.documents[fake_es.aliases[TENANTS_INDEX]][alias][0]


@pytest.mark.covers(
    f"{R}.ensure_organization",
    f"{R}.in_step",
    f"{R}.operators",
    f"{R}.add_member",
    f"{R}.add_to_read_group",
    f"{P}.provision",
    rules=["TRM-02", "TRM-03"],
)
async def test__a_provisioned_tenant_has_its_organization_groups_and_operators(
    command: Any,  # noqa: ANN401
    realm: Realm,
    fake_es: FakeClient,
) -> None:
    """The organization with the four groups; Ann, the operator, in atlas-read alone; the service account and
    Ted, who hold no operator role, left out; the record lists Ann; a second run changes nothing.
    """  # noqa: D205 - one sentence
    lines = await command("provision", "acme")
    acme = realm.org("acme")
    assert (acme.name, sorted(acme.groups)) == ("acme", ["atlas-admin", "atlas-read", "atlas-types", "atlas-write"])
    assert set(acme.members) == {realm.ann}
    assert realm.groups_of("acme", realm.ann) == {"atlas-read"}
    assert (record(fake_es, "acme")["state"], record(fake_es, "acme")["operatorMembers"]) == ("active", [realm.ann])
    assert lines[0] == "Realm acme: 1 operators added, 0 removed"
    posts = len([call for call in realm.keycloak.calls if call[0] == "POST"])
    assert await command("provision", "acme", "--existing-ok") == ["acme is already provisioned"]
    assert len([call for call in realm.keycloak.calls if call[0] == "POST"]) == posts
    assert realm.keycloak.tokens == 2


@pytest.mark.covers(f"{R}.organization", f"{R}.ensure_organization", rules=["TRM-02", "TRM-03"])
async def test__an_organization_made_by_hand_is_completed_and_its_own_operator_left_alone(
    command: Any,  # noqa: ANN401
    realm: Realm,
    fake_es: FakeClient,
) -> None:
    """Found by alias though named otherwise, its missing group made; Ann, its own member, keeps her groups."""
    made = realm.keycloak.organization("acme", {realm.ann: ("atlas-write",)}, name="ACME Corp")
    del made.groups["atlas-types"]
    await command("provision", "acme")
    assert realm.keycloak.by_alias("acme") is made
    assert sorted(made.groups) == ["atlas-admin", "atlas-read", "atlas-types", "atlas-write"]
    assert realm.groups_of("acme", realm.ann) == {"atlas-write"}
    assert record(fake_es, "acme")["operatorMembers"] == []


@pytest.mark.covers(f"{P}.trust", f"{R}.remove_member", rules=["TRM-04"])
async def test__trust_off_and_on_removes_and_adds_only_the_operators_trust_added(
    command: Any,  # noqa: ANN401
    realm: Realm,
    fake_es: FakeClient,
) -> None:
    """Off: Ann leaves, Bob, the tenant's own member, stays; on: Ann is back in atlas-read."""
    await command("provision", "acme")
    realm.org("acme").members[realm.bob] = set()
    assert await command("trust", "acme", "off") == [
        "Realm acme: 0 operators added, 1 removed",
        "acme does not trust the operators",
    ]
    assert set(realm.org("acme").members) == {realm.bob}
    assert record(fake_es, "acme")["operatorMembers"] == []
    await command("trust", "acme", "on")
    assert set(realm.org("acme").members) == {realm.bob, realm.ann}
    assert realm.groups_of("acme", realm.ann) == {"atlas-read"}


@pytest.mark.covers(f"{P}.operators", rules=["TRM-05"])
async def test__operators_keeps_every_trusting_tenant_in_step(
    command: Any,  # noqa: ANN401
    realm: Realm,
    fake_es: FakeClient,
) -> None:
    """Carl becomes an operator and joins acme, not globex, which doesn't trust them; Ann stops being one and
    leaves acme; each active tenant is reported.
    """  # noqa: D205 - one sentence
    await command("provision", "acme")
    await command("provision", "globex", "--no-operator-trust")
    carl = realm.keycloak.user("carl", roles=("atlas-operator",))
    realm.org("operators").members[carl] = set()
    realm.keycloak.users[realm.ann]["roles"] = set()
    assert await command("operators") == [
        "Realm acme: 1 operators added, 1 removed",
        "Realm globex: 0 operators added, 0 removed",
    ]
    assert set(realm.org("acme").members) == {carl}
    assert realm.org("globex").members == {}
    assert record(fake_es, "acme")["operatorMembers"] == [carl]


@pytest.mark.covers(f"{R}.operators", f"{R}.members", rules=["TRM-05"])
async def test__operators_are_read_across_every_page_of_members(realm: Realm) -> None:
    """An operator organization of more members than a page still yields its operators."""
    for index in range(PAGE + 5):
        realm.org("operators").members[realm.keycloak.user(f"member-{index}")] = set()
    late = realm.keycloak.user("late", roles=("atlas-operator",))
    realm.org("operators").members[late] = set()
    tenants = realm.tenants()
    assert await tenants.operators() == {realm.ann, late}
    await tenants.admin.close()


@pytest.mark.covers(f"{P}.admin", f"{R}.grant", f"{R}.user_id", rules=["TRM-06", "TRM-07", "TRM-08"])
async def test__a_tenants_administrators_are_granted_its_organization_groups_and_own_members(
    command: Any,  # noqa: ANN401
    realm: Realm,
    fake_es: FakeClient,
) -> None:
    """Tadmin's policy over acme, its four groups, and Bob, but not Ann, whom trust added; removed, nothing is
    left; an unknown user is refused.
    """  # noqa: D205 - one sentence
    keycloak = realm.keycloak
    await command("provision", "acme", "--admin", "tadmin")
    on_org, on_groups, on_members = permission_names("acme")
    policy = keycloak.named("policy", administrators_policy("acme"))
    assert policy is not None
    assert policy["users"] == [realm.tadmin]
    assert keycloak.named("permission", on_members) is None  # Ann alone is a member, added by trust (TRM-08)
    granted = keycloak.named("permission", on_org)
    assert granted is not None
    assert (granted["resourceType"], granted["resources"], granted["scopes"]) == (
        "Organizations",
        [realm.org("acme").id],
        ["view", "manage"],
    )
    groups = keycloak.named("permission", on_groups)
    assert groups is not None
    assert sorted(groups["resources"]) == sorted(realm.org("acme").groups.values())
    realm.org("acme").members[realm.bob] = set()
    assert await command("operators") == ["Realm acme: 0 operators added, 0 removed"]
    members = keycloak.named("permission", on_members)
    assert members is not None
    assert (members["resources"], members["scopes"]) == ([realm.bob], ["view", "manage-group-membership"])
    assert record(fake_es, "acme")["administrators"] == [realm.tadmin]
    assert await command("admin", "acme", "remove", "tadmin") == ["tadmin no longer administers acme"]
    assert (keycloak.policies, keycloak.permissions) == ({}, {})
    with pytest.raises(ProvisioningError, match="the realm has no user nobody"):
        await command("admin", "acme", "add", "nobody")


@pytest.mark.covers(f"{P}.remove", f"{R}.delete", rules=["TRM-09"])
async def test__removal_deletes_the_organization_and_the_administrators_rights(
    command: Any,  # noqa: ANN401
    realm: Realm,
    fake_es: FakeClient,
) -> None:
    """The organization, its policy and every permission go; globex's stay; the record goes last."""
    await command("provision", "acme", "--admin", "tadmin")
    await command("provision", "globex", "--admin", "tadmin")
    realm.org("acme").members[realm.bob] = set()
    await command("operators")
    lines = await command("remove", "acme")
    assert lines[-1].startswith("Removed acme:")
    assert realm.keycloak.by_alias("acme") is None
    left = [*realm.keycloak.policies.values(), *realm.keycloak.permissions.values()]
    assert all("acme" not in item["name"] for item in left)
    assert realm.keycloak.named("policy", administrators_policy("globex")) is not None
    assert "acme" not in fake_es.documents[fake_es.aliases[TENANTS_INDEX]]


@pytest.mark.covers(f"{R}.in_step", "aurelius_atlas_server.realm_tenants.KeycloakAdmin.call", rules=["TRM-10"])
async def test__a_refused_call_fails_the_command_and_a_second_run_carries_on(
    command: Any,  # noqa: ANN401
    realm: Realm,
    fake_es: FakeClient,
) -> None:
    """Ann joined but her group was refused: the command fails with Keycloak's answer, the tenant stays
    ``provisioning`` and lists her; once the realm admits it, the next run puts her in atlas-read.
    """  # noqa: D205 - one sentence
    realm.keycloak.refuse[("PUT", "/organizations/")] = 403
    with pytest.raises(ProvisioningError, match=r"the realm refused PUT /organizations/.*: 403"):
        await command("provision", "acme")
    assert (record(fake_es, "acme")["state"], record(fake_es, "acme")["operatorMembers"]) == (
        TenantState.PROVISIONING.value,
        [realm.ann],
    )
    assert realm.groups_of("acme", realm.ann) == set()
    realm.keycloak.refuse.clear()
    await command("provision", "acme")
    assert realm.groups_of("acme", realm.ann) == {"atlas-read"}
    assert record(fake_es, "acme")["state"] == "active"


@pytest.mark.covers("aurelius_atlas_server.realm_tenants.KeycloakAdmin.call", rules=["TRM-10"])
async def test__a_realm_that_refuses_the_client_or_cannot_be_reached_fails_the_command(
    settings: ServerSettings,
    fake_es: FakeClient,
) -> None:
    """A wrong secret and a failed connection both fail with the reason."""
    _ = fake_es
    keycloak = FakeKeycloak()

    def unreachable(_request: httpx.Request) -> httpx.Response:
        msg = "refused"
        raise httpx.ConnectError(msg)

    for http, reason in (
        (httpx.AsyncClient(transport=keycloak.transport()), "refused the client aurelius-atlas-provisioning a token"),
        (httpx.AsyncClient(transport=httpx.MockTransport(unreachable)), "could not be reached for a token"),
    ):
        admin = KeycloakAdmin(SERVER, REALM, CLIENT_ID, "wrong", http=http)
        tenants = RealmTenants(admin, operator_organization="operators", operator_role="atlas-operator")
        with pytest.raises(ProvisioningError, match=reason):
            await run(
                parser().parse_args(["provision", "acme"]),
                settings,
                print,
                store=ElasticsearchStore(settings.store_settings()),
                realm=tenants,
            )
