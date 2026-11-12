"""The metrics stored, listed, read by time and purged against the dev Elasticsearch (MHS-01, MHS-02, MHS-05)."""

import json

import pytest
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.metrics_service import MetricsService
from aurelius_atlas_core.metrics_util import AtlasMetricsUtil
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_typesystem.registry import TypeRegistry

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

HOUR = 3_600_000
BASE = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json").read_text(encoding="utf-8"))


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_core.metrics_service.MetricsService.save_metrics",
    "aurelius_atlas_core.metrics_service.MetricsService.get_all_metrics_stats",
    "aurelius_atlas_core.metrics_service.MetricsService.get_metrics_stat_by_collection_time",
    "aurelius_atlas_core.metrics_service.MetricsService.purge_metrics_stats",
    rules=["MHS-01", "MHS-02", "MHS-05"],
)
async def test__the_metrics_are_stored_as_entities_and_purged_after_their_time(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Two hours stored, the latest first, read back by time with their metrics; the expired one purged."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    await types.create_types_def(AtlasTypesDef.model_validate(BASE))
    now = [HOUR / 1000]
    store = EntityStore(
        types.registry, ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix), clock=lambda: now[0]
    )
    await store.prepare()
    service = MetricsService(store, AtlasMetricsUtil(), namespace="e2e", ttl_hours=1)
    await service.save_metrics(store_connected=True)
    now[0] = 2 * HOUR / 1000
    await service.save_metrics(store_connected=True)

    listed = await service.get_all_metrics_stats(min_info=True)
    found = await service.get_metrics_stat_by_collection_time(HOUR)
    now[0] = (2 * HOUR + 1) / 1000
    purged = await service.purge_metrics_stats()

    assert [stat.collection_time for stat in listed] == [2 * HOUR, HOUR]
    assert found.metrics is not None
    assert found.metrics.metric("general", "collectionTime") == HOUR
    assert [stat.collection_time for stat in purged] == [HOUR]
    assert [stat.collection_time for stat in await service.get_all_metrics_stats(min_info=True)] == [2 * HOUR]
