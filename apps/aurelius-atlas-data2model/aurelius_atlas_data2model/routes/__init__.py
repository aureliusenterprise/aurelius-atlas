"""The endpoints the composition root mounts: health, extraction (DD-120)."""

from aurelius_atlas_data2model.routes.extract import EXTRACT, build_router
from aurelius_atlas_data2model.routes.health import HEALTH

__all__ = ["EXTRACT", "HEALTH", "build_router"]
