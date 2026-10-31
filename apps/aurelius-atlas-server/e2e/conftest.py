"""E2E fixtures: the deployed server through the webapp edge, and clients (DD-283).

The suite's one target is the Helm umbrella of ``tools/cluster/install.sh up``:
the data path rides the whole deployment — Gateway, the webapp's nginx /api/
proxy, backend TLS to the server — under the edge hostname whose HTTPRoute
serves it, so SNI and certificate verification stay honest (the chart's edge
leaf carries this SAN). The cluster machinery is aurelius-atlas-cluster-lane's
(10.5b, DD-282; CHT-103/104); this conftest names only what is the server
suite's own shape — which services it dials.
"""

import ssl
import sys
from collections.abc import AsyncIterator, Iterator

import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_cluster_lane import ServiceForward, install_cluster_fixtures
from aurelius_atlas_server_client import AtlasClient

# The cluster shapes (the umbrella install of tools/cluster/install.sh).
RELEASE = "atlas"
NAMESPACE = "atlas"
EDGE_HOST = "atlas.atlas.test"
"""The Gateway hostname whose HTTPRoute serves the webapp edge — the suite
dials the data path by its real name so SNI and certificate verification stay
honest (the chart's edge leaf carries this SAN)."""

# The session `cluster` gate (fail-fast on a missing install), the autouse
# resolver shim, and the `ca_file` fixture (CHT-103).
install_cluster_fixtures(sys.modules[__name__])


@pytest.fixture(scope="session")
def server(_cluster_dns: None) -> str:
    """The server's base URL: the edge hostname through the installed umbrella.

    Traffic rides the whole deployment — Gateway, the webapp's nginx /api/
    proxy, backend TLS to the server — not a bypass.
    """
    return f"https://{EDGE_HOST}"


@pytest.fixture(scope="session")
def server_direct(_cluster_dns: None) -> Iterator[str]:
    """The server pod's own URL, bypassing the edge.

    The legacy dashboard is baked into the server image (DD-018) and served at
    its own root; at the edge, `/` belongs to the SPA. The dashboard tests
    port-forward the Service so they exercise the dashboard, not the webapp.
    The dial stays the loopback URL Playwright opens under
    ``ignore_https_errors`` (ADR 039 — browsers bypass the shim), which is why
    its readiness probe is the insecure check (CHT-104's one sanctioned
    127.0.0.1).
    """
    with ServiceForward(
        f"{RELEASE}-server",
        21000,
        "127.0.0.1",
        namespace=NAMESPACE,
        probe_path="/api/atlas/admin/liveness",
        insecure=True,
    ) as forward:
        yield f"https://127.0.0.1:{forward.local_port}"


@pytest.fixture(scope="session")
def tempo_url(_cluster_dns: None) -> Iterator[str]:
    """Tempo's query API through a port-forward — the suite's own local ingress.

    The cluster publishes nothing to the host, so the suite brings its own.
    """
    with ServiceForward(
        f"{RELEASE}-observability-tempo",
        3200,
        "127.0.0.1",
        namespace=NAMESPACE,
        probe_path="/ready",
        scheme="http",
    ) as forward:
        yield f"http://127.0.0.1:{forward.local_port}"


@pytest_asyncio.fixture(loop_scope="function")
async def client(server: str, ca_file: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the deployed server over HTTPS, verifying it against the chart CA."""
    async with httpx.AsyncClient(base_url=server, verify=ssl.create_default_context(cafile=ca_file)) as client:
        yield client


# The function loop (pytest-asyncio 1.x): the root config gives async fixtures
# a module loop, which here outlives the test loops its TLS connections were
# opened on — aclose then schedules on a closed loop ("Event loop is closed").
# On the function loop, the client, its requests, and aclose share one loop.
@pytest_asyncio.fixture(loop_scope="function")
async def api(server: str, ca_file: str) -> AsyncIterator[AtlasClient]:
    """The typed Atlas client for the deployed server over HTTPS (CL-11).

    The fixture builds the httpx pool and closes it (CL-02). The server's admin
    routes are open until 6.1, so the token source is empty — an empty source
    travels unauthenticated (CL-03), exactly as the dashboard calls arrive.
    """
    async with httpx.AsyncClient(base_url=server, verify=ssl.create_default_context(cafile=ca_file)) as http:
        yield AtlasClient(http, "")
