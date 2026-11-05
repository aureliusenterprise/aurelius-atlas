"""The rehearsed restore (SNP-06, ADR 026 R2 and R7): a snapshot of a running server's store comes back as a
working server on a clean cluster.

The rehearsal runs on two Elasticsearch containers of its own that share one snapshot directory, so it never
touches the shared dev store (DD-223). On the first, a server with snapshots on writes a type and two
entities, and a snapshot is taken by the policy; the first cluster is then removed. On the second, empty, the
snapshot command restores the server's indices, and a server started on them answers the entities, their
audits and a search as the first did. The time from the restore's start to the second server's first answer
is the recovery time, recorded as the junit property ``recovery_seconds``.
"""  # noqa: D205 - the title sentence spans the first two lines

import argparse
import os
import shutil
import tempfile
import time
from collections.abc import AsyncIterator, Callable, Generator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server import snapshots as command
from aurelius_atlas_server.settings import ENV_PREFIX, StoreAccessSettings
from aurelius_atlas_store_es import ElasticsearchStore, StoreSettings
from aurelius_atlas_store_es.snapshots import list_snapshots, take_snapshot
from aurelius_atlas_store_es.testing.container import elasticsearch_container

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA, which signed the server's certificate and the dev Keycloak's."""

TYPE = "snapshot_rehearsal_dataset"
RECOVERY_BUDGET_SECONDS = 300.0
"""The recovery time of R7 at the rehearsal's scale: the restore, the second server's start, its first answer."""


type TokenSource = Callable[[], str]
"""The e2e conftest's ``user_token``: the dev writer's current access token."""


class _Bearer(httpx.Auth):
    """Each request with the source's current token: the dev realm's tokens live 60 seconds."""

    def __init__(self, token: TokenSource) -> None:
        self._token = token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        """Add the ``Authorization`` header."""
        request.headers["Authorization"] = f"Bearer {self._token()}"
        yield request


@pytest.fixture
def snapshot_dir() -> Iterator[Path]:
    """A host directory both clusters mount as their ``path.repo``, writable by the nodes' user (uid 1000)."""
    path = Path(tempfile.mkdtemp(prefix="aurelius-atlas-snapshots-"))
    path.chmod(0o777)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def auth_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """The server client's secret; every other server setting of the project's ``.env`` is cleared.

    The in-process servers are configured here alone: the ``.env`` names the dev store, the dev collector and
    paths relative to the workspace root.
    """
    secret = os.environ["AURELIUS_ATLAS_SERVER_AUTH_CLIENT_SECRET"]
    for name in [name for name in os.environ if name.startswith(ENV_PREFIX)]:
        monkeypatch.delenv(name)
    return secret


def _settings(store: StoreSettings, auth_secret: str) -> ServerSettings:
    """A server on ``store`` with snapshots on, verifying the dev realm's tokens; nothing else scheduled."""
    return ServerSettings.model_validate(
        {
            "elasticsearch_hosts": [str(host) for host in store.hosts],
            "elasticsearch_password": store.password.get_secret_value(),
            "elasticsearch_ca_certs": store.ca_certs,
            "tls_cert_file": PROJECT / "certs/aurelius-atlas-server.pem",
            "tls_key_file": PROJECT / "certs/aurelius-atlas-server-key.pem",
            "tasks_enabled": False,
            "metrics_persist_interval_minutes": 0,
            "snapshot_enabled": True,
            "auth_server_url": "https://keycloak.localhost:8443/",
            "auth_client_secret": auth_secret,
            "auth_audiences": ["aurelius"],
            "auth_ca_file": CA_FILE,
        }
    )


@asynccontextmanager
async def _server(settings: ServerSettings, token: TokenSource) -> AsyncIterator[httpx.AsyncClient]:
    """The server started in-process on its store, and a client for it as the dev writer."""
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://aurelius-atlas", auth=_Bearer(token), timeout=60
        ) as client:
            yield client


async def _write_catalogue(client: httpx.AsyncClient) -> list[str]:
    """A type and two entities of it; their guids."""
    typedefs = {"entityDefs": [{"name": TYPE, "superTypes": ["DataSet"], "attributeDefs": []}]}
    assert (await client.post("/api/atlas/v2/types/typedefs", json=typedefs)).status_code == 200
    entities = {
        "entities": [
            {"typeName": TYPE, "attributes": {"qualifiedName": f"rehearsal.{n}@snapshot", "name": f"rehearsal {n}"}}
            for n in (1, 2)
        ]
    }
    created = await client.post("/api/atlas/v2/entity/bulk", json=entities)
    assert created.status_code == 200, created.text
    return sorted(entity["guid"] for entity in created.json()["mutatedEntities"]["CREATE"])


async def _read_catalogue(client: httpx.AsyncClient, guids: list[str]) -> dict[str, Any]:
    """What a person sees of the catalogue: the entities, their audits and a search of the type."""
    entities = [(await client.get(f"/api/atlas/v2/entity/guid/{guid}")).json()["entity"] for guid in guids]
    audits = [len((await client.get(f"/api/atlas/v2/entity/{guid}/audit")).json()) for guid in guids]
    search = (await client.get("/api/atlas/v2/search/basic", params={"typeName": TYPE})).json()
    return {
        "entities": [(e["guid"], e["status"], e["attributes"]["qualifiedName"], e["version"]) for e in entities],
        "audits": audits,
        "found": sorted(entity["guid"] for entity in search.get("entities", [])),
    }


@pytest.mark.covers("aurelius_atlas_server.snapshots.run", rules=["SNP-04", "SNP-05", "SNP-06"])
@pytest.mark.covers("aurelius_atlas_store_es.testing.container.elasticsearch_container", rules=["SNP-06"])
async def test__a_snapshot_of_a_running_server_comes_back_as_a_working_server_on_a_clean_cluster(
    snapshot_dir: Path,
    auth_secret: str,
    user_token: TokenSource,
    record_property: Callable[[str, object], None],
) -> None:
    """Snapshot on the first cluster, remove it, restore on a second, and the second server answers the same."""
    with elasticsearch_container(snapshot_dir=snapshot_dir) as first:
        async with _server(_settings(first, auth_secret), user_token) as client:
            guids = await _write_catalogue(client)
            before = await _read_catalogue(client, guids)
        async with ElasticsearchStore(first) as store:
            taken = await take_snapshot(store.client)

    with elasticsearch_container(snapshot_dir=snapshot_dir) as second:
        lines: list[str] = []
        access = StoreAccessSettings.model_validate(
            {
                "elasticsearch_hosts": [str(host) for host in second.hosts],
                "elasticsearch_password": second.password.get_secret_value(),
                "elasticsearch_ca_certs": second.ca_certs,
            }
        )
        started = time.monotonic()
        await command.run(argparse.Namespace(command="restore", snapshot=None, replace=False), access, lines.append)
        async with _server(_settings(second, auth_secret), user_token) as client:
            answered = await client.get(f"/api/atlas/v2/entity/guid/{guids[0]}")
            recovery = time.monotonic() - started
            after = await _read_catalogue(client, guids)
        async with ElasticsearchStore(second) as store:
            [listed] = await list_snapshots(store.client)

    record_property("recovery_seconds", f"{recovery:.1f}")
    record_property("restore", lines[0])
    assert answered.status_code == 200
    assert lines[0].startswith(f"Restored {taken}: ")
    assert listed.name == taken
    assert after == before
    assert before["found"] == guids
    assert all(count >= 1 for count in before["audits"])
    assert recovery < RECOVERY_BUDGET_SECONDS
