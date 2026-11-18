"""The standalone stack's realm `aurelius-atlas` (DMO-01 to DMO-03, 9.5b, DD-641; DD-673; IRT-06, ADR 066).

The realm file and the compose file are read as written: the clients and their roles against the server's
``ROLE_PRIVILEGES``, the service identities, and the stack's wiring to the realm. The realm carries the Helm
production realm's posture (DD-673): the same name and the same service identities, and no default user. The
stack's Keycloak is the infra slice's service extended (DD-670), so the suite proves the production topology
it inherits.
"""

import json
import re
from typing import Any

import pytest
import yaml
from aurelius_atlas_server.authorization import ROLE_PRIVILEGES
from conftest import WORKSPACE, compose_load, standalone_compose

STACK = WORKSPACE / "docker"
INFRA_KEYCLOAK = WORKSPACE / "infra/keycloak/docker-compose.yaml"
PROD_REALM = WORKSPACE / "infra/keycloak/helm/files/aurelius-atlas.json"
SERVER_CLIENT = "aurelius-atlas-server"
SERVICE_CLIENTS = ("aurelius-atlas-provisioning", "aurelius-atlas-admin", "aurelius-atlas-validate-entity")
PLACEHOLDER = re.compile(r"^\$\{[A-Z_]+\}$")


@pytest.fixture(scope="module")
def realm() -> dict[str, Any]:
    """The realm file the stack's Keycloak imports."""
    return json.loads((STACK / "keycloak/aurelius-atlas.json").read_text())


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


def _client(realm: dict[str, Any], client_id: str) -> dict[str, Any]:
    return next(client for client in realm["clients"] if client["clientId"] == client_id)


@pytest.mark.covers(rules=["DMO-01"])
def test__the_realm_holds_the_server_client_and_its_roles(realm: dict[str, Any]) -> None:
    """The realm is the Helm realm's name; the server's client holds the server's four roles, and the public
    client's tokens carry them (DMO-01).
    """  # noqa: D205 - one sentence
    assert realm["realm"] == "aurelius-atlas"
    roles = {role["name"] for role in realm["roles"]["client"][SERVER_CLIENT]}
    assert roles == set(ROLE_PRIVILEGES)
    server = _client(realm, SERVER_CLIENT)
    assert not server["publicClient"]
    assert PLACEHOLDER.match(server["secret"])
    assert server["redirectUris"] == ["https://localhost:9000/atlas2/login.jsp"]
    assert server["attributes"]["post.logout.redirect.uris"] == "https://localhost:9000/atlas2/"
    public = _client(realm, "aurelius")
    assert public["publicClient"]
    assert public["standardFlowEnabled"]
    mapped = realm["clientScopeMappings"][SERVER_CLIENT]
    assert mapped == [{"client": "aurelius", "roles": sorted(roles, key=list(ROLE_PRIVILEGES).index)}]


@pytest.mark.covers(rules=["DMO-02"])
def test__the_realm_holds_service_identities_and_no_person(realm: dict[str, Any]) -> None:
    """The realm's only users are the service accounts of the three service clients (DD-673): the provisioning
    client holds the realm-management roles, the admin holds the server's four, the validator holds its one
    read; no user carries a password.
    """  # noqa: D205 - one sentence
    users = {user["username"]: user for user in realm["users"]}
    assert sorted(users) == [f"service-account-{client_id}" for client_id in sorted(SERVICE_CLIENTS)]
    assert all("credentials" not in user for user in users.values())
    assert "${DEMO_USER" not in json.dumps(realm)
    assert "${MEYN_USER" not in json.dumps(realm)
    prov = users["service-account-aurelius-atlas-provisioning"]
    assert "manage-users" in prov["clientRoles"]["realm-management"]
    admin = users["service-account-aurelius-atlas-admin"]
    assert set(admin["clientRoles"][SERVER_CLIENT]) == set(ROLE_PRIVILEGES)
    validator = users["service-account-aurelius-atlas-validate-entity"]
    assert validator["clientRoles"][SERVER_CLIENT] == ["atlas-read"]
    for client_id in SERVICE_CLIENTS:
        found = _client(realm, client_id)
        assert (found["publicClient"], found["serviceAccountsEnabled"]) == (False, True)
        assert not found["standardFlowEnabled"]
        assert PLACEHOLDER.match(found["secret"])


@pytest.mark.covers(rules=["DMO-02"])
def test__the_realm_matches_the_helm_realms_service_identities(realm: dict[str, Any]) -> None:
    """The clients the two copies share are the same shape, and the operators organization carries groups of
    its own ids (DD-673): one Keycloak may hold both realms, as a migration replaces the placeholders from the
    environment either way. The validator's client joins the stack's realm alone — the Helm world carries it
    in the dev realm (CHT-113), and the stack has only this one.
    """  # noqa: D205 - one sentence
    prod = json.loads(PROD_REALM.read_text())
    shared = [
        client_id
        for client_id in ("aurelius", SERVER_CLIENT, *SERVICE_CLIENTS)
        if any(c["clientId"] == client_id for c in prod["clients"])
    ]
    assert len(shared) >= 4
    for client_id in shared:
        stack_client, helm_client = _client(realm, client_id), _client(prod, client_id)
        assert stack_client.get("secret") == helm_client.get("secret"), client_id
        assert (
            stack_client.get("serviceAccountsEnabled"),
            stack_client.get("standardFlowEnabled"),
        ) == (helm_client.get("serviceAccountsEnabled"), helm_client.get("standardFlowEnabled")), client_id
    assert sorted(u["username"] for u in prod["users"]) <= sorted(u["username"] for u in realm["users"])


@pytest.mark.covers(rules=["DMO-03"])
def test__stack_signs_in_to_the_realm_alone(services: dict[str, Any], realm: dict[str, Any]) -> None:
    """Keycloak imports `aurelius-atlas` alone with its placeholders; the server and the sample import use it,
    and the sample import signs as the admin service identity (DMO-03, DD-666).
    """  # noqa: D205 - one sentence
    keycloak = services["keycloak"]
    assert "docker/keycloak:/opt/keycloak/data/import:ro" in keycloak["volumes"]
    # The realm folder holds the fragment and one realm: aurelius-atlas alone is imported (DMO-03).
    assert sorted(path.name for path in (STACK / "keycloak").iterdir() if path.suffix == ".json") == [
        "aurelius-atlas.json"
    ]
    placeholders = {
        client["secret"][2:-1]
        for client in realm["clients"]
        if isinstance(client.get("secret"), str) and PLACEHOLDER.match(client["secret"])
    }
    assert placeholders <= set(keycloak["environment"])
    assert services["aurelius-atlas-server"]["environment"]["AURELIUS_ATLAS_SERVER_AUTH_REALM"] == "aurelius-atlas"
    audiences = json.loads(services["aurelius-atlas-server"]["environment"]["AURELIUS_ATLAS_SERVER_AUTH_AUDIENCES"])
    assert {"aurelius", "aurelius-atlas-validate-entity", "aurelius-atlas-admin"} <= set(audiences)
    sample = services["sample-import"]["environment"]
    token_url = "https://localhost:9000/auth/realms/aurelius-atlas/protocol/openid-connect/token"  # noqa: S105
    assert sample["TOKEN_URL"] == token_url
    assert sample["ATLAS_CLIENT_ID"] == "aurelius-atlas-admin"
    assert sample["ATLAS_CLIENT_SECRET"] == "${ATLAS_ADMIN_CLIENT_SECRET:-}"  # noqa: S105 - a placeholder
    assert (
        services["aurelius-atlas-validate-entity"]["environment"]["AURELIUS_ATLAS_VALIDATE_ENTITY_TOKEN_URL"]
        == token_url
    )


@pytest.mark.covers(rules=["TRM-06"])
def test__the_realms_operator_organization_keeps_its_id_across_imports(realm: dict[str, Any]) -> None:
    """A fixed id, held by no other realm: every new Keycloak container imports the realm again, and the
    provisioning command finds the organization by it.
    """  # noqa: D205 - one sentence
    ids = [org["id"] for org in realm["organizations"]] + [
        g["id"] for org in realm["organizations"] for g in org["groups"]
    ]
    prod = json.loads(PROD_REALM.read_text())
    prod_ids = {g["id"] for org in prod["organizations"] for g in org["groups"]}
    assert len(set(ids)) == len(ids)
    assert not set(ids) & prod_ids


@pytest.mark.covers(rules=["IRT-06"])
def test__the_stacks_keycloak_keeps_the_production_topology(services: dict[str, Any]) -> None:
    """The stack's provider is the infra service extended, Postgres-backed behind the proxy
    (IRT-06, DD-670): the image and the certificate-copy Postgres boot inherited, the realm
    served at the issuer the server verifies. Its native OTLP push rides the stack's own
    collector's legacy leg (DD-675).
    """  # noqa: D205 - one sentence
    keycloak = services["keycloak"]
    base = yaml.safe_load(INFRA_KEYCLOAK.read_text())["services"]
    stated = compose_load(WORKSPACE / "docker/keycloak/compose.yaml")["services"]
    # The image pins and the Postgres boot arrive by inheritance, written nowhere in the stack.
    assert keycloak["image"] == base["keycloak"]["image"]
    assert "image" not in stated["keycloak"]
    # Prod mode as the chart runs it (CHT-16's rule, DD-676): `start`, never `start-dev`.
    assert keycloak["command"][0] == "start"
    assert not any(part.startswith("start-dev") for part in keycloak["command"])
    # The build stage of the chart's prod boot, as a one shot: it builds the options the runtime
    # env states, into the home the runtime mounts. Its env is only the build-time options (the
    # listener and telemetry keys would be dead weight there), and it waits for nothing.
    build = services["keycloak-build"]
    # The build persists exactly the build options the start passes - parity is the point.
    assert build["command"] == [
        "build",
        "--http-relative-path=/auth",
        "--metrics-enabled=true",
        "--tracing-enabled=true",
        "--telemetry-metrics-enabled=true",
        "--telemetry-logs-enabled=true",
    ]
    assert [part for part in keycloak["command"] if part.endswith("=true") or part.startswith("--")] == [
        "--import-realm",
        "--metrics-enabled=true",
        "--tracing-enabled=true",
        "--telemetry-metrics-enabled=true",
        "--telemetry-logs-enabled=true",
        "--telemetry-endpoint=https://otel-collector:4320",
    ]
    assert build["environment"] == {
        "KC_DB": "postgres",
        "KC_HEALTH_ENABLED": "true",
        "KC_FEATURES": "opentelemetry-metrics,preview",
        "JAVA_OPTS": "-Xms256m -Xmx512m",
    }
    assert "depends_on" not in build
    assert "kc-home:/opt/keycloak" in build["volumes"]
    # The start finds that home current: it mounts over the image, and the built options are
    # stated as env so the runtime checks pass without re-augmenting. Prod mode's TLS gate is
    # closed by naming the relaxation off - the proxy is the TLS terminator (ADR 039's shape).
    assert keycloak["depends_on"]["keycloak-build"] == {"condition": "service_completed_successfully"}
    assert "kc-home:/opt/keycloak" in keycloak["volumes"]
    assert keycloak["environment"]["KC_DB"] == build["environment"]["KC_DB"]
    assert keycloak["environment"]["KC_HEALTH_ENABLED"] == build["environment"]["KC_HEALTH_ENABLED"]
    assert keycloak["environment"]["KC_HTTP_RELATIVE_PATH"] == "/auth"
    assert keycloak["environment"]["KC_FEATURES"] == build["environment"]["KC_FEATURES"]
    assert keycloak["environment"]["KC_HTTPS_ENABLED"] == "false"
    postgres = services["postgres-keycloak"]
    assert postgres["image"] == base["postgres-keycloak"]["image"]
    assert postgres["entrypoint"] == base["postgres-keycloak"]["entrypoint"]
    assert "entrypoint" not in stated["postgres-keycloak"]
    # The database, not the in-memory server the first demo ran: Postgres healthy first.
    assert keycloak["depends_on"]["postgres-keycloak"] == {"condition": "service_healthy"}
    assert keycloak["environment"]["KC_DB"] == "postgres"
    assert keycloak["environment"]["KC_DB_URL"].startswith("jdbc:postgresql://postgres-keycloak:5432/keycloak")
    assert "keycloak-postgres-data:/var/lib/postgresql" in postgres["volumes"]
    assert "ports" not in postgres
    # The issuer behind the proxy, unchanged for the server's check (ADR 039's one answer).
    assert keycloak["environment"]["KC_HOSTNAME"] == "https://localhost:9000/auth"
    assert keycloak["environment"]["KC_HTTP_RELATIVE_PATH"] == "/auth"
    assert keycloak["environment"]["KC_PROXY_HEADERS"] == "xforwarded"
    # The legacy OTLP leg (DD-675): the issuer cannot present its own token at cold boot
    # (DD-196), so it carries the shared ingest bearer to the stack's collector, as in the slice.
    assert keycloak["environment"]["OTEL_EXPORTER_OTLP_ENDPOINT"] == "https://otel-collector:4320"
    assert keycloak["environment"]["QUARKUS_OTEL_EXPORTER_OTLP_ENDPOINT"] == "https://otel-collector:4320"
    assert "${OTEL_COLLECTOR_INGEST_TOKEN:?}" in keycloak["environment"]["OTEL_EXPORTER_OTLP_HEADERS"]
    assert "--telemetry-endpoint=https://otel-collector:4320" in keycloak["command"]
    # No published port, and no host port: only the proxy reaches it (nginx.conf).
    assert "ports" not in keycloak
    # Its own healthcheck: the server lives under /auth here, so the probe path is the stack's.
    assert "/auth/health/ready" in keycloak["healthcheck"]["test"][1]
    assert "/auth/health/ready" not in base["keycloak"]["healthcheck"]["test"][1]
