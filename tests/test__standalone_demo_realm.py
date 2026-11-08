"""The standalone stack's demo realm (DMO-01..03, 9.5b).

The realm file and the compose file are read as written: the clients and their roles against the server's
``ROLE_PRIVILEGES``, each user's roles, the password placeholders, and the stack's wiring to the realm.
"""

import json
import re
from typing import Any

import pytest
import yaml
from aurelius_atlas_server.authorization import ROLE_PRIVILEGES
from conftest import WORKSPACE

STANDALONE = WORKSPACE / "apps/aurelius-atlas-server/standalone"
SERVER_CLIENT = "aurelius-atlas-server"
PLACEHOLDER = re.compile(r"^\$\{[A-Z_]+\}$")


@pytest.fixture(scope="module")
def realm() -> dict[str, Any]:
    """The realm file the stack's Keycloak imports."""
    return json.loads((STANDALONE / "keycloak/demo.json").read_text())


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services."""
    return yaml.safe_load((STANDALONE / "docker-compose.yaml").read_text())["services"]


def _client(realm: dict[str, Any], client_id: str) -> dict[str, Any]:
    return next(client for client in realm["clients"] if client["clientId"] == client_id)


@pytest.mark.covers(rules=["DMO-01"])
def test__demo_realm_holds_the_server_client_and_its_roles(realm: dict[str, Any]) -> None:
    """The server's client holds the server's four roles; the public client's tokens carry them (DMO-01)."""
    assert realm["realm"] == "demo"
    roles = {role["name"] for role in realm["roles"]["client"][SERVER_CLIENT]}
    assert roles == set(ROLE_PRIVILEGES)
    server = _client(realm, SERVER_CLIENT)
    assert not server["publicClient"]
    assert PLACEHOLDER.match(server["secret"])
    assert server["redirectUris"] == ["https://localhost:9000/atlas2/login.jsp"]
    assert server["attributes"]["post.logout.redirect.uris"] == "https://localhost:9000/atlas2/"
    public = _client(realm, "aurelius")
    assert public["publicClient"]
    assert public["directAccessGrantsEnabled"]
    mapped = realm["clientScopeMappings"][SERVER_CLIENT]
    assert mapped == [{"client": "aurelius", "roles": sorted(roles, key=list(ROLE_PRIVILEGES).index)}]


@pytest.mark.covers(rules=["DMO-02"])
def test__demo_users_hold_all_write_and_read_rights(realm: dict[str, Any]) -> None:
    """`atlas` holds every role, `steward` read and write, `scientist` read; passwords are placeholders (DMO-02)."""
    users = {user["username"]: user for user in realm["users"]}
    roles = {name: set(user["clientRoles"][SERVER_CLIENT]) for name, user in users.items()}
    assert roles == {
        "atlas": set(ROLE_PRIVILEGES),
        "steward": {"atlas-read", "atlas-write"},
        "scientist": {"atlas-read"},
    }
    for user in users.values():
        assert [credential["type"] for credential in user["credentials"]] == ["password"]
        assert PLACEHOLDER.match(user["credentials"][0]["value"])


@pytest.mark.covers(rules=["DMO-03"])
def test__stack_signs_in_to_demo_alone(services: dict[str, Any], realm: dict[str, Any]) -> None:
    """Keycloak imports `demo` alone with its placeholders; the server and the sample import use it (DMO-03)."""
    keycloak = services["keycloak"]
    assert "./keycloak:/opt/keycloak/data/import:ro" in keycloak["volumes"]
    assert sorted(path.name for path in (STANDALONE / "keycloak").iterdir()) == ["demo.json"]
    placeholders = {credential["value"][2:-1] for user in realm["users"] for credential in user["credentials"]} | {
        _client(realm, SERVER_CLIENT)["secret"][2:-1]
    }
    assert placeholders <= set(keycloak["environment"])
    assert services["aurelius-atlas-server"]["environment"]["AURELIUS_ATLAS_SERVER_AUTH_REALM"] == "demo"
    sample = services["sample-import"]["environment"]
    assert sample["TOKEN_URL"] == "https://localhost:9000/auth/realms/demo/protocol/openid-connect/token"  # noqa: S105 - a URL
    assert sample["ATLAS_USERNAME"] == "atlas"
    assert sample["ATLAS_PASSWORD"] == "${DEMO_USER_ATLAS_PASSWORD:-}"  # noqa: S105 - a placeholder
