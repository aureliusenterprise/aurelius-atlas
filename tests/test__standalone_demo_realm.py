"""The standalone stack's realm `aurelius-atlas` (DMO-01 to DMO-03, 9.5b, DD-641; DD-673; IRT-06, ADR 066).

The realm file and the compose file are read as written: the clients and their roles against the server's
``ROLE_PRIVILEGES``, the service identities, and the stack's wiring to the realm. The realm carries the Helm
production realm's posture (DD-673): the same name and the same service identities, and no default user. Its
browser URIs name `localhost` as written, with no host placeholder (SPC-02, DD-694). The stack's Keycloak is
the infra slice's service extended (DD-670), so the suite proves the production topology it inherits, booted
with no build one-shot (SPC-05, DD-696).
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


@pytest.mark.covers(rules=["DMO-01", "SPC-02"])
def test__the_realm_holds_the_server_client_and_its_roles(realm: dict[str, Any]) -> None:
    """The realm is the Helm realm's name; the server's client holds the server's four roles, and the public
    client's tokens carry them (DMO-01). The browser URIs name the host the stack serves, written out (SPC-02).
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
    # SPC-02, SPS-06 retired: the browser URIs are literal, and no host variable is substituted into them.
    assert public["redirectUris"] == ["https://localhost:9000/*"]
    assert public["webOrigins"] == ["https://localhost:9000"]
    assert "STANDALONE_HOST" not in json.dumps([public, server])
    mapped = realm["clientScopeMappings"][SERVER_CLIENT]
    assert mapped == [{"client": "aurelius", "roles": sorted(roles, key=list(ROLE_PRIVILEGES).index)}]


@pytest.mark.covers(rules=["DMO-02", "IRT-06"])
def test__the_realm_holds_service_identities_and_the_operator_alone(realm: dict[str, Any]) -> None:
    """The realm's users are the service accounts of the three service clients and the platform operator (DD-700):
    the provisioning client holds the realm-management roles, the admin holds the server's four, the validator its
    one read. The operator alone carries a password, a placeholder; no tenant's user is in the realm file.
    """  # noqa: D205 - one sentence
    users = {user["username"]: user for user in realm["users"]}
    services = [f"service-account-{client_id}" for client_id in sorted(SERVICE_CLIENTS)]
    assert sorted(users) == sorted([*services, "operator"])
    assert all("credentials" not in users[name] for name in services)
    operator = users["operator"]
    assert operator["credentials"] == [{"type": "password", "value": "${DEMO_USER_OPERATOR_PASSWORD}"}]
    assert sorted(operator["realmRoles"]) == ["atlas-operator", "default-roles-aurelius-atlas"]
    assert "${DEMO_USER_ATLAS" not in json.dumps(realm)
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
    its own ids (DD-673): one Keycloak may hold both realms. The validator's client joins the stack's realm
    alone — the Helm world carries it in the dev realm (CHT-113), and the stack has only this one.
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
    # The Helm realm's users are a subset of the stack's, which adds the validator and the operator (DD-700).
    assert {u["username"] for u in prod["users"]} <= {u["username"] for u in realm["users"]}


@pytest.mark.covers(rules=["DMO-03", "SPC-06"])
def test__stack_signs_in_to_the_realm_alone(services: dict[str, Any], realm: dict[str, Any]) -> None:
    """Keycloak imports `aurelius-atlas` alone with its secret placeholders; the server and the sample import
    use it, and the sample import signs as the admin service identity (DMO-03, DD-666). The sample import runs
    only when the person asks for it, behind the `demo` profile (SPC-06, DD-697).
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
    sample = services["sample-import"]
    assert sample["profiles"] == ["demo"]
    token_url = "https://localhost:9000/auth/realms/aurelius-atlas/protocol/openid-connect/token"  # noqa: S105
    assert sample["environment"]["TOKEN_URL"] == token_url
    assert sample["environment"]["ATLAS_CLIENT_ID"] == "aurelius-atlas-admin"
    assert sample["environment"]["ATLAS_CLIENT_SECRET"] == "${ATLAS_ADMIN_CLIENT_SECRET:-}"  # noqa: S105 - a placeholder
    token = services["aurelius-atlas-validate-entity"]["environment"]["AURELIUS_ATLAS_VALIDATE_ENTITY_TOKEN_URL"]
    assert token == token_url


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


@pytest.mark.covers(rules=["IRT-06", "SPC-05"])
def test__the_stacks_keycloak_keeps_the_production_topology(services: dict[str, Any]) -> None:
    """The stack's provider is the infra service extended, Postgres-backed behind the proxy
    (IRT-06, DD-670): the image and the certificate-copy Postgres boot inherited, the realm
    served at the issuer the server verifies. Its native OTLP push rides the stack's own
    collector's legacy leg (DD-675). Prod mode runs with no build one-shot: the home Compose
    seeds from the image carries the first start's augmentation (SPC-05, DD-696).
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
    # SPC-05: no build one-shot. The start passes the flags that are build options in prod mode, so
    # its first boot re-augments them into the seeded home and a later boot finds a current build.
    assert "keycloak-build" not in services
    assert "keycloak-build" not in stated
    assert [part for part in keycloak["command"] if part.endswith("=true") or part.startswith("--")] == [
        "--import-realm",
        "--metrics-enabled=true",
        "--tracing-enabled=true",
        "--telemetry-metrics-enabled=true",
        "--telemetry-logs-enabled=true",
        "--telemetry-endpoint=https://otel-collector:4320",
    ]
    assert "kc-home:/opt/keycloak" in keycloak["volumes"]
    assert keycloak["environment"]["KC_DB"] == "postgres"
    assert keycloak["environment"]["KC_HEALTH_ENABLED"] == "true"
    assert keycloak["environment"]["KC_HTTP_RELATIVE_PATH"] == "/auth"
    assert keycloak["environment"]["KC_FEATURES"] == "opentelemetry-metrics,preview"
    assert keycloak["environment"]["KC_HTTPS_ENABLED"] == "false"
    # The JVM options hold the truststore and the heap cap, and no realm placeholder flag (SPC-02).
    assert "-Djavax.net.ssl.trustStore=/certs/truststore.p12" in keycloak["environment"]["JAVA_OPTS"]
    assert "replace-placeholders" not in keycloak["environment"]["JAVA_OPTS"]
    postgres = services["postgres-keycloak"]
    assert postgres["image"] == base["postgres-keycloak"]["image"]
    assert postgres["entrypoint"] == base["postgres-keycloak"]["entrypoint"]
    assert "entrypoint" not in stated["postgres-keycloak"]
    # The database, not the in-memory server the first demo ran: Postgres healthy first, and nothing else.
    assert keycloak["depends_on"] == {"postgres-keycloak": {"condition": "service_healthy"}}
    assert keycloak["environment"]["KC_DB"] == "postgres"
    assert keycloak["environment"]["KC_DB_URL"].startswith("jdbc:postgresql://postgres-keycloak:5432/keycloak")
    assert "keycloak-postgres-data:/var/lib/postgresql" in postgres["volumes"]
    assert "ports" not in postgres
    # The issuer behind the proxy, unchanged for the server's check (ADR 039's one answer). SPC-02:
    # the value is the literal host the stack serves, and no host variable sits in the environment.
    assert keycloak["environment"]["KC_HOSTNAME"] == "https://localhost:9000/auth"
    assert "STANDALONE_HOST" not in keycloak["environment"]
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


@pytest.mark.covers(rules=["IRT-06"])
def test__every_client_scope_a_client_names_is_defined_in_the_realm(realm: dict[str, Any]) -> None:
    """A realm file that lists client scopes gets none of Keycloak's built-in ones, so each scope a client or the
    realm's defaults name must be in the file. Without ``organization``, a tenancy sign-in failed with
    ``invalid_scope``; without ``profile``, ``email`` and ``basic``, a token lacked the user's name and id.
    """  # noqa: D205 - one sentence
    defined = {scope["name"] for scope in realm["clientScopes"]}
    named = set(realm.get("defaultDefaultClientScopes") or []) | set(realm.get("defaultOptionalClientScopes") or [])
    for client_ in realm["clients"]:
        named |= set(client_.get("defaultClientScopes") or []) | set(client_.get("optionalClientScopes") or [])
    assert named <= defined, sorted(named - defined)
    assert {"organization", "profile", "email", "basic"} <= defined


@pytest.mark.covers(rules=["IRT-06"])
def test__the_account_console_is_in_the_realm_file_with_its_scopes_and_roles(realm: dict[str, Any]) -> None:
    """Keycloak makes its built-in clients before it imports a file's client scopes, so a built-in
    ``account-console`` gets none and its tokens carry no roles: the account page answers 403. The file names the
    account clients with their default scopes, roles and mappings, as the dev realm does.
    """  # noqa: D205 - one sentence
    console = _client(realm, "account-console")
    assert {"roles", "basic", "profile", "email"} <= set(console["defaultClientScopes"])
    # With the account client in the file too, Keycloak makes neither itself: no duplicate at import. The file then
    # carries what it would have made: the account roles and the default role granting the account page its two.
    assert _client(realm, "account")["redirectUris"] == ["/realms/aurelius-atlas/account/*"]
    assert {"view-profile", "manage-account"} <= {role["name"] for role in realm["roles"]["client"]["account"]}
    assert realm["defaultRole"]["name"] == "default-roles-aurelius-atlas"
    default = next(role for role in realm["roles"]["realm"] if role["name"] == "default-roles-aurelius-atlas")
    assert sorted(default["composites"]["client"]["account"]) == ["manage-account", "view-profile"]
    assert console["redirectUris"] == ["/realms/aurelius-atlas/account/*"]
    assert {"client": "account-console", "roles": ["manage-account", "view-groups"]} in realm["clientScopeMappings"][
        "account"
    ]


@pytest.mark.covers(rules=["IRT-06"])
def test__the_roles_scope_resolves_the_audience_and_carries_the_realm_roles(realm: dict[str, Any]) -> None:
    """Beside DD-661's client-role mapper, the roles scope resolves the audience, so a token holding the
    ``account`` roles is one the account API takes (the webapp saves its language there, SHC-10), and carries the
    realm roles, the operator's ``atlas-operator`` among them.
    """  # noqa: D205 - one sentence
    scope = next(scope for scope in realm["clientScopes"] if scope["name"] == "roles")
    mappers = {mapper["protocolMapper"] for mapper in scope["protocolMappers"]}
    assert {
        "oidc-usermodel-client-role-mapper",
        "oidc-audience-resolve-mapper",
        "oidc-usermodel-realm-role-mapper",
    } <= mappers
