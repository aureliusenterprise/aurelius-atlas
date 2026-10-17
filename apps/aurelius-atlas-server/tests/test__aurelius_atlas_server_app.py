import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es import ElasticsearchStore, StoreUnavailableError
from aurelius_atlas_store_es.testing.fake import FakeClient
from elasticsearch import ConnectionError as TransportConnectionError


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
