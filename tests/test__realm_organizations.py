"""Organizations in the realms and the store's operator role (RLM-01, RLM-02, RLM-04 to RLM-08; 15.5a, ADR 063).

The three realm files the repository ships, dev, chart and standalone, read as written; the store's role file in
dev and in the chart's render. A run on Keycloak 26.7.4 checked that they import and issue the claims (DD-580).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import yaml
from conftest import ES_CHART, WORKSPACE, container, helm_render, pod_spec

DEV_REALM = WORKSPACE / "infra/keycloak/import/master.json"
PROD_REALM = WORKSPACE / "infra/keycloak/helm/files/aurelius-atlas.json"
DEMO_REALM = WORKSPACE / "docker/keycloak/aurelius-atlas.json"
ROLES = ["atlas-read", "atlas-write", "atlas-types", "atlas-admin"]
MAPPER = "oidc-organization-group-membership-mapper"
SERVICE_CLIENTS = (
    "aurelius-atlas-db-scanner",
    "aurelius-atlas-kafka-scanner",
    "aurelius-atlas-quality-scanner",
    "aurelius-atlas-validate-entity",
    "aurelius-atlas-admin",
)
OPERATOR_ROLE = {
    "cluster": ["monitor"],
    "indices": [{"names": ["aurelius-atlas-*"], "privileges": ["read", "view_index_metadata", "monitor"]}],
}


def realm(path: Any) -> dict[str, Any]:  # noqa: ANN401 - a path
    """The realm file, parsed."""
    return json.loads(path.read_text())


def client(realm_: dict[str, Any], client_id: str) -> dict[str, Any]:
    """The realm's client by id."""
    return next(c for c in realm_["clients"] if c["clientId"] == client_id)


def organization(realm_: dict[str, Any], alias: str) -> dict[str, Any]:
    """The realm's organization by alias."""
    return next(o for o in realm_["organizations"] if o["alias"] == alias)


def memberships(realm_: dict[str, Any], alias: str) -> dict[str, list[str]]:
    """Each member of the organization with the names of its groups there, in the four roles' order."""
    org = organization(realm_, alias)
    names = {group["id"]: group["name"] for group in org["groups"]}
    return {
        member["username"]: [role for role in ROLES if role in {names[i] for i in member.get("groups", [])}]
        for member in org["members"]
    }


def server_roles(user: dict[str, Any]) -> list[str]:
    """The four roles the user holds as the server client's roles."""
    held = user.get("clientRoles", {}).get("aurelius-atlas-server", [])
    return [role for role in ROLES if role in held]


@pytest.mark.covers(rules=["RLM-01", "RLM-02"])
@pytest.mark.parametrize("path", [DEV_REALM, PROD_REALM, DEMO_REALM], ids=["dev", "chart", "demo"])
def test__each_realm_has_the_operator_organization_its_groups_and_the_mapper(path: Any) -> None:  # noqa: ANN401
    """Organizations on, the operator role, ``operators`` with the four top-level groups, and the server's and the
    webapp's clients writing the organization's groups when the organization scope is asked for.
    """  # noqa: D205 - one sentence
    loaded = realm(path)
    assert loaded["organizationsEnabled"] is True
    assert "atlas-operator" in {role["name"] for role in loaded["roles"]["realm"]}
    operators = organization(loaded, "operators")
    assert (operators["name"], operators["enabled"]) == ("operators", True)
    assert [group["name"] for group in operators["groups"]] == ROLES
    assert all("subGroups" not in group for group in operators["groups"])
    group_ids = [group["id"] for o in loaded["organizations"] for group in o["groups"]]
    assert len(group_ids) == len(set(group_ids))
    for client_id in ("aurelius-atlas-server", "aurelius"):
        found = client(loaded, client_id)
        assert [m["protocolMapper"] for m in found["protocolMappers"] if m["protocolMapper"] == MAPPER] == [MAPPER]
        assert "organization" not in found.get("defaultClientScopes", [])
        assert "organization" in found["optionalClientScopes"]


@pytest.mark.covers(rules=["RLM-01"])
def test__the_realms_group_ids_are_their_own() -> None:
    """No group id is shared between two realms, which one Keycloak may hold together."""
    ids = [
        [group["id"] for o in realm(path)["organizations"] for group in o["groups"]]
        for path in (DEV_REALM, PROD_REALM, DEMO_REALM)
    ]
    assert len({i for realm_ids in ids for i in realm_ids}) == sum(len(realm_ids) for realm_ids in ids)


@pytest.mark.covers(rules=["RLM-04", "RLM-05", "RLM-07"])
def test__in_the_dev_realm_people_and_service_accounts_act_in_the_operator_organization() -> None:
    """Each user with server roles is a member of ``operators`` in the groups of those roles, which it keeps; the
    service clients write the claim by default; the writer is an operator.
    """  # noqa: D205 - one sentence
    loaded = realm(DEV_REALM)
    users = {user["username"]: user for user in loaded["users"]}
    expected = {name: server_roles(user) for name, user in users.items() if server_roles(user)}
    assert memberships(loaded, "operators") == expected
    assert {f"service-account-{c}" for c in SERVICE_CLIENTS} <= set(expected)
    assert {name for name, user in users.items() if "atlas-operator" in user.get("realmRoles", [])} == {
        "aurelius-writer"
    }
    for client_id in SERVICE_CLIENTS:
        found = client(loaded, client_id)
        assert "organization" in found["defaultClientScopes"]
        assert MAPPER in [m["protocolMapper"] for m in found["protocolMappers"]]


@pytest.mark.covers(rules=["RLM-06", "RLM-07"])
def test__the_stack_realm_seeds_no_person_as_the_production_realm_does() -> None:
    """The stack's realm carries the production realm's posture (DD-673): ``operators`` with its four groups
    and no member, and no person anywhere. The tenants' organizations are not seeded either: the one shot of
    the profile tenancy provisions them, as it provisions any tenant a visitor adds.
    """  # noqa: D205 - one sentence
    loaded = realm(DEMO_REALM)
    assert [org["alias"] for org in loaded["organizations"]] == ["operators"]
    assert all(not org.get("members") for org in loaded["organizations"])
    assert [group["name"] for group in organization(loaded, "operators")["groups"]] == ROLES
    assert all(user.get("serviceAccountClientId") for user in loaded["users"])


@pytest.mark.covers(rules=["RLM-07"])
def test__the_production_realm_still_seeds_no_person() -> None:
    """The operator organization has its groups and no member; the realm's only users are the service
    accounts of the provisioning (TRM-11) and admin (DD-666) clients.
    """  # noqa: D205 - one sentence
    loaded = realm(PROD_REALM)
    assert sorted(user["username"] for user in loaded["users"]) == [
        "service-account-aurelius-atlas-admin",
        "service-account-aurelius-atlas-provisioning",
    ]
    assert all(not o.get("members") for o in loaded["organizations"])


@pytest.mark.covers(rules=["RLM-08"])
def test__the_store_defines_the_operators_read_role_in_dev_and_the_chart() -> None:
    """``aurelius_atlas_operator`` reads every catalogue's indices, mounted over the image's roles file."""
    dev = yaml.safe_load((WORKSPACE / "infra/elasticsearch/config/roles.yml").read_text())
    assert dev == {"aurelius_atlas_operator": OPERATOR_ROLE}
    compose = yaml.safe_load((WORKSPACE / "infra/elasticsearch/docker-compose.yaml").read_text())
    volumes = compose["services"]["elasticsearch"]["volumes"]
    assert "./config/roles.yml:/usr/share/elasticsearch/config/roles.yml:ro" in volumes
    docs = helm_render(ES_CHART)
    configmap = next(d for d in docs if d["kind"] == "ConfigMap" and "roles.yml" in d.get("data", {}))
    assert yaml.safe_load(configmap["data"]["roles.yml"]) == dev
    statefulset = next(d for d in docs if d["kind"] == "StatefulSet")
    mounts = {m["name"]: m for m in container(statefulset, "elasticsearch")["volumeMounts"]}
    assert (mounts["chart-roles"]["mountPath"], mounts["chart-roles"]["subPath"]) == (
        "/usr/share/elasticsearch/config/roles.yml",
        "roles.yml",
    )
    volumes_ = {v["name"]: v for v in pod_spec(statefulset)["volumes"]}
    assert volumes_["chart-roles"]["configMap"]["name"] == configmap["metadata"]["name"]


PROVISIONING_ROLES = {
    "manage-organizations",
    "view-organizations",
    "query-organizations",
    "manage-users",
    "view-users",
    "query-users",
    "query-groups",
    "view-clients",
    "manage-realm",
}
"""The realm-management roles the provisioning command needs, no more (DD-600's run on Keycloak 26.7.4)."""


@pytest.mark.covers(rules=["TRM-11"])
@pytest.mark.parametrize(
    ("path", "management"),
    [(DEV_REALM, "master-realm"), (PROD_REALM, "realm-management"), (DEMO_REALM, "realm-management")],
    ids=["dev", "chart", "demo"],
)
def test__each_realm_has_the_provisioning_client_with_the_roles_it_needs(path: Any, management: str) -> None:  # noqa: ANN401
    """Confidential, a service account and no sign-in; its account holds the nine roles on the realm's own
    management client (``master-realm`` in master); fine-grained admin permissions on.
    """  # noqa: D205 - one sentence
    loaded = realm(path)
    assert loaded["adminPermissionsEnabled"] is True
    found = client(loaded, "aurelius-atlas-provisioning")
    assert (found["publicClient"], found["serviceAccountsEnabled"]) == (False, True)
    assert (found["standardFlowEnabled"], found["directAccessGrantsEnabled"], found["implicitFlowEnabled"]) == (
        False,
        False,
        False,
    )
    assert found["secret"] == "${PROVISIONING_CLIENT_SECRET}"  # noqa: S105 - the import's placeholder
    accounts = [user for user in loaded["users"] if user.get("serviceAccountClientId") == found["clientId"]]
    assert [set(account["clientRoles"]) for account in accounts] == [{management}]
    assert set(accounts[0]["clientRoles"][management]) == PROVISIONING_ROLES
