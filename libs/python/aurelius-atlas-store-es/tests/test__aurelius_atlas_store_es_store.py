from collections.abc import Callable

import pytest
from aurelius_atlas_store_es import (
    ElasticsearchStore,
    HealthStatus,
    StoreSettings,
    StoreUnavailableError,
    UnsupportedVersionError,
)
from aurelius_atlas_store_es.store import STORE_NOT_OPEN_ERROR
from aurelius_atlas_store_es.testing.fake import FakeClient, response_meta
from elasticsearch import AuthenticationException, ConnectionTimeout
from elasticsearch import ConnectionError as TransportConnectionError


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.open", rules=["STO-01", "STO-02"])
async def test__elasticsearch_store_open_builds_a_verifying_https_client(
    settings: StoreSettings, fake_client: Callable[[], FakeClient], password: str
) -> None:
    """The client is built from the settings and always verifies certificates."""
    async with ElasticsearchStore(settings):
        kwargs = fake_client().kwargs

    assert kwargs == {
        "hosts": ["https://localhost:9200"],
        "basic_auth": ("elastic", password),
        "ca_certs": str(settings.ca_certs_path),
        "verify_certs": True,
        "request_timeout": 10.0,
    }


@pytest.mark.covers(
    "aurelius_atlas_store_es.ElasticsearchStore.open",
    "aurelius_atlas_store_es.ElasticsearchStore.close",
    rules=["STO-03"],
)
async def test__elasticsearch_store_closes_its_client_once(
    settings: StoreSettings, fake_client: Callable[[], FakeClient]
) -> None:
    """One client per store, closed exactly once, however often close is called."""
    store = ElasticsearchStore(settings)

    await store.open()
    await store.open()
    assert store.is_open
    await store.close()
    await store.close()

    assert not store.is_open
    assert fake_client().close_calls == 1


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.close", rules=["STO-03"])
async def test__elasticsearch_store_closes_its_client_when_the_body_raises(
    settings: StoreSettings, fake_client: Callable[[], FakeClient]
) -> None:
    """Leaving ``async with`` by an exception still closes the client."""
    message = "boom"

    with pytest.raises(RuntimeError, match=message):
        async with ElasticsearchStore(settings):
            raise RuntimeError(message)

    assert fake_client().close_calls == 1


@pytest.mark.covers(
    "aurelius_atlas_store_es.ElasticsearchStore.client",
    "aurelius_atlas_store_es.ElasticsearchStore.is_open",
    rules=["STO-03"],
)
async def test__elasticsearch_store_client_requires_an_open_store(settings: StoreSettings) -> None:
    """The client is only available between open and close."""
    with pytest.raises(RuntimeError, match=STORE_NOT_OPEN_ERROR):
        _ = ElasticsearchStore(settings).client


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.open", rules=["STO-04"])
@pytest.mark.parametrize("version", ["8.19.23", "10.0.0", "unknown"])
async def test__elasticsearch_store_open_rejects_unsupported_versions(
    settings: StoreSettings, fake_client: Callable[[], FakeClient], version: str
) -> None:
    """A server that is not Elasticsearch 9 is refused, and the client is closed."""
    fake_client().version = version
    store = ElasticsearchStore(settings)

    with pytest.raises(UnsupportedVersionError, match=version):
        await store.open()

    assert not store.is_open
    assert fake_client().close_calls == 1


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.open", rules=["STO-04"])
@pytest.mark.parametrize(
    "error",
    [
        TransportConnectionError("connection refused"),
        ConnectionTimeout("timed out"),
        AuthenticationException("unauthorized", response_meta(401), {}),
    ],
)
async def test__elasticsearch_store_open_reports_an_unavailable_server(
    settings: StoreSettings, fake_client: Callable[[], FakeClient], error: Exception, password: str
) -> None:
    """An unreachable or refusing server raises StoreUnavailableError, and the client is closed."""
    fake_client().info_error = error
    store = ElasticsearchStore(settings)

    with pytest.raises(StoreUnavailableError) as caught:
        await store.open()

    assert caught.value.__cause__ is error
    assert password not in str(caught.value)
    assert not store.is_open
    assert fake_client().close_calls == 1


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.health", rules=["STO-06"])
async def test__elasticsearch_store_health_is_down_when_not_open(settings: StoreSettings) -> None:
    """Asking a closed store for its health does not raise."""
    report = await ElasticsearchStore(settings).health()

    assert report.status is HealthStatus.DOWN
    assert report.reason == "store is not open"


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.health", rules=["STO-05", "STO-07"])
async def test__elasticsearch_store_health_asks_the_cluster(
    settings: StoreSettings, fake_client: Callable[[], FakeClient]
) -> None:
    """An open store reports the cluster's health."""
    async with ElasticsearchStore(settings) as store:
        report = await store.health()

    assert report.status is HealthStatus.UP
    assert report.cluster_name == fake_client().cluster_name


@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.open", rules=["STO-08"])
async def test__elasticsearch_store_does_not_log_the_password(
    settings: StoreSettings, fake_client: Callable[[], FakeClient], caplog: pytest.LogCaptureFixture, password: str
) -> None:
    """Neither a successful nor a failed open logs the password."""
    caplog.set_level("DEBUG")

    async with ElasticsearchStore(settings) as store:
        await store.health()
    fake_client().info_error = TransportConnectionError("connection refused")
    with pytest.raises(StoreUnavailableError):
        await ElasticsearchStore(settings).open()

    assert caplog.records
    assert password not in caplog.text
