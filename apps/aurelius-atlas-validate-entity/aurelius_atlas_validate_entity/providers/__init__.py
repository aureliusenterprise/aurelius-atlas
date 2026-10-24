"""The factories that build the app's collaborators: auth and telemetry (DD-108, DD-120).

The composition root in ``app.py`` wires what these build; the routes serve
requests. The app has no upstreams — its answer is module data (DV-50), not a
collaborator to build.
"""

from aurelius_atlas_validate_entity.providers.auth import build_auth
from aurelius_atlas_validate_entity.providers.telemetry import configure_telemetry, ingest_pipeline

__all__ = ["build_auth", "configure_telemetry", "ingest_pipeline"]
