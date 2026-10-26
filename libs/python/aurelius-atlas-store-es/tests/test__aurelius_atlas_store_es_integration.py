"""The store against a real Elasticsearch 9.5 with TLS and authentication on."""

from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import trustme
from aurelius_atlas_store_es import (
    ElasticsearchStore,
    HealthStatus,
    StoreSettings,
    StoreUnavailableError,
    check_health,
)
from aurelius_atlas_store_es.testing.container import elasticsearch_container
from elasticsearch import AsyncElasticsearch

# The module-scoped container and the async fixtures share one event loop with the tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module")
def es_settings() -> Generator[StoreSettings]:
    """One container for the whole module; tests clean up the indices they create.

    ``request_timeout`` is raised from the 10 s default: every client's first
    request is the transport's product-check HEAD, bounded by the CLIENT
    timeout - on a runner shared by the whole e2e fan-out that HEAD can pass
    10 s before the server answers (CI runs 40282797027, 40286077875,
    40289090955: elastic_transport.ConnectionTimeout). Fast-failure tests
    below override it back down.
    """
    with elasticsearch_container() as settings:
        yield with_changes(settings, request_timeout=60)


@pytest.fixture
async def store(es_settings: StoreSettings) -> AsyncGenerator[ElasticsearchStore]:
    """An open store on the container."""
    async with ElasticsearchStore(es_settings) as opened:
        yield opened


def with_changes(settings: StoreSettings, **changes: object) -> StoreSettings:
    """Copy settings with some fields replaced, re-validated."""
    return StoreSettings.model_validate({**settings.model_dump(), "password": settings.password, **changes})


@pytest.mark.covers("aurelius_atlas_store_es.testing.container.elasticsearch_container")
async def test__elasticsearch_container_yields_working_settings(es_settings: StoreSettings) -> None:
    """The fixture starts a TLS-only, authenticated server and yields settings that reach it."""
    assert es_settings.host_urls[0].startswith("https://localhost:")

    async with ElasticsearchStore(es_settings) as store:
        info = await store.client.info()

    assert info["cluster_name"] == "aurelius-atlas-test"


@pytest.mark.covers(
    "aurelius_atlas_store_es.ElasticsearchStore.open",
    "aurelius_atlas_store_es.ElasticsearchStore.client",
    rules=["STO-03", "STO-04"],
)
async def test__elasticsearch_store_opens_on_elasticsearch_9(store: ElasticsearchStore) -> None:
    """An Elasticsearch 9 server is accepted and the store holds one open client."""
    assert store.is_open
    info = await store.client.info()
    assert str(info["version"]["number"]).startswith("9.")


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.health", rules=["STO-05", "STO-07"])
async def test__elasticsearch_store_health_is_up_on_a_fresh_node(store: ElasticsearchStore) -> None:
    """A fresh single node is up and reports its name, version and status."""
    report = await store.health()

    assert report.status is HealthStatus.UP
    assert report.cluster_name == "aurelius-atlas-test"
    assert report.version is not None
    assert report.version.startswith("9.")
    assert report.cluster_status in {"green", "yellow"}


@pytest.mark.covers("aurelius_atlas_store_es.check_health", rules=["STO-05"])
async def test__check_health_is_up_when_replicas_cannot_be_placed(store: ElasticsearchStore) -> None:
    """An index with a replica makes a single node yellow, which is still up."""
    index = "sto-05-yellow"
    await store.client.indices.create(index=index, settings={"number_of_shards": 1, "number_of_replicas": 1})
    try:
        # request_timeout must exceed the server-side timeout: cluster.health
        # blocks for up to `timeout` waiting for yellow, and the client's
        # default 3 s request timeout kills that wait on a loaded runner
        # (CI run 40282797027: elastic_transport.ConnectionTimeout).
        await store.client.cluster.health(
            index=index,
            wait_for_status="yellow",
            timeout="30s",
            request_timeout=60,  # pyright: ignore[reportCallIssue] - transport kwarg, not in the generated signature
        )
        report = await check_health(store.client)
    finally:
        await store.client.indices.delete(index=index)

    assert report.cluster_status == "yellow"
    assert report.status is HealthStatus.UP


@pytest.mark.covers("aurelius_atlas_store_es.check_health", rules=["STO-05", "STO-07"])
async def test__check_health_is_down_when_a_primary_cannot_be_placed(store: ElasticsearchStore) -> None:
    """An index whose primary cannot be allocated makes the cluster red, which is down."""
    index = "sto-05-red"
    await store.client.indices.create(
        index=index,
        settings={"number_of_shards": 1, "number_of_replicas": 0, "routing.allocation.require._name": "nowhere"},
        wait_for_active_shards="0",
    )
    try:
        report = await check_health(store.client)
    finally:
        await store.client.indices.delete(index=index)

    assert report.status is HealthStatus.DOWN
    assert report.cluster_status == "red"
    assert report.cluster_name == "aurelius-atlas-test"
    assert report.reason == "cluster status is red"


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.open", rules=["STO-04", "STO-08"])
async def test__elasticsearch_store_open_rejects_a_wrong_password(es_settings: StoreSettings) -> None:
    """A rejected credential makes the store unavailable, without echoing the password."""
    wrong = "not-the-password"
    store = ElasticsearchStore(with_changes(es_settings, password=wrong))

    with pytest.raises(StoreUnavailableError, match="401") as caught:
        await store.open()

    assert wrong not in str(caught.value)
    assert not store.is_open


@pytest.mark.covers("aurelius_atlas_store_es.check_health", rules=["STO-06"])
async def test__check_health_reports_a_rejected_credential_as_down(es_settings: StoreSettings) -> None:
    """A client with a wrong password gets a down report, not an exception."""
    client = AsyncElasticsearch(
        hosts=es_settings.host_urls,
        basic_auth=(es_settings.username, "not-the-password"),
        ca_certs=str(es_settings.ca_certs_path),
    )
    try:
        report = await check_health(client)
    finally:
        await client.close()

    assert report.status is HealthStatus.DOWN
    assert report.reason == "request rejected with status 401"


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.open", rules=["STO-02"])
async def test__elasticsearch_store_open_rejects_an_untrusted_certificate(
    es_settings: StoreSettings, tmp_path: Path
) -> None:
    """A server certificate that the configured CA did not sign is refused."""
    other_ca = tmp_path / "other-ca.pem"
    trustme.CA().cert_pem.write_to_path(other_ca)

    with pytest.raises(StoreUnavailableError):
        await ElasticsearchStore(with_changes(es_settings, ca_certs=other_ca)).open()


@pytest.mark.covers(
    "aurelius_atlas_store_es.ElasticsearchStore.open",
    "aurelius_atlas_store_es.check_health",
    rules=["STO-04", "STO-06"],
)
async def test__elasticsearch_store_open_reports_an_unreachable_server(es_settings: StoreSettings) -> None:
    """Nothing listening is unavailable on open and down on health, never a crash."""
    settings = with_changes(es_settings, hosts=["https://localhost:1"], request_timeout=2)

    with pytest.raises(StoreUnavailableError, match="unreachable"):
        await ElasticsearchStore(settings).open()

    client = AsyncElasticsearch(hosts=settings.host_urls, ca_certs=str(settings.ca_certs_path), request_timeout=2)
    try:
        report = await check_health(client)
    finally:
        await client.close()

    assert report.status is HealthStatus.DOWN
    assert report.reason is not None
    assert report.reason.startswith("server unreachable")
