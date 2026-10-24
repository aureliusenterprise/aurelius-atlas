"""The endpoints the composition root mounts: health, validation (DD-209)."""

from aurelius_atlas_validate_entity.routes.health import HEALTH
from aurelius_atlas_validate_entity.routes.validate import VALIDATE, build_router

__all__ = ["HEALTH", "VALIDATE", "build_router"]
