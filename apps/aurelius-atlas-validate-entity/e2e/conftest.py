"""E2E fixtures: the app on TLS, the Keycloak mint, and clients (DD-283).

The suite's one target is the Helm umbrella of ``tools/cluster/install.sh up``:
the app dialled at its Service's real name through a port-forward (SAN-honest
TLS, CHT-104), the token minted through ``keycloak.atlas.test`` — the same
issuer origin the deployed pods verify against (DD-265) — with the writer
password read from the release's ``atlas-keycloak-users`` Secret. The cluster
machinery is aurelius-atlas-cluster-lane's (10.5b, DD-282); this conftest names
only what is the suite's: the app Service, the mint identity, the clients.

The suite's tests are data-independent (extract-from-body), so no seeding is
needed.
"""

import ssl
import sys
from collections.abc import AsyncIterator, Iterator

import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_cluster_lane import (
    SecretReader,
    ServiceForward,
    install_cluster_fixtures,
    mint_token,
)
from aurelius_atlas_validate_entity_client import ValidateEntityClient

# The cluster shapes (the umbrella install of tools/cluster/install.sh).
SERVICE_CLUSTER = "atlas-validate-entity"
"""The aux chart's Service (the umbrella's release name + chart name)."""
SERVICE_PORT = 21003
"""The Service's real port — what the shim rewrites alongside the name (CHT-104)."""
ISSUER_HOST = "keycloak.atlas.test"
"""The edge-routed issuer: CoreDNS rewrites it in-cluster (DD-265), the
resolver maps it here — the pods' own issuer origin, so the mint stays honest."""
KEYCLOAK_USERS_SECRET = "atlas-keycloak-users"
"""The release Secret carrying the smoke users' passwords (CHT-78)."""
CLUSTER_NAMESPACE = "atlas"

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the realm to serve tokens (a warming stack may be starting up)."""

# The session `cluster` gate, the autouse resolver shim, and `ca_file` come
# from the library (CHT-103).
install_cluster_fixtures(sys.modules[__name__])


@pytest.fixture(scope="session")
def token(ca_file: str) -> str:
    """A bearer token for the app, minted from the realm as the writer (the `aurelius` client).

    Minted at ``https://keycloak.atlas.test`` — the same origin the deployed
    pods verify against — with the password read from the release's
    ``atlas-keycloak-users`` Secret. The token carries azp `aurelius`, the
    audience the app accepts (AUX-04, DV-75); the minikube overlay's audience
    override (CHT-105) is what answers it on the cluster.
    """
    password = SecretReader(CLUSTER_NAMESPACE).read(KEYCLOAK_USERS_SECRET, "writer-password")
    return mint_token(
        f"https://{ISSUER_HOST}",
        password,
        ca_file=ca_file,
        timeout=MINT_TIMEOUT_SECONDS,
    )


@pytest.fixture(scope="session")
def app_url(_cluster_dns: None, ca_file: str) -> Iterator[str]:
    """The app's base URL, once healthy.

    The Service's own name at its real port through a port-forward, so the
    URL, SNI, and verified SAN stay honest (CHT-104).
    """
    with ServiceForward(
        SERVICE_CLUSTER,
        SERVICE_PORT,
        f"{SERVICE_CLUSTER}.atlas.svc.cluster.local",
        namespace=CLUSTER_NAMESPACE,
        probe_path="/liveness",
        ca_file=ca_file,
    ) as forward:
        yield forward.url


# The function loop (pytest-asyncio 1.x): the root config gives async fixtures
# a module loop, which here outlives the test loops its TLS connections were
# opened on — aclose then schedules on a closed loop ("Event loop is closed").
# On the function loop, client, requests, and aclose share one loop per test.
@pytest_asyncio.fixture(loop_scope="function")
async def client(app_url: str, token: str, ca_file: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the deployed app over HTTPS, verifying it against the chart CA, carrying the token."""
    async with httpx.AsyncClient(
        base_url=app_url,
        verify=ssl.create_default_context(cafile=ca_file),
        headers={"authorization": f"Bearer {token}"},
    ) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def anonymous_client(app_url: str, ca_file: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running app over HTTPS, without a token (the 401 path)."""
    async with httpx.AsyncClient(base_url=app_url, verify=ssl.create_default_context(cafile=ca_file)) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def api(app_url: str, token: str, ca_file: str) -> AsyncIterator[ValidateEntityClient]:
    """The typed validate-entity client for the running app over HTTPS (CL-40).

    The fixture builds the httpx pool (the chart CA, no auth header — the
    client adds the bearer per call, CL-03) and closes it, the owner-closes
    rule of CL-02; the minted realm token is the client's token source.
    """
    async with httpx.AsyncClient(base_url=app_url, verify=ssl.create_default_context(cafile=ca_file)) as http:
        yield ValidateEntityClient(http, token)
