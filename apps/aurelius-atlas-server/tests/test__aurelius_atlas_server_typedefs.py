from typing import cast

import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument, StoredTypedefs
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
    await stored.write(StoredTypedefs(AtlasTypesDef(entity_defs=[AtlasEntityDef(name="stored_type")])), None)
    app = create_app(settings.model_copy(update={"typedef_refresh_seconds": 30.0}))

    async with app.router.lifespan_context(app):
        assert app.state.type_registry.entity_type("stored_type") is not None
        assert app.state.typedef_store.registry is app.state.type_registry


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["TDS-12"])
async def test__with_nothing_stored_the_registry_holds_the_built_in_types(
    settings: ServerSettings, fake_es: FakeClient
) -> None:
    """A fresh store creates the typedef index and, without models, starts with the built-in types only."""
    app = create_app(settings)

    async with app.router.lifespan_context(app):
        assert app.state.type_registry.is_registered("string")
        assert app.state.type_registry.typedef_names("ENTITY") == []
    assert "aurelius-atlas-typedefs" in fake_es.aliases


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["MDL-16"])
async def test__the_models_are_loaded_after_the_stored_types(settings: ServerSettings, fake_es: FakeClient) -> None:
    """By default Atlas's 2.4.0 models load at start-up, patched, next to what was stored."""
    stored = ElasticsearchTypedefDocument(cast("AsyncElasticsearch", fake_es))
    await stored.prepare()
    await stored.write(StoredTypedefs(AtlasTypesDef(entity_defs=[AtlasEntityDef(name="stored_type")])), None)
    app = create_app(settings.model_copy(update={"models_dir": BUILTIN_MODELS_DIR}))

    async with app.router.lifespan_context(app):
        registry = app.state.type_registry
        assert registry.entity_type("stored_type") is not None
        assert registry.entity_type("hive_table") is not None
        referenceable = registry.typedef_by_name("Referenceable")
        assert referenceable is not None
        assert referenceable.service_type == "atlas_core"
    written, _ = await stored.read()
    assert written is not None
    assert written.patches
