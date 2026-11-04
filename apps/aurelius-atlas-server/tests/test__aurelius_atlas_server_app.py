import logging

import pytest
from aurelius_atlas_otel import ClientCredentialsTokenSource
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_server.app import BRIDGED_LOGGERS, _ingest_source
from aurelius_atlas_store_es import ElasticsearchStore, StoreUnavailableError
from aurelius_atlas_store_es.testing.fake import FakeClient
from elasticsearch import ConnectionError as TransportConnectionError
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from pydantic import SecretStr


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["SRV-02"])
async def test__the_store_is_open_while_the_server_runs(settings: ServerSettings, fake_es: FakeClient) -> None:
    """Start-up opens the store built from the settings; shutdown closes it."""
    app = create_app(settings)
    store: ElasticsearchStore = app.state.store

    async with app.router.lifespan_context(app):
        assert store.is_open
        assert fake_es.kwargs["hosts"] == ["https://localhost:9200"]

    assert not store.is_open
    assert fake_es.close_calls == 1


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["SRV-02"])
async def test__the_server_does_not_start_without_its_store(settings: ServerSettings, fake_es: FakeClient) -> None:
    """An unreachable store stops the start-up."""
    fake_es.info_error = TransportConnectionError("connection refused")
    app = create_app(settings)

    with pytest.raises(StoreUnavailableError, match="unreachable"):
        async with app.router.lifespan_context(app):
            pass


@pytest.mark.covers("aurelius_atlas_server.app.create_app")
def test__create_app_uses_a_given_store(settings: ServerSettings) -> None:
    """A store passed in is used as it is."""
    store = ElasticsearchStore(settings.store_settings())

    assert create_app(settings, store).state.store is store


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["OBS-01"])
def test__the_server_s_loggers_reach_the_log_pipeline_and_the_output(settings: ServerSettings) -> None:
    """Each bridged logger carries one OTel handler and still propagates to the process's output (OBS-01)."""
    saved = {name: (logging.getLogger(name).handlers, logging.getLogger(name).propagate) for name in BRIDGED_LOGGERS}
    try:
        create_app(settings)
        create_app(settings)  # a second app replaces the handlers, never stacks them

        for name in BRIDGED_LOGGERS:
            logger = logging.getLogger(name)
            assert len([h for h in logger.handlers if isinstance(h, LoggingHandler)]) == 1
            assert logger.propagate is True
    finally:
        for name, (handlers, propagate) in saved.items():
            logging.getLogger(name).handlers, logging.getLogger(name).propagate = handlers, propagate


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["OBS-01"])
def test__the_ingest_credential_comes_from_the_settings(settings: ServerSettings) -> None:
    """No token URL or secret, no export; both, a client-credentials source for the per-service leg (OBS-01)."""
    assert _ingest_source(settings) is None

    configured = settings.model_copy(
        update={"otel_token_url": "https://keycloak.localhost:8443/token", "otel_client_secret": SecretStr("s")}
    )
    source = _ingest_source(configured)

    assert isinstance(source, ClientCredentialsTokenSource)
