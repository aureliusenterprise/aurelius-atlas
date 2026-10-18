from typing import cast

import pytest
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument
from aurelius_atlas_model.typedef import AtlasEntityDef, AtlasTypesDef
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient
from elasticsearch import AsyncElasticsearch


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["TDS-12"])
async def test__the_registry_is_loaded_from_the_stored_types_at_start_up(
    settings: ServerSettings, fake_es: FakeClient
) -> None:
    """The lifespan opens the store, then loads the typedef document into the server's registry."""
    stored = ElasticsearchTypedefDocument(cast("AsyncElasticsearch", fake_es))
    await stored.prepare()
    await stored.write(AtlasTypesDef(entity_defs=[AtlasEntityDef(name="stored_type")]), None)
    app = create_app(settings.model_copy(update={"typedef_refresh_seconds": 30.0}))

    async with app.router.lifespan_context(app):
        assert app.state.type_registry.entity_type("stored_type") is not None
        assert app.state.typedef_store.registry is app.state.type_registry


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["TDS-12"])
async def test__with_nothing_stored_the_registry_holds_the_built_in_types(
    settings: ServerSettings, fake_es: FakeClient
) -> None:
    """A fresh store creates the typedef index and starts with the built-in types only."""
    app = create_app(settings)

    async with app.router.lifespan_context(app):
        assert app.state.type_registry.is_registered("string")
        assert app.state.type_registry.typedef_names("ENTITY") == []
    assert "aurelius-atlas-typedefs" in fake_es.aliases
